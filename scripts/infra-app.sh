#!/usr/bin/env bash
# Creates, updates or deletes the app stack (infra/app) with Terraform.
# Usage: scripts/infra-app.sh up|down

# Stop on the first failing command, on an unset variable, and on a
# failure anywhere in a pipe.
set -euo pipefail

# The repo root, found from this file's location, so the script works
# from any directory.
root="$(cd "$(dirname "$0")/.." && pwd)"
stack="$root/infra/app"

up() {
  terraform -chdir="$stack" init -input=false
  # Shows the plan and waits for "yes" before changing anything, then
  # prints the instance's public IP.
  terraform -chdir="$stack" apply
}

down() {
  terraform -chdir="$stack" init -input=false
  # Shows what will be deleted and waits for "yes".
  terraform -chdir="$stack" destroy
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  *)
    echo "Usage: $0 up|down" >&2
    exit 2
    ;;
esac
