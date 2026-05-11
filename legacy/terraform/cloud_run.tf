# === Cloud Run Service ===
resource "google_cloud_run_service" "api" {
  name     = var.service_name
  location = var.gcp_region

  template {
    spec {
      service_account_name = google_service_account.orbital_prime.email

      containers {
        image = "gcr.io/${var.gcp_project_id}/${var.service_name}:${var.app_version}"

        ports {
          container_port = 3001
        }

        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }

        env {
          name  = "PORT"
          value = "3001"
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "AI_PROVIDER"
          value = "vertex"
        }

        env {
          name  = "MONGODB_PROVIDER"
          value = "local"
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.gcp_project_id
        }

        env {
          name  = "GCP_LOCATION"
          value = var.gcp_region
        }

        env {
          name  = "CLOUD_SQL_CONNECTION_NAME"
          value = google_sql_database_instance.postgres.connection_name
        }

        env {
          name  = "GCS_BUCKET_NAME"
          value = google_storage_bucket.govdocs.name
        }

        env {
          name  = "REDIS_URL"
          value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
        }

        # Secrets from Secret Manager
        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.database_url.id
              key  = "latest"
            }
          }
        }

        env {
          name = "MONGODB_ATLAS_URI"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.mongodb_uri.id
              key  = "latest"
            }
          }
        }

        env {
          name  = "MONGO_DB"
          value = var.mongo_database_name
        }

        env {
          name = "MONGO_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.mongodb_uri.id
              key  = "latest"
            }
          }
        }

        env {
          name = "JWT_SECRET"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.jwt_secret.id
              key  = "latest"
            }
          }
        }
      }

      timeout_seconds = 3600
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "100"
        "autoscaling.knative.dev/minScale" = "1"
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.cloud_run_connector.id
        "run.googleapis.com/vpc-access-egress"    = "private-ranges-only"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_cloud_run_service_iam_member.public_access,
    google_sql_database_instance.postgres,
    google_storage_bucket.govdocs,
    google_redis_instance.cache,
    google_vpc_access_connector.cloud_run_connector,
    google_compute_firewall.allow_cloud_run_to_mongo,
  ]
}

# === Cloud Run IAM - Allow unauthenticated access ===
resource "google_cloud_run_service_iam_member" "public_access" {
  service       = google_cloud_run_service.api.name
  location      = google_cloud_run_service.api.location
  role          = "roles/run.invoker"
  member        = "allUsers"
  depends_on    = [google_cloud_run_service.api]
}

# === Cloud Run custom domain (optional) ===
resource "google_cloud_run_domain_mapping" "default" {
  location       = google_cloud_run_service.api.location
  name           = "api.yourdomain.com"  # Change to your domain
  service_name   = google_cloud_run_service.api.name

  metadata {
    namespace = var.gcp_project_id
  }

  depends_on = [google_cloud_run_service.api]
}
