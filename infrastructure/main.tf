terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

data "google_secret_manager_secret_version" "github_token" {
  secret  = "github-etl-pat"
  version = "latest"
}

provider "github" {
  token = data.google_secret_manager_secret_version.github_token.secret_data
  owner = split("/", var.github_repo)[0]
}

# Enable required APIs
resource "google_project_service" "services" {
  for_each = toset(["iam.googleapis.com", "cloudresourcemanager.googleapis.com", "iamcredentials.googleapis.com", "artifactregistry.googleapis.com", "secretmanager.googleapis.com"])
  project  = var.project_id
  service  = each.key
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "docker_repo" {
  provider      = google
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repo_name
  description   = "Docker repository for ${var.server_name}"
  format        = "DOCKER"
  depends_on    = [google_project_service.services]
}

resource "local_file" "github_workflow" {
  content = templatefile("${path.module}/scripts/deploy.yml.tftpl", {
    project_id  = var.project_id
    region      = var.region
    repo_name   = var.artifact_registry_repo_name
    image_name  = var.image_name
    vm_name     = var.server_name
    vm_zone     = var.zone
    port        = var.port
  })
  filename = "${path.module}/.github/workflows/deploy.yml"
}

# --- GitHub Actions Identity & Access ---

# 1. Service Account for GitHub Actions
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-deployer"
  display_name = "GitHub Actions Deployer"
  project      = var.project_id
}

# 2. Workload Identity Pool
resource "google_iam_workload_identity_pool" "github_pool" {
  workload_identity_pool_id = "github-pool-insights"
  display_name              = "GitHub Actions Pool"
  project                   = var.project_id
  depends_on                = [google_project_service.services]
}

# 3. Workload Identity Provider
resource "google_iam_workload_identity_pool_provider" "github_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"
  project                            = var.project_id
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }
  attribute_condition = "assertion.repository == '${var.github_repo}'"
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# 4. Allow GitHub Repo to impersonate the Service Account
resource "google_service_account_iam_member" "workload_identity_user" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/attribute.repository/${var.github_repo}"
}

# 5. Grant Permissions to the Service Account
resource "google_project_iam_member" "artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "compute_admin" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# --- SSH Key for Deployment ---

resource "tls_private_key" "github_deploy_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "github_actions_secret" "gcp_workload_identity_provider" {
  repository      = split("/", var.github_repo)[1]
  secret_name     = "GCP_WORKLOAD_IDENTITY_PROVIDER"
  plaintext_value = google_iam_workload_identity_pool_provider.github_provider.name
}

resource "github_actions_secret" "gcp_service_account" {
  repository      = split("/", var.github_repo)[1]
  secret_name     = "GCP_SERVICE_ACCOUNT"
  plaintext_value = google_service_account.github_actions.email
}

resource "github_actions_secret" "gcp_ssh_private_key" {
  repository      = split("/", var.github_repo)[1]
  secret_name     = "GCP_SSH_PRIVATE_KEY"
  plaintext_value = tls_private_key.github_deploy_key.private_key_openssh
}

module "firewall" {
  source = "./modules/firewall"
  server_name = var.server_name
  network_tag = var.network_tag
}

module "server_vm" {
  source = "./modules/server_vm"
  domain_name           = var.domain_name
  contact_email         = var.contact_email
  static_ip_name        = var.static_ip_name
  server_name           = var.server_name
  network_tag           = var.network_tag
  project_id            = var.project_id
  bucket_name           = var.bucket_name
  port                  = var.port
  machine_type          = var.machine_type
  boot_image            = var.boot_image
  boot_disk_size_gb     = var.boot_disk_size_gb
  db_disk_size_gb       = var.db_disk_size_gb
  ssh_user              = var.ssh_user
  ssh_private_key_path  = var.ssh_private_key_path
  flask_secret_key      = var.flask_secret_key
  flask_encryption_key  = var.flask_encryption_key
  authorized_domains    = var.authorized_domains
  region                = var.region
  github_actions_public_key = tls_private_key.github_deploy_key.public_key_openssh
}

output "reserved_static_ip" {
  value = module.server_vm.static_ip
}

output "app_internal_ip" {
  value = module.server_vm.internal_ip
}

output "github_secrets" {
  sensitive = true
  value = <<EOT
  
  ✅ GitHub Secrets have been automatically configured for ${var.github_repo}.
  
  EOT
}