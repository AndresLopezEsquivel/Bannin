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
repo="andreslopezesquivel/bannin"

# Prints the digest the image tag `main` points to in GHCR, through the
# registry API: an anonymous pull token first, then a HEAD request for
# the manifest, whose Docker-Content-Digest header holds the digest.
image_digest() {
  local token
  token=$(curl -fsS "https://ghcr.io/token?scope=repository:$repo:pull" |
    sed -E 's/.*"token":"([^"]+)".*/\1/')
  # Accepts both manifest formats, OCI and Docker, single image or list.
  curl -fsSI -H "Authorization: Bearer $token" \
    -H "Accept: application/vnd.oci.image.index.v1+json" \
    -H "Accept: application/vnd.oci.image.manifest.v1+json" \
    -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json" \
    -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
    "https://ghcr.io/v2/$repo/manifests/main" |
    tr -d '\r' | awk 'tolower($1) == "docker-content-digest:" { print $2 }'
}

up() {
  terraform -chdir="$stack" init -input=false
  # Shows the plan and waits for "yes" before changing anything.
  terraform -chdir="$stack" apply
  local ip
  ip=$(terraform -chdir="$stack" output -raw public_ip)

  # First boot installs Docker, pulls the images and gets the
  # certificate. Tries every 10 seconds, for up to 5 minutes. -k skips
  # the certificate check, which is done separately below.
  echo "Waiting for https://$ip/health ..."
  local try
  for try in $(seq 30); do
    if curl -fsSk --max-time 5 -o /dev/null "https://$ip/health"; then
      break
    fi
    if [ "$try" -eq 30 ]; then
      echo "No answer after 5 minutes. Look inside with Session Manager:" >&2
      echo "  cloud-init status; sudo docker compose -f /opt/bannin/compose.yaml logs" >&2
      exit 1
    fi
    sleep 10
  done

  # Reads the issuer of the certificate the server sends.
  local issuer
  issuer=$(openssl s_client -connect "$ip:443" </dev/null 2>/dev/null |
    openssl x509 -noout -issuer | sed 's/^issuer= *//')

  echo "Service:  https://$ip"
  echo "Image:    ghcr.io/$repo@$(image_digest)"
  echo "Issuer:   $issuer"
  # Staging comes before production: both issuers contain "Let's Encrypt".
  case "$issuer" in
    *"Caddy Local Authority"*)
      echo "Warning: Let's Encrypt failed; the fallback self-signed certificate is in use." >&2
      ;;
    *STAGING*)
      echo "Note: a staging certificate; clients don't trust it, so use curl -k." ;;
    *"Let's Encrypt"*)
      echo "Note: a production certificate; clients trust it." ;;
  esac
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
