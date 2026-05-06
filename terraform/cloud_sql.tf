# === Cloud SQL PostgreSQL Instance ===
resource "google_sql_database_instance" "postgres" {
  name             = "orbital-prime-postgres-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.gcp_region

  settings {
    tier              = "db-custom-2-8192"
    availability_type = "REGIONAL"  # High availability
    disk_type         = "PD_SSD"
    disk_size         = 100
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 30
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      require_ssl = true

      # Allow Cloud Run to connect
      authorized_networks {
        name  = "Cloud Run"
        value = "0.0.0.0/0"  # Restrict further with Cloud SQL Auth proxy
      }
    }

    database_flags {
      name  = "log_statement"
      value = "all"
    }

    user_labels = {
      environment = var.environment
      managed_by  = "terraform"
    }
  }
}

# === Cloud SQL Database ===
resource "google_sql_database" "govdocs" {
  name     = "govdocs_${var.environment}"
  instance = google_sql_database_instance.postgres.name
  charset  = "UTF8"
}

# === Cloud SQL User ===
resource "google_sql_user" "govdocs_user" {
  name     = "govdocs_user"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

# === Generate secure password ===
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# === Store password in Secret Manager ===
resource "google_secret_manager_secret" "database_password" {
  secret_id = "govdocs-db-password-${var.environment}"
}

resource "google_secret_manager_secret_version" "database_password_version" {
  secret             = google_secret_manager_secret.database_password.id
  secret_data        = random_password.db_password.result
  deletion_policy    = "DELETE"
}

# === Store full connection string in Secret Manager ===
resource "google_secret_manager_secret" "database_url" {
  secret_id = "govdocs-database-url-${var.environment}"
}

resource "google_secret_manager_secret_version" "database_url_version" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = "postgresql+asyncpg://govdocs_user:${random_password.db_password.result}@/${google_sql_database.govdocs.name}?host=/cloudsql/${google_sql_database_instance.postgres.connection_name}"
  deletion_policy = "DELETE"
}

# === Output Cloud SQL connection details ===
output "cloudsql_instance_name" {
  value = google_sql_database_instance.postgres.name
}

output "cloudsql_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "cloudsql_database_name" {
  value = google_sql_database.govdocs.name
}

output "cloudsql_user" {
  value = google_sql_user.govdocs_user.name
}
