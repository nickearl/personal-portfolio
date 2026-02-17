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
    IMAGE_PATH    = var.gar_image_path
  })
  port = var.port
  proxy_target   = "app:${var.port}"
  nginx_http_conf = templatefile("${path.module}/../../scripts/nginx/conf.d/default-http.conf.tftpl", {
    domain_name         = var.domain_name
    proxy_target        = local.proxy_target
  })

  nginx_ssl_conf = templatefile("${path.module}/../../scripts/nginx/conf.d/default-ssl.conf.tftpl", {
    domain_name       = var.domain_name
    proxy_target      = local.proxy_target
    port              = var.port
  })

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
      size  = var.boot_disk_size_gb
      type  = "pd-balanced"
    }
  }


  network_interface {
    network = "default"
    network_ip = google_compute_address.internal_ip.address
    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  metadata = {
    enable-oslogin = "FALSE"
    ssh-keys       = trimspace(join("\n", compact([
      var.github_actions_public_key != "" ? "${var.ssh_user}:${var.github_actions_public_key}" : "",
      "${var.ssh_user}:${file("${pathexpand(var.ssh_private_key_path)}.pub")}"
    ])))
  }

  service_account {
    scopes = ["cloud-platform"]
  }
}

resource "null_resource" "provision_vm" {
  depends_on = [google_compute_instance.app_server]

  triggers = {
    script_hash = sha256(data.template_file.startup_script.rendered)
    instance_id = google_compute_instance.app_server.id
  }

  connection {
    type        = "ssh"
    user        = var.ssh_user
    private_key = file(pathexpand(var.ssh_private_key_path))
    host        = google_compute_instance.app_server.network_interface.0.access_config.0.nat_ip
  }

  provisioner "file" {
    content     = data.template_file.startup_script.rendered
    destination = "/tmp/startup.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/startup.sh",
      "sudo /tmp/startup.sh"
    ]
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

resource "google_project_iam_member" "vm_artifact_registry_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${data.google_compute_default_service_account.default.email}"
}

resource "google_project_iam_member" "vm_token_writer" {
  project   = var.project_id
  role      = "roles/secretmanager.secretVersionAdder"
  member    = "serviceAccount:${data.google_compute_default_service_account.default.email}"
}

data "template_file" "startup_script" {
  template = file("${path.module}/../../scripts/startup.sh.tftpl")

  vars = {
    domain_name     = var.domain_name
    contact_email   = var.contact_email
    server_name     = var.server_name
    ip              = google_compute_address.static_ip.address
    dotenv_file     = local.dotenv
    compose_file    = local.compose_file
    port            = local.port
    ssh_user        = var.ssh_user
    nginx_http_conf = local.nginx_http_conf
    nginx_ssl_conf  = local.nginx_ssl_conf
    region          = var.region
    bucket_name     = var.bucket_name
  }
}
