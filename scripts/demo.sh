#!/usr/bin/env bash
# Sends one made-up payment to the service's POST /score and prints the
# HTTP status and the response body.
# Usage: scripts/demo.sh https://<ip> [-k]
#   -k: accept a certificate that clients don't trust (Let's Encrypt's
#       staging certificate, or the self-signed fallback).

# Stop on the first failing command, on an unset variable, and on a
# failure anywhere in a pipe.
set -euo pipefail

base="${1:?Usage: $0 https://<ip> [-k]}"
insecure=()
if [ "${2:-}" = "-k" ]; then
  insecure=(-k)
fi

# Asked for without showing it, so the key is never typed on a command
# line or saved in the shell history.
read -rsp "API key: " key
echo

# A new payment ID each run, since each run is a new payment attempt.
# Every value is made up.
body=$(printf '{"payment_id":"pay_demo_%s","amount":1000,"currency":"USD","card_id":"card_demo"}' "$(date +%s)")

# The Authorization header is read from a file descriptor (-H @...), so
# the key isn't in curl's arguments, which other processes can see.
# -w adds the status after the body, on its own line.
response=$(curl -sS --max-time 20 "${insecure[@]}" -X POST "$base/score" \
  -H 'Content-Type: application/json' \
  -H @<(printf 'Authorization: Bearer %s\n' "$key") \
  --data-binary "$body" -w '\n%{http_code}')

echo "Sent:   $body"
echo "Status: ${response##*$'\n'}"
echo "Body:   ${response%$'\n'*}"
