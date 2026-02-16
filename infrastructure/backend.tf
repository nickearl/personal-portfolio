terraform {
  backend "gcs" {
    bucket  = "FILL_ME_IN"
    prefix  = "default/state"
  }
}
