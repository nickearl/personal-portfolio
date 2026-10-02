# --- Canary: email when the public site is down or its certificate stops renewing ---

resource "google_monitoring_notification_channel" "email" {
  display_name = "${var.service_name} alerts"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
  depends_on = [google_project_service.services]
}

# Uptime checks run from every selected region each period (3 regions x 96/day, well inside the free 1M/month).
# 900s is the slowest period Cloud Monitoring offers; emails are only sent when an incident opens or closes.
resource "google_monitoring_uptime_check_config" "site" {
  display_name     = "${var.service_name} homepage"
  timeout          = "10s"
  period           = "900s"
  selected_regions = ["USA_OREGON", "USA_IOWA", "USA_VIRGINIA"]

  http_check {
    # Not /healthz: Cloud Run reserves paths ending in "z", so it 404s from outside
    path         = "/portfolio/"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  # A 200 without the page shell (e.g. a placeholder or error page) still counts as down
  content_matchers {
    content = "Nick Earl Portfolio"
    matcher = "CONTAINS_STRING"
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = var.domain_name
    }
  }

  depends_on = [google_project_service.services]
}

resource "google_monitoring_alert_policy" "site_down" {
  display_name          = "${var.domain_name} is down"
  combiner              = "OR"
  notification_channels = [google_monitoring_notification_channel.email.id]

  conditions {
    display_name = "Uptime check failing from 2+ regions"
    condition_threshold {
      filter = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND metric.label.check_id=\"${google_monitoring_uptime_check_config.site.uptime_check_id}\" AND resource.type=\"uptime_url\""
      aggregations {
        alignment_period     = "1200s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.*"]
      }
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      # Longer than one 900s period, so two consecutive failed checks are needed
      duration = "1200s"
      trigger {
        count = 1
      }
    }
  }

  documentation {
    mime_type = "text/markdown"
    content   = <<-EOT
      The uptime check for https://${var.domain_name}/portfolio/ is failing from at least 2 of 3 regions.

      Narrow it down:
      - App: open ${google_cloud_run_v2_service.app.uri}/portfolio/ . If that fails too, the service is down. Run `gcloud run services describe ${var.service_name} --region ${var.region}` and check its logs.
      - Domain/TLS: if the run.app URL works, the problem is DNS, the domain mapping or its certificate. Run `gcloud beta run domain-mappings describe --domain ${var.domain_name} --region ${var.region}`. The Cloudflare record must stay a DNS-only CNAME to ghs.googlehosted.com.
    EOT
  }
}

# Google renews the managed certificate ~30 days before expiry; under 14 days means renewal is stuck
resource "google_monitoring_alert_policy" "cert_expiring" {
  display_name          = "${var.domain_name} TLS certificate is not renewing"
  combiner              = "OR"
  notification_channels = [google_monitoring_notification_channel.email.id]

  conditions {
    display_name = "Certificate expires in under 14 days"
    condition_threshold {
      filter = "metric.type=\"monitoring.googleapis.com/uptime_check/time_until_ssl_cert_expires\" AND metric.label.check_id=\"${google_monitoring_uptime_check_config.site.uptime_check_id}\" AND resource.type=\"uptime_url\""
      aggregations {
        alignment_period     = "1200s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_MIN"
        group_by_fields      = ["resource.label.*"]
      }
      comparison      = "COMPARISON_LT"
      threshold_value = 14
      duration        = "0s"
      trigger {
        count = 1
      }
    }
  }

  documentation {
    mime_type = "text/markdown"
    content   = <<-EOT
      The certificate on https://${var.domain_name} expires in under 14 days, so Google's automatic renewal for the Cloud Run domain mapping is not happening.

      Run `gcloud beta run domain-mappings describe --domain ${var.domain_name} --region ${var.region}` and check that the Cloudflare record is still a DNS-only CNAME to ghs.googlehosted.com. Renewal needs the domain to resolve to Google.
    EOT
  }
}
