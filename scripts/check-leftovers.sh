#!/usr/bin/env bash
# Lists what is still billed by the hour in us-east-1: instances not
# terminated, EBS volumes and Elastic IPs, tagged or not. Exits 1 if
# any remain. The scripts/infra-app.sh down command runs it after
# deleting the app stack; it also runs on its own.
# Usage: scripts/check-leftovers.sh

# Stop on the first failing command, on an unset variable, and on a
# failure anywhere in a pipe.
set -euo pipefail

region="us-east-1"
tries=6

# Prints one tab-separated line per leftover: type, ID, state (or IP
# address), Name tag. Each `|| return 1` makes a failed AWS call fail
# the check, instead of looking like an empty list.
leftovers() {
  # Every state except terminated: a stopped instance still bills
  # for its disk.
  aws ec2 describe-instances --region "$region" \
    --filters "Name=instance-state-name,Values=pending,running,shutting-down,stopping,stopped" \
    --query "Reservations[].Instances[].[InstanceId, State.Name, Tags[?Key=='Name'] | [0].Value]" \
    --output text | awk '{ print "instance\t" $0 }' || return 1
  aws ec2 describe-volumes --region "$region" \
    --query "Volumes[].[VolumeId, State, Tags[?Key=='Name'] | [0].Value]" \
    --output text | awk '{ print "volume\t" $0 }' || return 1
  aws ec2 describe-addresses --region "$region" \
    --query "Addresses[].[AllocationId, PublicIp, Tags[?Key=='Name'] | [0].Value]" \
    --output text | awk '{ print "elastic-ip\t" $0 }' || return 1
}

# AWS deletes an instance's disk a few seconds after the instance is
# terminated, so the check runs up to 6 times, 10 seconds apart.
for try in $(seq "$tries"); do
  found=$(leftovers)
  if [ -z "$found" ]; then
    echo "No billed leftovers in $region."
    exit 0
  fi
  if [ "$try" -lt "$tries" ]; then
    echo "Leftovers found; checking again in 10 seconds ($try/$tries)."
    sleep 10
  fi
done

echo "Still billed in $region (type, ID, state, Name tag):" >&2
echo "$found" >&2
exit 1
