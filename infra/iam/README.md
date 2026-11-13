# IAM

An admin sets these up by hand in the IAM console, so the `terraform`
user never gets rights to create or change IAM users, roles or
policies.

## `terraform-policy.json`

The `terraform` user's policy, `bannin-terraform`. An admin pastes the
file into the policy in IAM whenever the file changes.

## The `bannin-app` role

The service's instance runs with this role.

Do these steps in the AWS console, signed in as a user allowed to
create IAM roles.

1. Open the IAM console: search for **IAM** in the console's top
   search bar and select it.
2. In the left menu, select **Roles**, then **Create role**.
3. For **Trusted entity type**, select **AWS service**.
4. For **Use case**, select **EC2**, then select **Next**.
5. On **Add permissions**, search for `AmazonSSMManagedInstanceCore`,
   select its checkbox, and select **Next**. This policy lets Session
   Manager open a shell on the instance.
6. For **Role name**, enter `bannin-app`.
7. Under **Add tags**, add the key `Project` with the value `bannin`.
8. Select **Create role**. The console also creates an instance
   profile named `bannin-app`, which is what attaches the role to the
   instance.

`bannin-app-trust.json` is a copy of the trust policy the console
generates in steps 3 and 4. Nothing needs to be done with it: it
records what the role's **Trust relationships** tab should show.

