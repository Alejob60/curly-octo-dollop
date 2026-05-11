# Terraform Variables Configuration
# Copy this and populate with your actual GCP project details

variable "gcp_project_id" {
  description = "Your GCP Project ID"
  type        = string
  # Replace with your actual GCP project ID
}

variable "gcp_region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (prod, staging, dev)"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be one of: production, staging, development"
  }
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "orbital-prime-api"
}

variable "app_version" {
  description = "Application version/tag"
  type        = string
  default     = "latest"
}

variable "enable_monitoring" {
  description = "Enable Google Cloud Monitoring"
  type        = bool
  default     = true
}

variable "enable_cloud_trace" {
  description = "Enable Cloud Trace for distributed tracing"
  type        = bool
  default     = true
}

variable "cloud_run_memory" {
  description = "Cloud Run memory allocation (must be valid format)"
  type        = string
  default     = "2Gi"
  validation {
    condition = contains(["256Mi", "512Mi", "1Gi", "2Gi", "4Gi", "6Gi", "8Gi"], var.cloud_run_memory)
    error_message = "Memory must be one of: 256Mi, 512Mi, 1Gi, 2Gi, 4Gi, 6Gi, 8Gi"
  }
}

variable "cloud_run_cpu" {
  description = "Cloud Run CPU allocation"
  type        = string
  default     = "2"
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 100
}

variable "custom_domain" {
  description = "Custom domain for Cloud Run (optional)"
  type        = string
  default     = ""
}

variable "vpc_network_name" {
  description = "VPC network name for internal connectivity"
  type        = string
  default     = "default"
}

variable "vpc_subnet_name" {
  description = "Subnetwork name used by Cloud Run connector"
  type        = string
  default     = "default"
}

variable "serverless_connector_cidr" {
  description = "CIDR range reserved for the Serverless VPC Access connector"
  type        = string
  default     = "10.8.0.0/28"
}

variable "mongo_vm_internal_ip" {
  description = "Internal IP address of the MongoDB VM in GCP"
  type        = string
  default     = "10.128.0.3"
}

variable "mongo_port" {
  description = "MongoDB port on the VM"
  type        = number
  default     = 27017
}

variable "mongo_database_name" {
  description = "MongoDB database name used by GovDocs"
  type        = string
  default     = "govdocs_db"
}

variable "mongo_username" {
  description = "MongoDB username for the GovDocs application"
  type        = string
  default     = "adminRealculture"
}

variable "mongo_password" {
  description = "MongoDB password for the GovDocs application"
  type        = string
  default     = "Alejob6005901@/"
  sensitive   = true
}

locals {
  service_labels = {
    environment = var.environment
    service     = var.service_name
    managed_by  = "terraform"
  }
}
