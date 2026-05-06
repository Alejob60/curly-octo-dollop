# Terraform Configuration for Orbital Prime on Google Cloud Platform
# Directory: terraform/
# Usage: terraform plan && terraform apply

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  # Configure backend for remote state
  backend "gcs" {
    bucket = "orbital-prime-terraform-state"
    prefix = "production"
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# === Variables ===
variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (prod, staging, dev)"
  type        = string
  default     = "production"
}

variable "service_name" {
  description = "Service name"
  type        = string
  default     = "orbital-prime-api"
}

variable "app_version" {
  description = "Application version"
  type        = string
  default     = "latest"
}

# === Outputs ===
output "cloud_run_service_url" {
  value       = google_cloud_run_service.api.status[0].url
  description = "URL of the Cloud Run service"
}

output "cloud_sql_connection_name" {
  value       = google_sql_database_instance.postgres.connection_name
  description = "Cloud SQL instance connection name"
}

output "gcs_bucket_name" {
  value       = google_storage_bucket.govdocs.name
  description = "GCS bucket name for document storage"
}

output "memorystore_redis_host" {
  value       = google_redis_instance.cache.host
  description = "Redis instance host"
}

output "service_account_email" {
  value       = google_service_account.orbital_prime.email
  description = "Service account email for Cloud Run"
}
