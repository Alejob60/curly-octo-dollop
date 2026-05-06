data "google_project" "current" {
  project_id = var.gcp_project_id
}

resource "google_vpc_access_connector" "cloud_run_connector" {
  name          = "orbital-prime-connector-${var.environment}"
  project       = var.gcp_project_id
  region        = var.gcp_region
  network       = var.vpc_network_name
  ip_cidr_range = var.serverless_connector_cidr

  min_instances = 2
  max_instances = 3

  machine_type = "e2-micro"
}

resource "google_compute_firewall" "allow_cloud_run_to_mongo" {
  name    = "allow-orbital-cloudrun-to-mongo-${var.environment}"
  network = var.vpc_network_name
  project = var.gcp_project_id

  direction     = "INGRESS"
  source_ranges = [var.serverless_connector_cidr]
  target_service_accounts = [
    "${data.google_project.current.number}-compute@developer.gserviceaccount.com",
  ]

  allow {
    protocol = "tcp"
    ports    = [tostring(var.mongo_port)]
  }

  description = "Allow Cloud Run traffic from the serverless connector to the MongoDB VM on the internal network."
}
