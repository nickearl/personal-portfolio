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
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# Token comes from the GITHUB_TOKEN env var (e.g. GITHUB_TOKEN=$(gh auth token) terraform apply)
provider "github" {
  owner = split("/", var.github_repo)[0]
}

# Enable required APIs
resource "google_project_service" "services" {
  for_each           = toset(["iam.googleapis.com", "cloudresourcemanager.googleapis.com", "iamcredentials.googleapis.com", "artifactregistry.googleapis.com", "secretmanager.googleapis.com", "compute.googleapis.com", "run.googleapis.com", "apikeys.googleapis.com", "monitoring.googleapis.com", "generativelanguage.googleapis.com"])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "docker_repo" {
  provider      = google
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repo_name
  description   = "Docker repository for ${var.service_name}"
  format        = "DOCKER"
  depends_on    = [google_project_service.services]
}

# --- GitHub Actions Identity & Access ---

# 1. Service Account for GitHub Actions
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-deployer"
  display_name = "GitHub Actions Deployer"
  project      = var.project_id
}

# 2. Workload Identity Pool (this repo's own; github-pool-ca576959 belongs to Bestfoot's Terraform)
resource "google_iam_workload_identity_pool" "github_pool" {
  workload_identity_pool_id = "${var.service_name}-github"
  display_name              = "GitHub (${var.service_name})"
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

resource "google_project_iam_member" "run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# Lets the deployer launch revisions that run as the app's runtime service account
resource "google_project_iam_member" "sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
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

# --- GitHub Actions Variables ---

resource "github_actions_variable" "gcp_project_id" {
  repository    = split("/", var.github_repo)[1]
  variable_name = "GCP_PROJECT_ID"
  value         = var.project_id
}

resource "github_actions_variable" "gcp_region" {
  repository    = split("/", var.github_repo)[1]
  variable_name = "GCP_REGION"
  value         = var.region
}

resource "github_actions_variable" "artifact_registry_repo_name" {
  repository    = split("/", var.github_repo)[1]
  variable_name = "ARTIFACT_REGISTRY_REPO_NAME"
  value         = var.artifact_registry_repo_name
}

resource "github_actions_variable" "image_name" {
  repository    = split("/", var.github_repo)[1]
  variable_name = "IMAGE_NAME"
  value         = var.image_name
}

resource "github_actions_variable" "cloud_run_service" {
  repository    = split("/", var.github_repo)[1]
  variable_name = "CLOUD_RUN_SERVICE"
  value         = var.service_name
}

# --- Application Secrets ---

resource "random_password" "flask_secret_key" {
  length  = 32
  special = false
}

resource "random_id" "flask_encryption_key" {
  byte_length = 32
}

resource "google_secret_manager_secret" "flask_secret_key" {
  secret_id = "${var.service_name}-flask-secret-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_version" "flask_secret_key" {
  secret      = google_secret_manager_secret.flask_secret_key.id
  secret_data = random_password.flask_secret_key.result
}

resource "google_secret_manager_secret" "flask_encryption_key" {
  secret_id = "${var.service_name}-flask-encryption-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_version" "flask_encryption_key" {
  secret      = google_secret_manager_secret.flask_encryption_key.id
  secret_data = random_id.flask_encryption_key.b64_url
}

# Dedicated Gemini key so the portfolio's usage and quota stay separate from other projects
resource "google_apikeys_key" "gemini" {
  name         = "${var.service_name}-gemini"
  display_name = "${var.service_name} Gemini"
  project      = var.project_id
  restrictions {
    api_targets {
      service = "generativelanguage.googleapis.com"
    }
  }
  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "${var.service_name}-gemini-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_version" "gemini_api_key" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = google_apikeys_key.gemini.key_string
}

# --- Cloud Run ---

resource "google_service_account" "app_runtime" {
  account_id   = "${var.service_name}-run"
  display_name = "${var.service_name} Cloud Run runtime"
  project      = var.project_id
}

resource "google_secret_manager_secret_iam_member" "app_secret_access" {
  for_each = {
    flask_secret_key     = google_secret_manager_secret.flask_secret_key.secret_id
    flask_encryption_key = google_secret_manager_secret.flask_encryption_key.secret_id
    gemini_api_key       = google_secret_manager_secret.gemini_api_key.secret_id
  }
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_runtime.email}"
}

resource "google_cloud_run_v2_service" "app" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.app_runtime.email
    # Each AI demo request is a single Gemini call; matches gunicorn's --timeout in app/Dockerfile
    timeout                          = "120s"
    max_instance_request_concurrency = 16 # gunicorn: 1 worker x 16 threads

    scaling {
      # One warm instance so the first visitor never waits for a ~20s cold start
      min_instance_count = 1
      max_instance_count = 3
    }

    containers {
      # Placeholder for the first create only; GitHub Actions deploys the real image
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = var.port
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "DEPLOY_ENV"
        value = "prod"
      }
      env {
        name  = "SERVER_NAME"
        value = var.service_name
      }
      env {
        name  = "ENABLE_GOOGLE_AUTH"
        value = "false"
      }
      env {
        name = "FLASK_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.flask_secret_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "FLASK_ENCRYPTION_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.flask_encryption_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/healthz"
        }
        period_seconds    = 5
        timeout_seconds   = 3
        failure_threshold = 24
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [
    google_project_service.services,
    google_secret_manager_secret_iam_member.app_secret_access,
    google_secret_manager_secret_version.flask_secret_key,
    google_secret_manager_secret_version.flask_encryption_key,
    google_secret_manager_secret_version.gemini_api_key,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.app.name
  location = google_cloud_run_v2_service.app.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Google-managed TLS certificate, renewed automatically
resource "google_cloud_run_domain_mapping" "app" {
  location = var.region
  name     = var.domain_name
  metadata {
    namespace = var.project_id
  }
  spec {
    route_name = google_cloud_run_v2_service.app.name
  }
}

# Must stay DNS-only (not proxied) or Google cannot issue the certificate
resource "cloudflare_record" "app_dns" {
  zone_id = var.cloudflare_zone_id
  name    = split(".", var.domain_name)[0]
  content = "ghs.googlehosted.com"
  type    = "CNAME"
  proxied = false
}

output "service_url" {
  value = google_cloud_run_v2_service.app.uri
}
