# Infrastructure

Terraform code for Bannin's AWS resources.

## Stacks

| Stack | Holds | Script |
|---|---|---|
| `costs/` | Monthly cost budget with email alerts | `scripts/infra-costs.sh` |
| `app/` | Bannin's infrastructure (e.g., service's instance) | `scripts/infra-app.sh` |

## Every stack

1. An admin pastes `iam/terraform-policy.json` into the `terraform` IAM
   user's policy in IAM whenever the file changes.
2. Sign in with the AWS CLI as the `terraform` user.
3. Run each stack with its script: `up` creates or updates it, `down`
   deletes it.

State is local (`terraform.tfstate` in each stack, ignored by git).
Losing it means Terraform no longer knows what that stack created.

## `costs/`

Before the first run:

1. Create `costs/terraform.tfvars` with `alert_email = "..."`. Git
   ignores it.
2. Run `terraform -chdir=infra/costs init`.

```bash
scripts/infra-costs.sh up
scripts/infra-costs.sh down
```

## `app/`

One EC2 instance in `us-east-1` runs the latest image published from
`main` (`ghcr.io/andreslopezesquivel/bannin:main`), behind Caddy on
port 443. Caddy gets a Let's Encrypt certificate for the instance's
public IP address, and falls back to a self-signed one if that fails.
The instance, its disk and its public IP address are billed by the
hour, so delete the stack at the end of each session.

Before the first run:

1. An admin creates the `bannin-app` role (see `iam/README.md`).
2. Run `terraform -chdir=infra/app init`.

```bash
# Test certificates: Let's Encrypt's staging environment has much
# higher rate limits, but clients don't trust its certificates.
TF_VAR_acme_ca=staging scripts/infra-app.sh up
# Trusted certificates (the default).
scripts/infra-app.sh up
scripts/infra-app.sh down
```

`up` waits for `https://<ip>/health` (about 2 minutes on first boot),
then prints the service URL, the image digest and the certificate's
issuer. `down` deletes the stack, then runs
`scripts/check-leftovers.sh`, which fails if any instance (not
terminated), EBS volume or Elastic IP is still in `us-east-1`. The
check also runs on its own.

Port 22 is closed. For a shell on the instance, an admin opens EC2 →
**Instances**, selects `bannin-app`, then **Connect → Session Manager →
Connect**. Then:

```bash
cloud-init status                                     # done when boot setup finished
sudo docker compose -f /opt/bannin/compose.yaml ps    # container states
sudo docker compose -f /opt/bannin/compose.yaml logs  # app and Caddy logs
```

## IAM

`iam/` holds the IAM policies and roles that an admin sets up by hand
in the IAM console. See `iam/README.md`.
