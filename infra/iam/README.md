# IAM

An admin sets these up by hand in the IAM console, so the `terraform`
user never gets rights to create or change IAM users, roles or
policies.

## `terraform-policy.json`

The `terraform` user's policy, `bannin-terraform`. An admin pastes the
file into the policy in IAM whenever the file changes.

## The `bannin-app` role

The service's instance runs with this role.

1. **Roles → Create role.** Trusted entity type: **AWS service**. Use
   case: **EC2**.
2. Attach `AmazonSSMManagedInstanceCore`, so Session Manager can open a
   shell on the instance.
3. Name it `bannin-app`, add the tag `Project = bannin`, and create it.
   The console also creates an instance profile named `bannin-app`.

`bannin-app-trust.json` is a copy of the trust policy the console
generates in step 1. Nothing needs to be done with it: it records what
the role's **Trust relationships** tab should show.
