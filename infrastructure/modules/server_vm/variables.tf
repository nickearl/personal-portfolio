
variable "domain_name" {
  description = "Domain name for UI/API"
  type        = string
}

variable "contact_email" {
  description = "Email used for SSL certificate registration"
  type        = string
}

variable "static_ip_name" {
  description = "Name of the static IP resource"
  type        = string
}

variable "server_name" {
  description = "Name of the VM instance running the server"
  type        = string
}

variable "network_tag" {
  description = "Network tag applied to the VM"
  type        = string
}

variable "port" {
  description = "Port to use for nginx proxy_pass"
  type        = string
}

variable "project_id" {
  description = "Google Cloud project ID"
  type = string
}

variable "bucket_name" {
  description = "GCS bucket name used for state and backups"
  type = string
}

variable "machine_type" {
  description = "GCE machine type"
  type        = string
}

variable "boot_image" {
  description = "Boot image"
  type        = string
}

variable "boot_disk_size_gb" {
  description = "Root disk size (GB)"
  type        = number
}

variable "db_disk_size_gb" {
  description = "DB persistent disk size (GB)"
  type        = number
}

variable "ssh_user" {
  description = "VM username for uploading files"
  type        = string
}

variable "ssh_private_key_path" {
  description = "Path for Google creds (from gcloud compute os-login ssh-keys add --key-file ~/.ssh/google_compute_engine.pub)"
  type        = string
}

variable "flask_secret_key" {
  description = "Random key for Flask to use, generate one in shell ie uuidgen"
  type        = string
}

variable "flask_encryption_key" {
  description = "Key used to encrypt Google session credentials"
  type        = string
}

variable "authorized_domains" {
  description = "Comma-separated list of authorized email domains"
  type        = string
}

variable "github_actions_public_key" {
  description = "Public SSH key for GitHub Actions deployment"
  type        = string
  default     = ""
}