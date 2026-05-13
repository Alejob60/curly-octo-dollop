# === Cloud Memorystore for Redis ===
resource "google_redis_instance" "cache" {
  name               = "orbital-prime-redis-${var.environment}"
  tier               = "standard"
  memory_size_gb     = 5
  region             = var.gcp_region
  redis_version      = "7.0"
  display_name       = "Orbital Prime Redis Cache"
  authorized_network = "default"

  auth_enabled = true

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }

  depends_on = [google_service_account.orbital_prime]
}

# === Store Redis auth token in Secret Manager ===
resource "google_secret_manager_secret" "redis_auth_string" {
  secret_id = "govdocs-redis-auth-${var.environment}"
}

resource "google_secret_manager_secret_version" "redis_auth_string_version" {
  secret      = google_secret_manager_secret.redis_auth_string.id
  secret_data = "redis://:${google_redis_instance.cache.auth_string}@${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
  deletion_policy = "DELETE"
}

# === Output Redis details ===
output "redis_host" {
  value = google_redis_instance.cache.host
}

output "redis_port" {
  value = google_redis_instance.cache.port
}
