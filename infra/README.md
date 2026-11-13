# Infrastructure

Terraform code for Bannin's AWS resources.

## Stacks

| Stack | Holds | Script |
|---|---|---|
| `costs/` | Monthly cost budget with email alerts | `scripts/infra-costs.sh` |
| `app/` | Bannin's infrastructure (e.g., service's instance) | `scripts/infra-app.sh` |

## Every stack

1. Whenever `iam/terraform-policy.json` changes, a user allowed to
   edit IAM policies copies it into the `bannin-terraform` policy (see
   `iam/README.md`).
2. Sign in with the AWS CLI as a user whose only policy is
   `bannin-terraform`.
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

1. A user allowed to create IAM roles creates the `bannin-app` role
   (see `iam/README.md`).
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

Port 22 is closed. For a shell on the instance, do these steps in the
AWS console, signed in as a user allowed to start Session Manager
sessions:

1. Open the EC2 console: search for **EC2** in the console's top
   search bar and select it.
2. In the left menu, select **Instances**.
3. Select the checkbox of the running instance named `bannin-app`,
   then select **Connect**.
4. Select the **Session Manager** tab, then **Connect**.

A shell opens in the browser. Then:

```bash
cloud-init status                                     # done when boot setup finished
sudo docker compose -f /opt/bannin/compose.yaml ps    # container states
sudo docker compose -f /opt/bannin/compose.yaml logs  # app and Caddy logs
```

## Deploys from CI

On every push to `main`, once the checks pass and the image is
published, the CI `deploy` job:

1. Gets credentials for the `bannin-ci` role through GitHub's OIDC
   token. No AWS keys are stored in GitHub.
2. Runs `scripts/deploy.sh <commit hash>`. If no instance named
   `bannin-app` is running, it prints "No instance running; nothing to
   deploy." and passes.
3. Otherwise, through SSM Run Command, the instance sets `IMAGE_TAG` in
   `/opt/bannin/.env` to the commit hash, pulls that image, replaces
   the app container and waits until its health check passes. The job
   prints the command's output and fails if the command failed.

The next spin-up starts from `main` again, the latest image.

To read a deploy's output, open the repository's **Actions** tab,
select the run, then the `deploy` job and its **Deploy this commit's
image** step. The role's ARN and the account ID show as `***`.

If a deploy fails, the instance may be left running the new, unhealthy
container. To deploy an earlier commit's image again, re-run only that
run's `deploy` job (re-running every job would rebuild that commit and
move the `main` tag back to it):

1. In the repository's **Actions** tab, select the earlier commit's
   run.
2. Select the `deploy` job.
3. Select the re-run button at the top right of the job's log, then
   **Re-run job**.

Set up once, outside the code:

1. A user allowed to create IAM providers, policies and roles creates
   the `bannin-ci` role (see `iam/README.md`).
2. A user with admin rights on the GitHub repository adds the role's
   ARN as a secret, in GitHub:
   1. In the repository, select **Settings**.
   2. In the left menu, select **Secrets and variables**, then
      **Actions**.
   3. Select **New repository secret**.
   4. For **Name**, enter `AWS_ROLE_ARN`. For **Secret**, enter
      `arn:aws:iam::<account-id>:role/bannin-ci`, with the account's
      ID.
   5. Select **Add secret**.
   6. Repeat steps 3 to 5 with the name `AWS_ROLE_ID` and the role's
      unique ID (starts with `AROA`) as the value. The deploy job
      masks it in the logs, since the account ID can be decoded from
      it. To read the ID, run
      `aws iam get-role --role-name bannin-ci --query Role.RoleId`
      as a user allowed to read IAM roles, for example in CloudShell.
3. Only pushes to `main` can deploy, so `main` is protected. In the
   repository's **Settings**, the left menu's **Rules**, then
   **Rulesets**, lists the `main` ruleset: it blocks deleting and
   force-pushing `main`, and requires a pull request whose CI checks
   pass.

## IAM

`iam/` holds the IAM policies and roles that a user with rights to
manage IAM sets up by hand in the AWS console. See `iam/README.md`.
