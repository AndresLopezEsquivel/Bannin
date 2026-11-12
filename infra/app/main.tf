# The service's server.

terraform {
  required_version = "~> 1.17"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.72"
    }
  }
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      Project = "bannin"
      Stack   = "app"
    }
  }
}

# Provides the ID of the OS image used to boot the service's instance.
# Canonical publishes the current image ID in a public parameter hosted by AWS (see `name`).
# If Canonical publishes a new image while the instance is running, the next `terraform apply`
# detects the updated image ID and replaces the instance.
# https://documentation.ubuntu.com/aws/aws-how-to/instances/find-ubuntu-images/
data "aws_ssm_parameter" "ubuntu_ami" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id"
}

data "aws_vpc" "default" {
  default = true
}

# The instance's firewall. No inbound rules yet: nothing can connect in.
resource "aws_security_group" "app" {
  name        = "bannin-app"
  description = "Bannin service instance"
  vpc_id      = data.aws_vpc.default.id
}

# Lets the instance open connections to any address, for example to pull the
# image. Terraform removes AWS's default outbound rule when it creates a
# security group, so the rule is declared here.
resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.app.id
  description       = "All outbound IPv4 traffic"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# The default VPC includes one default subnet in each Availability Zone.
# `default_for_az = true` tells AWS to select the default subnet created
# for the specified AZ. In this case, it selects the default subnet in
# us-east-1a.
# We pin the AZ because AWS could otherwise select one that doesn't offer
# Graviton (arm64) instances.
data "aws_subnet" "app" {
  vpc_id            = data.aws_vpc.default.id
  availability_zone = "us-east-1a"
  default_for_az    = true
}

resource "aws_instance" "app" {
  ami = data.aws_ssm_parameter.ubuntu_ami.insecure_value
  # The smallest type that fits for now. Switch to a bigger one when it
  # runs out of memory.
  instance_type               = "t4g.micro"
  subnet_id                   = data.aws_subnet.app.id
  vpc_security_group_ids      = [aws_security_group.app.id]
  associate_public_ip_address = true
  # The bannin-app role is created manually in the AWS console; see
  # infra/iam/README.md. It may move into code later, with a permissions
  # boundary.
  iam_instance_profile = "bannin-app"

  # Hands the instance a set of setup instructions to run when it first boots.
  # Then cloud-init handles the instructions. Cloud-init runs only on
  # first boot, so a change to the file replaces the instance.
  # templatefile replaces ${compose} in user-data.yaml with compose.yaml,
  # base64-encoded, so a change to either file replaces the instance.
  user_data = templatefile("${path.module}/user-data.yaml", {
    compose = base64encode(file("${path.module}/compose.yaml"))
  })
  user_data_replace_on_change = true

  # Controls the instance metadata service (IMDS).
  metadata_options {
    http_endpoint = "enabled"
    # Allows IMDSv2 only: every request to IMDS needs a session token.
    http_tokens = "required"
    # Set the IMDS response hop limit (TTL) to 1 to prevent containers
    # from accessing instance metadata, including IAM credentials.
    # Increase it to 2 if containers later need access to IMDS.
    #
    # A hop is one pass through a router: each time a network packet is
    # forwarded from one network to another, it makes one hop. Every
    # packet carries a TTL counter that routers decrement by 1 when
    # forwarding it. Packets are dropped when the counter reaches 0.
    #
    # The hop limit determines the TTL of responses sent by IMDS. When a
    # Docker container requests instance metadata, the EC2 instance acts
    # as a router between the container and IMDS, and forwarding the
    # response back to the container consumes one hop. A hop limit of 1
    # therefore prevents the response from reaching the container, while
    # a limit of 2 allows it.
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 10
    encrypted             = true
    delete_on_termination = true
  }

  tags = {
    Name = "bannin-app"
  }
}

output "public_ip" {
  value = aws_instance.app.public_ip
}
