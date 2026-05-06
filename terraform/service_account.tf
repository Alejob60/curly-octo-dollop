# === Service Account ===
resource "google_service_account" "orbital_prime" {
  account_id   = "orbital-prime-sa"
  display_name = "Orbital Prime API Service Account"
  description  = "Service account for Orbital Prime GovDocs Engine"
}

# === IAM Bindings ===
resource "google_project_iam_member" "run_developer" {
  project = var.gcp_project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_project_iam_member" "storage_admin" {
  project = var.gcp_project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_project_iam_member" "cloudsql_client" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_project_iam_member" "cloudkms_crypto_decrypter" {
  project = var.gcp_project_id
  role    = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member  = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_project_iam_member" "monitoring_metric_writer" {
  project = var.gcp_project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_project_iam_member" "logging_log_writer" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_project_iam_member" "secretmanager_accessor" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_project_iam_member" "aiplatform_user" {
  project = var.gcp_project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_project_iam_member" "redis_admin" {
  project = var.gcp_project_id
  role    = "roles/redis.admin"
  member  = "serviceAccount:${google_service_account.orbital_prime.email}"
}
