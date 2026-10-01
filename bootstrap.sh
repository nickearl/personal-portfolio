#!/bin/bash
# Plan/apply the infrastructure. Extra args pass through, e.g. ./bootstrap.sh plan
set -euo pipefail
cd "$(dirname "$0")/infrastructure"

command -v terraform >/dev/null || { echo "terraform not found"; exit 1; }

# github provider auth, and the account-wide Cloudflare token kept in Secret Manager
export GITHUB_TOKEN="$(gh auth token)"
export TF_VAR_cloudflare_api_token="$(gcloud secrets versions access latest --secret=cloudflare-api-token)"

# Backend bucket/prefix come from backend.tf
terraform init -input=false
terraform "${@:-apply}"
