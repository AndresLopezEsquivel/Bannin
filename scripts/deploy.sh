#!/usr/bin/env bash
# Deploys the image built from a commit to the service's instance, if
# it runs. With no instance running, says so and exits 0. CI runs it
# after publishing the image; it also runs by hand.
# Usage: scripts/deploy.sh <full 40-character commit hash>

# Stop on the first failing command, on an unset variable, and on a
# failure anywhere in a pipe.
set -euo pipefail

region="us-east-1"
sha="${1:-}"

# Only a full hash is accepted: it's both the image tag and part of
# the command run on the instance, so nothing else may get through.
if ! [[ "$sha" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Usage: scripts/deploy.sh <full 40-character commit hash>" >&2
  exit 2
fi

# The ID of the running instance tagged Name = bannin-app, if any.
instance=$(aws ec2 describe-instances --region "$region" \
  --filters "Name=tag:Name,Values=bannin-app" "Name=instance-state-name,Values=running" \
  --query "Reservations[].Instances[].InstanceId" --output text)
if [ -z "$instance" ]; then
  echo "No instance running; nothing to deploy."
  exit 0
fi
if [ "$(wc -w <<<"$instance")" -ne 1 ]; then
  echo "More than one running instance named bannin-app: $instance" >&2
  exit 1
fi

# Run on the instance, as root, by the SSM agent: sets IMAGE_TAG in
# .env (replacing the line, or adding it), pulls the image, replaces
# the app container and waits until its health check passes, then
# prints the image's digest.
commands=$(jq -n --arg sha "$sha" '{
  commands: [
    "set -eu",
    "cd /opt/bannin",
    "if grep -q \"^IMAGE_TAG=\" .env; then sed -i \"s/^IMAGE_TAG=.*/IMAGE_TAG=\($sha)/\" .env; else echo \"IMAGE_TAG=\($sha)\" >> .env; fi",
    "docker compose pull app",
    "docker compose up -d --wait app",
    "docker inspect --format \"{{index .RepoDigests 0}}\" ghcr.io/andreslopezesquivel/bannin:\($sha)"
  ],
  executionTimeout: ["300"]
}')

echo "Deploying $sha to $instance ..."
command_id=$(aws ssm send-command --region "$region" \
  --instance-ids "$instance" --document-name AWS-RunShellScript \
  --comment "Deploy $sha" --parameters "$commands" \
  --query "Command.CommandId" --output text)

# Checks every 5 seconds, for up to 6 minutes. Right after sending,
# AWS may not know the invocation yet, which counts as Pending.
for _ in $(seq 72); do
  sleep 5
  status=$(aws ssm get-command-invocation --region "$region" \
    --command-id "$command_id" --instance-id "$instance" \
    --query Status --output text 2>/dev/null) || status=Pending
  case "$status" in
    Pending | InProgress | Delayed) continue ;;
    *) break ;;
  esac
done

# Prints what the commands wrote, then fails unless they all succeeded.
for stream in StandardOutputContent StandardErrorContent; do
  echo "--- $stream"
  aws ssm get-command-invocation --region "$region" \
    --command-id "$command_id" --instance-id "$instance" \
    --query "$stream" --output text
done
echo "Status: $status"
[ "$status" = Success ]
