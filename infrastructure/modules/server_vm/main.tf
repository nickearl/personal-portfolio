variable "region" {
  description = "Region for the internal IP"
  type        = string
}

locals {
  dotenv = templatefile("${path.module}/../../scripts/.env.tftpl", {
    PROJECT_ID            = var.project_id
    BUCKET_NAME           = var.bucket_name
    PORT                  = var.port
    SERVER_NAME           = var.server_name
    FLASK_SECRET_KEY      = var.flask_secret_key
    FLASK_ENCRYPTION_KEY  = var.flask_encryption_key
    AUTHORIZED_DOMAINS    = var.authorized_domains
    
  })
  compose_file = templatefile("${path.module}/../../scripts/docker-compose.yml.tftpl", {
    PORT          = var.port
    SERVER_NAME   = var.server_name
  })
  dockerfile_file = templatefile("${path.module}/../../scripts/Dockerfile.tftpl", {
    PORT = var.port
  })
  port = var.port
}

resource "google_compute_address" "static_ip" {
  name   = var.static_ip_name
}

resource "google_compute_address" "internal_ip" {
  name         = "${var.server_name}-internal-ip"
  subnetwork   = "default"
  address_type = "INTERNAL"
  region       = var.region
}

resource "google_compute_instance" "app_server" {
  name         = var.server_name
  machine_type = var.machine_type
  tags         = [var.network_tag]

  boot_disk {
    initialize_params {
      image = var.boot_image
      size  = 30
    }
  }


  network_interface {
    network = "default"
    network_ip = google_compute_address.internal_ip.address
    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  metadata_startup_script = local_file.startup_script.content

  metadata = {
    enable-oslogin = "TRUE"
    ssh-keys       = var.github_actions_public_key != "" ? "${var.ssh_user}:${var.github_actions_public_key}" : null
  }

  service_account {
    scopes = ["cloud-platform"]
  }
}

output "static_ip" {
  value = google_compute_address.static_ip.address
}

output "internal_ip" {
  value = google_compute_address.internal_ip.address
}

data "google_compute_default_service_account" "default" {
}

resource "google_project_iam_member" "vm_gcs_write_access" {
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${data.google_compute_default_service_account.default.email}"
  project = var.project_id
}

resource "google_project_iam_member" "vm_secretmanager_access" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${data.google_compute_default_service_account.default.email}"
}

resource "google_project_iam_member" "vm_token_writer" {
  project   = var.project_id
  role      = "roles/secretmanager.secretVersionAdder"
  member    = "serviceAccount:${data.google_compute_default_service_account.default.email}"
}



data "google_secret_manager_secret_version" "contact_email" {
  secret  = "contact-email"
  version = "latest"
}


data "template_file" "startup_script" {
  template = file("${path.module}/../../scripts/startup.sh.tftpl")

  vars = {
    domain_name     = var.domain_name
    contact_email   = data.google_secret_manager_secret_version.contact_email.secret_data
    server_name     = var.server_name
    ip              = google_compute_address.static_ip.address
    dotenv_file     = local.dotenv
    compose_file    = local.compose_file
    dockerfile_file = local.dockerfile_file
    port            = local.port
    ssh_user        = var.ssh_user
  }
}

resource "local_file" "startup_script" {
  content  = data.template_file.startup_script.rendered
  filename = "${path.module}/../../scripts/startup.sh"
}

resource "null_resource" "upload_startup_script" {
  depends_on = [google_compute_instance.app_server, local_file.startup_script]

  triggers = {
    script_hash = sha256(data.template_file.startup_script.rendered)
  }

  connection {
    type        = "ssh"
    user        = var.ssh_user
    private_key = file(var.ssh_private_key_path)
    host        = google_compute_instance.app_server.network_interface[0].access_config[0].nat_ip
  }

  # Copy the rendered script up to a durable path
  provisioner "file" {
    source      = local_file.startup_script.filename
    destination = "/tmp/startup.sh"
  }

  # Make it executable and root-owned
  provisioner "remote-exec" {
    inline = [
      "sudo mv /tmp/startup.sh /home/${var.ssh_user}/startup.sh",
      "sudo chown root:root /home/${var.ssh_user}/startup.sh",
      "sudo chmod 0755 /home/${var.ssh_user}/startup.sh",
    ]
  }
}

# Render templated Dockerfile into ./app
resource "local_file" "rendered_dockerfile" {
  content  = templatefile("${path.module}/../../scripts/Dockerfile.tftpl", {
    PORT = var.port
  })
  filename = "${path.root}/app/Dockerfile"
}

# Bundle the whole ./app dir after Dockerfile exists
data "archive_file" "app_bundle" {
  depends_on  = [local_file.rendered_dockerfile]
  type        = "zip"
  source_dir  = "${path.root}/app"
  output_path = "${path.root}/build/app.zip"
}

# Copy app.zip to VM
resource "null_resource" "upload_app" {
  depends_on = [google_compute_instance.app_server, null_resource.upload_startup_script]

  triggers = {
    app_bundle_hash = data.archive_file.app_bundle.output_base64sha256
    script_hash     = sha256(data.template_file.startup_script.rendered)
  }

  connection {
    type        = "ssh"
    user        = var.ssh_user
    private_key = file(var.ssh_private_key_path)
    host        = google_compute_instance.app_server.network_interface[0].access_config[0].nat_ip
  }

  provisioner "file" {
    source      = data.archive_file.app_bundle.output_path
    destination = "/tmp/app.zip"
  }

  # Trigger the startup script to unpack and deploy immediately after upload
  provisioner "remote-exec" {
    inline = [
      "sudo /home/${var.ssh_user}/startup.sh"
    ]
  }
}

# uv.lock contents (handle "file may not exist")
locals {
  uv_lock_contents = try(file("${path.root}/uv.lock"), "")
  has_uv_lock      = length(local.uv_lock_contents) > 0
}

# Ensure pyproject.toml is inside app/ (build context)
resource "local_file" "pyproject_into_app" {
  content  = file("${path.root}/pyproject.toml")
  filename = "${path.root}/app/pyproject.toml"
}

# Copy uv.lock if present
resource "local_file" "uv_lock_into_app" {
  count    = local.has_uv_lock ? 1 : 0
  content  = local.uv_lock_contents
  filename = "${path.root}/app/uv.lock"
}
