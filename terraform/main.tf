# Terraform Configuration for Mandate Vault on GCP
# ==================================================

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    bucket = "mandate-vault-terraform-state"
    prefix = "terraform/state"
  }
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (staging/production)"
  type        = string
}

variable "db_tier" {
  description = "Database instance tier"
  type        = string
  default     = "db-g1-small"
}

# Enable required APIs
resource "google_project_service" "services" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudkms.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com"
  ])
  
  service            = each.value
  disable_on_destroy = false
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "mandate-vault-${var.environment}"
  auto_create_subnetworks = false
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name          = "mandate-vault-subnet-${var.environment}"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
  
  private_ip_google_access = true
}

# Cloud SQL (PostgreSQL)
resource "google_sql_database_instance" "postgres" {
  name             = "mandate-vault-db-${var.environment}"
  database_version = "POSTGRES_14"
  region           = var.region
  
  settings {
    tier              = var.db_tier
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    disk_size         = 20
    disk_type         = "PD_SSD"
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = var.environment == "production"
      backup_retention_settings {
        retained_backups = 7
      }
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }
    
    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }
  
  deletion_protection = var.environment == "production"
}

# Database
resource "google_sql_database" "database" {
  name     = "mandate_vault"
  instance = google_sql_database_instance.postgres.name
}

# Database User
resource "google_sql_user" "user" {
  name     = "mandate_user"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

# Generate secure database password
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Secret Manager - Database URL
resource "google_secret_manager_secret" "database_url" {
  secret_id = "mandate-vault-database-url-${var.environment}"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = "postgresql+asyncpg://${google_sql_user.user.name}:${random_password.db_password.result}@/${google_sql_database.database.name}?host=/cloudsql/${google_sql_database_instance.postgres.connection_name}"
}

# Secret Manager - Application Secret Key
resource "google_secret_manager_secret" "secret_key" {
  secret_id = "mandate-vault-secret-key"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "secret_key" {
  secret      = google_secret_manager_secret.secret_key.id
  secret_data = random_password.secret_key.result
}

resource "random_password" "secret_key" {
  length  = 64
  special = false
}

# GKE Cluster (for production)
resource "google_container_cluster" "primary" {
  count = var.environment == "production" ? 1 : 0
  
  name     = "mandate-vault-cluster"
  location = var.region
  
  # We can't create a cluster with no node pool, so we create the smallest possible default node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1
  
  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name
  
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  
  release_channel {
    channel = "REGULAR"
  }
  
  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
  }
}

# GKE Node Pool
resource "google_container_node_pool" "primary_nodes" {
  count      = var.environment == "production" ? 1 : 0
  name       = "mandate-vault-node-pool"
  location   = var.region
  cluster    = google_container_cluster.primary[0].name
  node_count = 3
  
  autoscaling {
    min_node_count = 3
    max_node_count = 10
  }
  
  node_config {
    machine_type = "e2-medium"
    disk_size_gb = 50
    disk_type    = "pd-standard"
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

# Cloud Run Service (for staging)
resource "google_cloud_run_service" "api" {
  count    = var.environment == "staging" ? 1 : 0
  name     = "mandate-vault-${var.environment}"
  location = var.region
  
  template {
    spec {
      service_account_name = google_service_account.api.email
      
      containers {
        image = "gcr.io/${var.project_id}/mandate-vault:latest"
        
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        
        env {
          name = "SECRET_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.secret_key.secret_id
              key  = "latest"
            }
          }
        }
        
        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.database_url.secret_id
              key  = "latest"
            }
          }
        }
        
        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }
      }
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale"      = "10"
        "run.googleapis.com/cloudsql-instances" = google_sql_database_instance.postgres.connection_name
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Cloud Run IAM
resource "google_cloud_run_service_iam_member" "public" {
  count    = var.environment == "staging" ? 1 : 0
  service  = google_cloud_run_service.api[0].name
  location = google_cloud_run_service.api[0].location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Service Account
resource "google_service_account" "api" {
  account_id   = "mandate-vault-${var.environment}"
  display_name = "Mandate Vault API Service Account"
}

# IAM - Secret Manager Access
resource "google_secret_manager_secret_iam_member" "api_secret_key" {
  secret_id = google_secret_manager_secret.secret_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

resource "google_secret_manager_secret_iam_member" "api_database_url" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

# IAM - Cloud SQL Client
resource "google_project_iam_member" "api_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}

# Artifact Registry
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "mandate-vault"
  description   = "Docker repository for Mandate Vault"
  format        = "DOCKER"
}

# Outputs
output "database_connection_name" {
  value       = google_sql_database_instance.postgres.connection_name
  description = "Cloud SQL instance connection name"
}

output "service_url" {
  value       = var.environment == "staging" ? google_cloud_run_service.api[0].status[0].url : "Deploy with kubectl"
  description = "Service URL"
}

output "service_account_email" {
  value       = google_service_account.api.email
  description = "Service account email"
}
