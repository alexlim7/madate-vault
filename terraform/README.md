# Mandate Vault - Google Cloud Infrastructure

This Terraform configuration deploys a secure, production-ready mandate vault system on Google Cloud Platform.

## Architecture

The infrastructure includes:

- **Cloud Run**: FastAPI service with auto-scaling
- **Cloud SQL**: Private PostgreSQL database with encryption
- **GCS Bucket**: Encrypted storage with versioning for application data
- **KMS**: Encryption keys for JWT verification cache and secrets
- **Secret Manager**: Secure storage for database credentials
- **VPC Service Controls**: Network isolation for Cloud SQL and GCS
- **Artifact Registry**: Private container registry
- **CI/CD**: GitHub Actions integration for automated deployments

## Security Features

- ✅ **No raw payment card data stored** - Enforced by data classification policies
- ✅ **Private Cloud SQL** - No public IP, VPC-only access
- ✅ **Encrypted storage** - GCS bucket encrypted with KMS
- ✅ **VPC Service Controls** - Network perimeter protection
- ✅ **Secret Manager** - Database credentials stored securely
- ✅ **KMS encryption** - JWT cache and secrets encrypted
- ✅ **Private GCS access** - Bucket access restricted to VPC

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **Required APIs enabled**:
   - Cloud Run API
   - Cloud SQL Admin API
   - Cloud Storage API
   - Cloud KMS API
   - Secret Manager API
   - Service Networking API
   - VPC Access API
   - Artifact Registry API
   - Cloud Build API

3. **Terraform** (version >= 1.0)
4. **gcloud CLI** configured with appropriate permissions

## Setup

### 1. Configure Variables

Copy the example variables file and update with your values:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
project_id       = "your-gcp-project-id"
region           = "us-central1"
environment      = "staging"
organization_id  = "your-gcp-organization-id"
github_owner     = "your-github-username"
github_repo      = "mandate-vault"
db_password      = "your-secure-db-password"
db_instance_tier = "db-f1-micro"
db_disk_size     = 20
```

### 2. Initialize Terraform

```bash
cd terraform
terraform init
```

### 3. Plan Deployment

```bash
terraform plan
```

### 4. Deploy Infrastructure

```bash
terraform apply
```

## CI/CD Setup

### 1. GitHub Secrets

Add the following secrets to your GitHub repository:

- `GCP_PROJECT_ID`: Your GCP project ID
- `GCP_SA_KEY`: Service account key JSON (for Cloud Build)
- `SLACK_WEBHOOK`: Slack webhook URL for notifications (optional)

### 2. Service Account Permissions

The Cloud Build service account needs the following roles:
- Cloud Run Admin
- IAM Service Account User
- Storage Admin
- Artifact Registry Admin

### 3. GitHub Actions

The workflow automatically:
- Runs tests and security scans
- Builds and pushes Docker images
- Deploys to Cloud Run
- Runs database migrations
- Performs health checks

## Environment Configuration

### Staging Environment
- Triggered by pushes to `develop` branch
- Uses staging-specific configurations
- Minimal resource allocation

### Production Environment
- Triggered by pushes to `main` branch
- Uses production-specific configurations
- Enhanced security and monitoring
- Higher resource allocation

## Database Migrations

Migrations are automatically run during deployment using Cloud Run Jobs:

1. A migration job is created with the latest image
2. The job runs `alembic upgrade head`
3. Database credentials are fetched from Secret Manager
4. Migration status is reported in the CI/CD pipeline

## Monitoring and Logging

- **Cloud Logging**: All application logs are automatically collected
- **Cloud Monitoring**: Service metrics and health checks
- **Error Reporting**: Automatic error tracking and alerting
- **Cloud Trace**: Distributed tracing for request flows

## Security Considerations

### Data Protection
- All data encrypted at rest and in transit
- Database connections use SSL/TLS
- Secrets stored in Secret Manager
- KMS encryption for sensitive data

### Network Security
- VPC Service Controls for network isolation
- Private IP addresses for Cloud SQL
- VPC Connector for Cloud Run
- No public database access

### Access Control
- Service accounts with minimal permissions
- IAM roles following principle of least privilege
- Secret Manager for credential management
- Cloud KMS for key management

## Troubleshooting

### Common Issues

1. **API Not Enabled**
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable sqladmin.googleapis.com
   # ... enable other required APIs
   ```

2. **Insufficient Permissions**
   ```bash
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="user:your-email@domain.com" \
     --role="roles/owner"
   ```

3. **VPC Service Controls Issues**
   - Ensure organization ID is correct
   - Verify VPC Service Controls API is enabled
   - Check network configuration

### Useful Commands

```bash
# Check service status
gcloud run services describe mandate-vault --region us-central1

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Check database connectivity
gcloud sql instances describe mandate-vault-postgres

# View secrets
gcloud secrets list
```

## Cost Optimization

- **Cloud Run**: Pay-per-request pricing with automatic scaling
- **Cloud SQL**: Use appropriate instance tiers for your workload
- **GCS**: Lifecycle policies for automatic data archival
- **KMS**: Key rotation policies for cost management

## Cleanup

To destroy the infrastructure:

```bash
cd terraform
terraform destroy
```

**Warning**: This will permanently delete all resources including databases and stored data.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review Cloud Logging for error messages
3. Consult the application documentation
4. Contact the development team


