#!/bin/bash
set -euo pipefail

echo "🔧 Terraform bootstrap (no SSL, VM-only)"
# Ensure terraform exists
command -v terraform >/dev/null || { echo "terraform not found"; exit 1; }

echo "🔧 Initializing Terraform..."
BUCKET_NAME=$(grep bucket_name terraform.tfvars | cut -d\" -f2)
PREFIX=$(grep server_name terraform.tfvars | cut -d\" -f2)
terraform init \
  -backend-config="bucket=${BUCKET_NAME}" \
  -backend-config="prefix=${PREFIX}/state" \
  -reconfigure

# macOS-specific fix: ensure provider binaries are executable
chmod -R +x .terraform/providers || true
if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "📦 macOS detected: removing quarantine flag on .terraform directory..."
  xattr -dr com.apple.quarantine .terraform/ || true
fi

echo "🚀 Proceeding with full Terraform apply..."
terraform apply -auto-approve

echo ""
echo "---------------------------------------------------"
echo "✅ Infrastructure updated."
echo "To view the GitHub Secrets (including Private Key), run:"
echo "terraform output -raw github_secrets"
echo "---------------------------------------------------"
