# IAM

Bannin's IAM resources, each set up by hand in the AWS console.
Terraform's IAM user isn't allowed to create or change IAM users,
roles or policies, so a user with rights to manage IAM creates them.

| Identity | Used by | Section |
|---|---|---|
| An IAM user with the `bannin-terraform` policy | Terraform, run from your machine | [Terraform's IAM user](#terraforms-iam-user) |
| The `bannin-app` role, through its instance profile | The service's EC2 instance, to read its API keys | [The `bannin-app` role](#the-bannin-app-role) |
| The `bannin-ci` role, through OIDC | GitHub Actions, to deploy | [The `bannin-ci` role](#the-bannin-ci-role) |

## Terraform's IAM user

Terraform runs as an IAM user with two policies: `bannin-terraform`
(from `terraform-policy.json`), and the AWS managed policy
`SignInLocalDevelopmentAccess`, which lets the user sign in to the AWS
CLI with `aws login`. The user has console access and no access keys.

Do these steps in the AWS console, signed in as a user allowed to
create IAM users and policies.

1. Open the IAM console: search for **IAM** in the console's top
   search bar and select it.
2. In the left menu, select **Policies**, then **Create policy**.
3. Select the **JSON** tab, replace the policy in the editor with the
   contents of `terraform-policy.json`, then select **Next**.
4. For **Policy name**, enter `bannin-terraform`.
5. Under **Add tags**, add the key `Project` with the value `bannin`,
   then select **Create policy**.
6. In the left menu, select **Users**, then **Create user**.
7. For **User name**, enter a name of your choice.
8. Select **Provide user access to the AWS Management Console**, then
   **I want to create an IAM user**. Choose a password, then select
   **Next**.
9. Under **Permissions options**, select **Attach policies directly**.
   Search for `bannin-terraform` and `SignInLocalDevelopmentAccess`,
   select both checkboxes, then select **Next**.
10. Under **Tags**, add the key `Project` with the value `bannin`,
    then select **Create user**.
11. Select the new user, open the **Security credentials** tab, and
    under **Multi-factor authentication (MFA)** select **Assign MFA
    device**. Follow the console's steps.

Then, on your machine, run `aws login` and sign in as this user in
the browser that opens.

## `terraform-policy.json`

Terraform's IAM user's policy, `bannin-terraform`. Whenever the file
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

### Reading the API keys

The app reads the API keys from Parameter Store when it starts. The
policy `bannin-app-keys` (`bannin-app-keys-policy.json`) lets the role
list and read the parameters under `/bannin/api-keys`, and nothing
else. AWS checks this permission against the path the app asks for,
not against each parameter it returns. No KMS permission is needed:
the keys are encrypted with the account's AWS managed key `aws/ssm`,
which every IAM principal in the account may decrypt through
Parameter Store.

Do these steps in the AWS console, signed in as a user allowed to
create IAM policies and attach them to roles.

1. Open the IAM console: search for **IAM** in the console's top
   search bar and select it.
2. In the left menu, select **Policies**, then **Create policy**.
3. Select the **JSON** tab, replace the policy in the editor with the
   contents of `bannin-app-keys-policy.json`, and select **Next**.
4. For **Policy name**, enter `bannin-app-keys`.
5. Under **Add tags**, add the key `Project` with the value `bannin`.
6. Select **Create policy**.
7. In the left menu, select **Roles**, search for `bannin-app`, and
   select its name.
8. On the **Permissions** tab, select **Add permissions**, then
   **Attach policies**.
9. Search for `bannin-app-keys`, select its checkbox, and select
   **Add permissions**.

### The first API key

Each key is a SecureString parameter named `/bannin/api-keys/key_NN`;
its last segment is the key's ID, which is what the app logs. The app
accepts at most two keys at once.

First, make a random key in your own terminal. It prints the key once
and nowhere else:

```sh
python3 -c 'import secrets; print("bn_" + secrets.token_urlsafe(32))'
```

Then do these steps in the AWS console, signed in as a user allowed to
create Parameter Store parameters:

1. In the console's top right, check that the Region is **US East
   (N. Virginia)**. Parameters exist in one Region only.
2. Open the Systems Manager console: search for **Systems Manager** in
   the console's top search bar and select it.
3. In the left menu, select **Parameter Store**, then **Create
   parameter**.
4. For **Name**, enter `/bannin/api-keys/key_01`. The app reads only
   names under `/bannin/api-keys/`, and refuses to start if the last
   segment isn't `key_` followed by two digits.
5. Leave **Description** empty, or say who uses the key (for example
   `Demo caller`). Never put the key there: the description isn't
   encrypted.
6. For **Tier**, select **Standard**. Standard parameters are free;
   advanced ones are billed each month.
7. For **Type**, select **SecureString**, not **String** or
   **StringList**: those store the key unencrypted, and the app
   refuses to start if a key isn't a SecureString. The console then
   shows a note recommending Secrets Manager for API keys. This
   project uses Parameter Store, which is free, and rotates keys by
   hand (see [API keys](../README.md#api-keys)).
8. For **Data type**, keep `text`.
9. For **KMS key source**, select **My current account**, and for
   **KMS Key ID**, keep `alias/aws/ssm`. The console notes that every
   user in the account can use this key; that's expected (see
   [Reading the API keys](#reading-the-api-keys)).
10. For **Value**, paste the whole key from your terminal, starting
    with `bn_`, with no spaces before or after it. A stored space
    becomes part of the key, and no caller's key would match it.
11. Under **Tags**, select **Add tag** and add the key `Project` with
    the value `bannin`.
12. Select **Create parameter**. The **My parameters** list shows
    `/bannin/api-keys/key_01` with the type **SecureString**.

Then clear your terminal. To see the key again later, open the
parameter in Parameter Store and select **Show decrypted value**.

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
