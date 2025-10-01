# Outputs for Mandate Vault Infrastructure

output "cloud_run_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.app.uri
}

output "database_connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.postgres.connection_name
}

output "database_private_ip" {
  description = "Cloud SQL private IP address"
  value       = google_sql_database_instance.postgres.private_ip_address
  sensitive   = true
}

output "gcs_bucket_name" {
  description = "GCS bucket name"
  value       = google_storage_bucket.app_data.name
}

output "kms_key_name" {
  description = "KMS key name for JWT cache encryption"
  value       = google_kms_crypto_key.jwt_cache_key.name
}

output "artifact_registry_repo" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.app_repo.repository_id}"
}

output "vpc_connector_name" {
  description = "VPC Connector name"
  value       = google_vpc_access_connector.connector.name
}

output "service_account_email" {
  description = "Cloud Run service account email"
  value       = google_service_account.cloud_run_sa.email
}

output "secrets" {
  description = "Secret Manager secret names"
  value = {
    db_password = google_secret_manager_secret.db_password.secret_id
    db_host     = google_secret_manager_secret.db_host.secret_id
    db_name     = google_secret_manager_secret.db_name.secret_id
    db_user     = google_secret_manager_secret.db_user.secret_id
  }
}


