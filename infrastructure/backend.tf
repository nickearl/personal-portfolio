terraform {
  backend "gcs" {
    bucket  = "ne-tf"
    prefix  = "default/state"
  }
}
