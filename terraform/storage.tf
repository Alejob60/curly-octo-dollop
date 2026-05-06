# === Google Cloud Storage Bucket for Documents ===
resource "google_storage_bucket" "govdocs" {
  name          = "orbital-prime-govdocs-${var.gcp_project_id}-${var.environment}"
  location      = "US"
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }

  # Retention policy for legal hold compliance
  retention_policy {
    retention_period_seconds = 31536000  # 1 year
    is_locked                = false     # Set to true in production for immutability
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

# === GCS Bucket for archives (immutable) ===
resource "google_storage_bucket" "archives" {
  name          = "orbital-prime-archives-${var.gcp_project_id}-${var.environment}"
  location      = "US"
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }

  # Immutable bucket for legal compliance
  retention_policy {
    retention_period_seconds = 94608000  # 3 years
    is_locked                = true      # Immutable - cannot be changed
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    archive_tier = "cold"
  }
}

# === Cloud Storage IAM - Service account access ===
resource "google_storage_bucket_iam_member" "govdocs_access" {
  bucket = google_storage_bucket.govdocs.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.orbital_prime.email}"
}

resource "google_storage_bucket_iam_member" "archives_access" {
  bucket = google_storage_bucket.archives.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.orbital_prime.email}"
}

# === Output GCS bucket details ===
output "gcs_govdocs_bucket" {
  value = google_storage_bucket.govdocs.name
}

output "gcs_archives_bucket" {
  value = google_storage_bucket.archives.name
}
