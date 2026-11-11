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
