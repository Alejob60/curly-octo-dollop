# === Secret Manager Secrets ===

# === JWT Secrets ===
resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "govdocs-jwt-secret-${var.environment}"
}

resource "google_secret_manager_secret_version" "jwt_secret_version" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = random_password.jwt_secret.result
  deletion_policy = "DELETE"
}

# === MongoDB Internal URI (GCP VM) ===
resource "google_secret_manager_secret" "mongodb_uri" {
  secret_id = "govdocs-mongodb-uri-${var.environment}"
}

resource "google_secret_manager_secret_version" "mongodb_uri_version" {
  secret = google_secret_manager_secret.mongodb_uri.id
  secret_data = "mongodb://${var.mongo_username}:${urlencode(var.mongo_password)}@${var.mongo_vm_internal_ip}:${var.mongo_port}/${var.mongo_database_name}?authSource=admin&directConnection=true"
  deletion_policy = "DELETE"
}

# === OAuth Client ID and Secret ===
resource "google_secret_manager_secret" "google_oauth_client_id" {
  secret_id = "govdocs-google-oauth-client-id-${var.environment}"
}

resource "google_secret_manager_secret" "google_oauth_client_secret" {
  secret_id = "govdocs-google-oauth-client-secret-${var.environment}"
}

# === Internal API Key ===
resource "google_secret_manager_secret" "internal_api_key" {
  secret_id = "govdocs-internal-api-key-${var.environment}"
}

resource "google_secret_manager_secret_version" "internal_api_key_version" {
  secret      = google_secret_manager_secret.internal_api_key.id
  secret_data = random_password.internal_api_key.result
  deletion_policy = "DELETE"
}

# === Generate random secrets ===
resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "random_password" "internal_api_key" {
  length  = 32
  special = true
}

# === Grant Secret Manager access to service account ===
resource "google_secret_manager_secret_iam_member" "jwt_secret_accessor" {
  secret_id = google_secret_manager_secret.jwt_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_secret_manager_secret_iam_member" "mongodb_uri_accessor" {
  secret_id = google_secret_manager_secret.mongodb_uri.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_secret_manager_secret_iam_member" "database_url_accessor" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_secret_manager_secret_iam_member" "internal_api_key_accessor" {
  secret_id = google_secret_manager_secret.internal_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_secret_manager_secret_iam_member" "database_password_accessor" {
  secret_id = google_secret_manager_secret.database_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.orbital_prime.email}"
}

# === Output secret IDs ===
output "jwt_secret_id" {
  value = google_secret_manager_secret.jwt_secret.id
}

output "mongodb_uri_secret_id" {
  value = google_secret_manager_secret.mongodb_uri.id
}

output "database_url_secret_id" {
  value = google_secret_manager_secret.database_url.id
}

output "internal_api_key_secret_id" {
  value = google_secret_manager_secret.internal_api_key.id
}
