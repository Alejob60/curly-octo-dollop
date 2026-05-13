# Terraform Backend Configuration
# Create a Cloud Storage bucket for remote state management

# Step 1: Create the backend bucket manually:
# gsutil mb -p YOUR_PROJECT_ID gs://orbital-prime-terraform-state

# Step 2: Enable versioning on the bucket:
# gsutil versioning set on gs://orbital-prime-terraform-state

# Step 3: Create this file as terraform/backend.tf with your bucket name

terraform {
  backend "gcs" {
    bucket  = "orbital-prime-terraform-state"
    prefix  = "production"
  }
}

# For local testing, use local backend:
# terraform {
#   backend "local" {
#     path = "terraform.tfstate"
#   }
# }

# To migrate from local to GCS:
# terraform init -reconfigure -backend-config=bucket=orbital-prime-terraform-state -backend-config=prefix=production
