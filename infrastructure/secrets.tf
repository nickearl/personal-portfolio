resource "random_password" "flask_secret_key" {
  length  = 32
  special = true
}

# Generates a 32-byte URL-safe base64-encoded key suitable for Fernet
resource "random_id" "flask_encryption_key" {
  byte_length = 32
}