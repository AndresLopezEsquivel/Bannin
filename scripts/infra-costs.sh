#!/usr/bin/env bash
# Creates, updates or deletes the costs stack (infra/costs) with Terraform.
# Usage: scripts/infra-costs.sh up|down

# Stop on the first failing command, on an unset variable, and on a
# failure anywhere in a pipe.
set -euo pipefail

# The repo root, found from this file's location, so the script works
# from any directory.
root="$(cd "$(dirname "$0")/.." && pwd)"

up() {
  terraform -chdir="$root/infra/costs" init -input=false
  # Shows the plan and waits for "yes" before changing anything.
  terraform -chdir="$root/infra/costs" apply
}

down() {
  terraform -chdir="$root/infra/costs" init -input=false
  # Shows what will be deleted and waits for "yes".
  terraform -chdir="$root/infra/costs" destroy
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  *)
    echo "Usage: $0 up|down" >&2
    exit 2
    ;;
esac
