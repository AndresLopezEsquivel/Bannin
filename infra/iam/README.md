# IAM

A user with rights to manage IAM sets these up by hand in the AWS
console, so the `terraform` user never gets rights to create or change
IAM users, roles or policies.

## `terraform-policy.json`

The `terraform` user's policy, `bannin-terraform`. Whenever the file
changes, copy it into the policy. Do these steps in the AWS console,
signed in as a user allowed to edit IAM policies.

1. Open the IAM console: search for **IAM** in the console's top
   search bar and select it.
2. In the left menu, select **Policies**, search for
   `bannin-terraform`, and select its name.
3. Select **Edit**, then the **JSON** tab.
4. Replace the policy in the editor with the contents of
   `terraform-policy.json`, then select **Next**.
5. Select **Save changes**.

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

## The `bannin-ci` role

GitHub Actions takes this role to deploy, with no stored AWS keys: the
job gets a signed token from GitHub (OpenID Connect), and AWS swaps it
for credentials that expire within an hour.

Do these steps in the AWS console, signed in as a user allowed to
create IAM identity providers, policies and roles.

First, register GitHub Actions as an identity provider. One provider
serves every role that trusts GitHub Actions, so this is done once per
account.

1. Open the IAM console: search for **IAM** in the console's top
   search bar and select it.
2. In the left menu, select **Identity providers**, then **Add
   provider**.
3. For **Provider type**, select **OpenID Connect**.
4. For **Provider URL**, enter
   `https://token.actions.githubusercontent.com`.
5. For **Audience**, enter `sts.amazonaws.com`.
6. Under **Add tags**, select **Add new tag** and add the key
   `Project` with the value `bannin`.
7. Select **Add provider**.

Then create the role's policy, `bannin-ci-deploy`. It lets the role
find the service's instance and run a shell command on it (the
deploy), and nothing else:

1. In the IAM console's left menu, select **Policies**, then **Create
   policy**.
2. Select the **JSON** tab, replace the policy in the editor with the
   contents of `bannin-ci-policy.json`, and select **Next**.
3. For **Policy name**, enter `bannin-ci-deploy`.
4. Under **Add tags**, add the key `Project` with the value `bannin`.
5. Select **Create policy**.

Whenever `bannin-ci-policy.json` changes, update the policy the same
way as `bannin-terraform` above.

Then create the role:

1. In the IAM console's left menu, select **Roles**, then **Create
   role**.
2. For **Trusted entity type**, select **Custom trust policy**.
3. Delete the example policy in the editor, paste the contents of
   `bannin-ci-trust.json`, and replace `<account-id>` with the
   account's 12-digit ID (shown in the account menu at the top right).
   Select **Next**.
4. On **Add permissions**, search for `bannin-ci-deploy`, select its
   checkbox, and select **Next**.
5. For **Role name**, enter `bannin-ci`.
6. Under **Add tags**, add the key `Project` with the value `bannin`.
7. Select **Create role**.

The trust policy accepts only tokens for pushes to `main` of this
repository. GitHub names the repository by owner and repository IDs as
well as names (`AndresLopezEsquivel@30853355/Bannin@1443610805`), so a
repository that later takes the same name gets no access. A custom
policy is used so the condition holds this exact value.
