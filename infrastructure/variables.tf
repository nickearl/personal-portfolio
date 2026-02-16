variable "domain_name" {
  description = "Domain name for the UI/API service"
  type = string
}

variable "contact_email" {
  description = "Email used for SSL certificate registration"
  type = string
}

variable "static_ip_name" {
  description = "Name of the static IP resource"
  type = string
}

variable "server_name" {
  description = "Name of the VM instance running services"
  type = string
}

variable "region" {
  description = "GCP region to deploy to"
  type = string
}

variable "zone" {
  description = "GCP zone to deploy to"
  type = string
}

variable "network_tag" {
  description = "Network tag applied to the VM"
  type = string
}

variable "project_id" {
  description = "Google Cloud project ID"
  type = string
}

variable "bucket_name" {
  description = "GCS bucket name used for state and backups"
  type = string
}

variable "artifact_registry_repo_name" {
  description = "Name of the Google Artifact Registry repository for Docker images"
  type        = string
  default     = "base-insights-repo"
}

variable "image_name" {
  description = "Name of the Docker image and container"
  type        = string
  default     = "base-insights-app"
}

variable "port" {
  description = "Port to use for nginx proxy_pass to internal app"
  type        = string
  default     = 5309
}

variable "machine_type" {
  description = "GCE machine type"
  type        = string
  default     = "e2-small"
}

variable "boot_image" {
  description = "Boot image"
  type        = string
  default     = "ubuntu-os-cloud/ubuntu-2204-lts"
}

variable "boot_disk_size_gb" {
  description = "Root disk size (GB)"
  type        = number
  default     = 30
}

variable "db_disk_size_gb" {
  description = "DB persistent disk size (GB)"
  type        = number
  default     = 20
}

variable "ssh_user" {
  description = "VM username for uploading files"
  type        = string
}

variable "ssh_private_key_path" {
  description = "Path for Google creds (from gcloud compute os-login ssh-keys add --key-file ~/.ssh/google_compute_engine.pub)"
  type        = string
  default     = "~/.ssh/google_compute_engine"
}

variable "authorized_domains" {
  description = "Comma-separated list of authorized email domains"
  type        = string
  default     = "basemakers.com"
}

variable "cloudflare_api_token" {
  description = "Cloudflare API Token with DNS:Edit permissions"
  type        = string
  sensitive   = true
}

variable "cloudflare_zone_id" {
  description = "The Zone ID for the domain in Cloudflare"
  type        = string
}

variable "github_repo" {
  description = "The GitHub repository (owner/repo) to use for CI/CD deployments"
  type        = string
}