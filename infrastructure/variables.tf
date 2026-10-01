variable "domain_name" {
  description = "Custom domain mapped to the Cloud Run service"
  type        = string
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run and Artifact Registry"
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name (also used to name its service account and secrets)"
  type        = string
}

variable "artifact_registry_repo_name" {
  description = "Artifact Registry Docker repository name"
  type        = string
}

variable "image_name" {
  description = "Docker image name within the repository"
  type        = string
}

variable "port" {
  description = "Port the app container listens on"
  type        = number
  default     = 1701
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token with Zone.DNS edit permission (bootstrap.sh reads it from Secret Manager)"
  type        = string
  sensitive   = true
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for the domain"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository (owner/name) allowed to deploy"
  type        = string
}
