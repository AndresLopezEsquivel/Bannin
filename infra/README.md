# Infrastructure

Terraform code for Bannin's AWS resources.

## Stacks

| Stack | Holds | Script |
|---|---|---|
| `costs/` | Monthly cost budget with email alerts | `scripts/infra-costs.sh` |

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

## IAM

`iam/` holds the IAM policies and roles that an admin sets up by hand
in the IAM console. See `iam/README.md`.
