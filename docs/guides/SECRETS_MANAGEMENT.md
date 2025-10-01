# Secrets Management Guide

Comprehensive guide for managing secrets securely in Mandate Vault across different environments and platforms.

---

## 🔐 Overview

**Never store secrets in plain text!** This guide shows how to manage secrets securely for development, staging, and production environments.

---

## 🎯 Quick Start

### Development

```bash
# Generate secure key
python scripts/generate_secret_key.py

# Create .env file
cp config/env.development.template .env

# Add generated key to .env
echo "SECRET_KEY=<generated-key>" >> .env

# Validate configuration
python scripts/validate_environment.py
```

### Production

```bash
# Use cloud secrets management (recommended)
# See platform-specific sections below

# OR use environment variables (less secure)
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db"
```

---

## 🔑 Secret Key Generation

### Generate Secure Keys

**Method 1: Using Our Script**
```bash
python scripts/generate_secret_key.py
```

**Method 2: Using Python**
```bash
# URL-safe key (recommended)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Hex key
python -c "import secrets; print(secrets.token_hex(32))"

# Custom length
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

**Method 3: Using OpenSSL**
```bash
openssl rand -base64 32
```

### Key Requirements

✅ **Minimum 32 characters**  
✅ **Cryptographically random** (use secrets module, not random)  
✅ **Unique per environment** (dev ≠ staging ≠ production)  
✅ **Rotated regularly** (every 90 days recommended)  

❌ **Never use:**
- Dictionary words
- Predictable patterns
- Same key across environments
- Committed to git

---

## ☁️ Cloud Secrets Management

### Google Cloud Platform (GCP)

**Setup Secret Manager:**
```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Create secrets
gcloud secrets create mandate-vault-secret-key \
  --data-file=- <<< "$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

gcloud secrets create mandate-vault-database-url \
  --data-file=- <<< "postgresql+asyncpg://user:pass@host:5432/db"

# Grant access to service account
gcloud secrets add-iam-policy-binding mandate-vault-secret-key \
  --member="serviceAccount:mandate-vault@PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**Access in Application:**
```python
from google.cloud import secretmanager

def get_secret(secret_id, project_id):
    """Get secret from Google Cloud Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode('UTF-8')

# Use in app
SECRET_KEY = get_secret('mandate-vault-secret-key', 'your-project-id')
```

**In Cloud Run:**
```bash
gcloud run deploy mandate-vault \
  --image gcr.io/PROJECT/mandate-vault \
  --update-secrets=SECRET_KEY=mandate-vault-secret-key:latest \
  --update-secrets=DATABASE_URL=mandate-vault-database-url:latest
```

### AWS (Amazon Web Services)

**Setup Secrets Manager:**
```bash
# Install AWS CLI
aws configure

# Create secret
aws secretsmanager create-secret \
  --name mandate-vault/secret-key \
  --secret-string "$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

aws secretsmanager create-secret \
  --name mandate-vault/database-url \
  --secret-string "postgresql+asyncpg://user:pass@rds:5432/db"
```

**Access in Application:**
```python
import boto3
import json

def get_secret(secret_name, region_name="us-east-1"):
    """Get secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager', region_name=region_name)
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# Use in app
SECRET_KEY = get_secret('mandate-vault/secret-key')
```

**In ECS/Fargate:**
```json
{
  "containerDefinitions": [{
    "secrets": [
      {
        "name": "SECRET_KEY",
        "valueFrom": "arn:aws:secretsmanager:region:account:secret:mandate-vault/secret-key"
      }
    ]
  }]
}
```

### Azure

**Setup Key Vault:**
```bash
# Create Key Vault
az keyvault create \
  --name mandate-vault-kv \
  --resource-group mandate-vault-rg \
  --location eastus

# Add secrets
az keyvault secret set \
  --vault-name mandate-vault-kv \
  --name secret-key \
  --value "$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

**Access in Application:**
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_secret(vault_url, secret_name):
    """Get secret from Azure Key Vault."""
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    return client.get_secret(secret_name).value

# Use in app
SECRET_KEY = get_secret('https://mandate-vault-kv.vault.azure.net/', 'secret-key')
```

---

## 🐳 Docker & Kubernetes

### Docker Secrets

**Create secret file:**
```bash
# Generate and save
python -c 'import secrets; print(secrets.token_urlsafe(32))' > secret_key.txt

# Initialize Docker Swarm
docker swarm init

# Create secret
docker secret create mandate_vault_secret_key secret_key.txt

# Remove plain text file
rm secret_key.txt
```

**Use in docker-compose.yml:**
```yaml
version: '3.8'
services:
  api:
    image: mandate-vault:latest
    secrets:
      - mandate_vault_secret_key
    environment:
      - SECRET_KEY_FILE=/run/secrets/mandate_vault_secret_key

secrets:
  mandate_vault_secret_key:
    external: true
```

