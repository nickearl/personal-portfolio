
resource "google_compute_firewall" "http_https" {
  name    = "${var.server_name}-allow-http-https"
  source_ranges = ["0.0.0.0/0"]
  network = "default"
  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
  direction     = "INGRESS"
  target_tags   = [var.network_tag]
  priority      = 1000
  description   = "Allow HTTP/HTTPS access"
}