### Kubernetes Secrets

**Create secret:**
```bash
# Generate secret
kubectl create secret generic mandate-vault-secrets \
  --from-literal=secret-key="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  --from-literal=database-url="postgresql+asyncpg://user:pass@db:5432/mandate"
```

**Use in deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mandate-vault
spec:
  template:
    spec:
      containers:
      - name: api
        image: mandate-vault:latest
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: mandate-vault-secrets
              key: secret-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mandate-vault-secrets
              key: database-url
```

**Using External Secrets Operator:**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: mandate-vault
spec:
  secretStoreRef:
    name: gcpsm-secret-store
    kind: SecretStore
  target:
    name: mandate-vault-secrets
  data:
  - secretKey: secret-key
    remoteRef:
      key: mandate-vault-secret-key
```

---

## 🔄 Secret Rotation

### Rotation Strategy

**Frequency:**
- Production: Every 90 days
- Staging: Every 180 days
- Development: Annually or on compromise

**Process:**

1. **Generate new secret**
```bash
NEW_SECRET=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
```

2. **Update secrets manager**
```bash
# GCP
gcloud secrets versions add mandate-vault-secret-key --data-file=- <<< "$NEW_SECRET"

# AWS
aws secretsmanager put-secret-value \
  --secret-id mandate-vault/secret-key \
  --secret-string "$NEW_SECRET"
```

3. **Deploy new version** (graceful rollout)

4. **Verify** old tokens still work (grace period)

5. **After grace period**, invalidate old tokens

### Automated Rotation

**Using AWS Secrets Manager:**
```python
# Lambda function for automatic rotation
import boto3

def lambda_handler(event, context):
    secret = secrets.token_urlsafe(32)
    
    client = boto3.client('secretsmanager')
    client.put_secret_value(
        SecretId='mandate-vault/secret-key',
        SecretString=secret
    )
    
    return {"statusCode": 200}
```

---

## 🏗️ Deployment Patterns

### Pattern 1: Environment Variables (Simple)

**Pros:** Simple, works everywhere  
**Cons:** Less secure, visible in process list  

```bash
export SECRET_KEY="your-key"
export DATABASE_URL="postgresql://..."
python -m uvicorn app.main:app
```

### Pattern 2: .env File (Development)

**Pros:** Easy local development  
**Cons:** File can be accidentally committed  

```bash
# .env
SECRET_KEY=dev-key
DATABASE_URL=sqlite:///test.db

# .gitignore (CRITICAL!)
.env
.env.local
.env.*.local
```

### Pattern 3: Secrets Management Service (Production)

**Pros:** Most secure, audit trail, rotation  
**Cons:** More complex setup  

Use GCP Secret Manager, AWS Secrets Manager, or Azure Key Vault (see above).

### Pattern 4: HashiCorp Vault (Enterprise)

```bash
# Store secret
vault kv put secret/mandate-vault secret_key="..."

# Access in app
vault kv get -field=secret_key secret/mandate-vault
```

---

## 🔒 Best Practices

### DO ✅

1. **Use secrets management service** in production
2. **Rotate secrets regularly** (90 days)
3. **Different secrets per environment**
4. **Minimum 32 characters** for SECRET_KEY
5. **Use environment variables** not config files
6. **Audit secret access**
7. **Encrypt secrets at rest**
8. **Use TLS/SSL** for secrets in transit

### DON'T ❌

1. **Commit secrets to git**
2. **Log secrets**
3. **Expose in error messages**
4. **Store in plain text**
5. **Reuse across environments**
6. **Use weak/predictable keys**
7. **Share secrets via email/Slack**

---

## 🚨 Security Incidents

### If Secret Key is Compromised

**Immediate Actions:**

1. **Generate new secret**
```bash
NEW_KEY=$(python scripts/generate_secret_key.py)
```

2. **Update in secrets manager**

3. **Deploy with new secret**

4. **Invalidate all existing tokens**

5. **Force all users to re-authenticate**

6. **Audit access logs** for suspicious activity

7. **Notify affected customers** (if data breach)

### If Database Credentials Compromised

1. **Change database password immediately**
2. **Rotate database connection strings**
3. **Review database audit logs**
4. **Check for unauthorized access**
5. **Update firewall rules**

---

## 📚 References

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [12-Factor App: Config](https://12factor.net/config)
- [Google Cloud Secret Manager](https://cloud.google.com/secret-manager/docs)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [Azure Key Vault](https://docs.microsoft.com/en-us/azure/key-vault/)

---

**Last Updated:** October 2025  
**Version:** 1.0.0

