# Mandate Vault Python SDK

Official Python client library for the Mandate Vault API.

## Installation

```bash
pip install mandate-vault
```

## Quick Start

```python
from mandate_vault import MandateVaultClient

# Initialize client
client = MandateVaultClient(api_key='mvk_your_api_key_here')

# Create an ACP authorization (NEW - multi-protocol)
authorization = client.authorizations.create(
    protocol='ACP',
    payload={
        'token_id': 'acp-token-123',
        'psp_id': 'psp-stripe',
        'merchant_id': 'merchant-456',
        'max_amount': '5000.00',
        'currency': 'USD',
        'expires_at': '2026-01-01T00:00:00Z',
        'constraints': {}
    },
    tenant_id='your-tenant-id'
)

print(f"Authorization created: {authorization['id']}")
print(f"Protocol: {authorization['protocol']}")
print(f"Status: {authorization['status']}")
```

## Usage Examples

### Create AP2 (JWT-VC) Authorization

```python
# Using new authorizations API (recommended)
auth = client.authorizations.create(
    protocol='AP2',
    payload={'vc_jwt': 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...'},
    tenant_id='your-tenant-id'
)
```

### Search Authorizations

```python
# Advanced search with filters
results = client.authorizations.search(
    tenant_id='your-tenant-id',
    protocol='ACP',  # Filter by protocol
    status='VALID',
    currency='USD',
    min_amount='1000.00',
    limit=50
)

print(f"Found {results['total']} authorizations")
for auth in results['authorizations']:
    print(f"{auth['id']}: {auth['protocol']} - {auth['issuer']}")
```

### Re-verify Authorization

```python
# Re-run verification on existing authorization
result = client.authorizations.verify('auth-123')
print(f"Verification status: {result['status']}")
print(f"Reason: {result['reason']}")
```

### Export Evidence Pack

```python
# Download evidence pack as ZIP
path = client.authorizations.export_evidence_pack(
    authorization_id='auth-123',
    output_path='./evidence_pack.zip'
)
print(f"Evidence pack saved to {path}")
```

### Revoke Authorization

```python
revoked = client.authorizations.revoke('auth-123')
print(f"Revoked: {revoked['status']}")
```

---

## Legacy Mandate API (Deprecated)

⚠️ **The `/mandates` endpoints are deprecated. Use `client.authorizations` for new code.**

### Create Mandate (AP2 only)

```python
# DEPRECATED - Use client.authorizations.create() instead
mandate = client.mandates.create(
    vc_jwt='eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...',
    tenant_id='your-tenant-id'
)
```

### Search Mandates

```python
# DEPRECATED - Use client.authorizations.search() instead
results = client.mandates.search(
    tenant_id='your-tenant-id',
    issuer_did='did:web:bank.example.com',
    status='active',
    limit=50
)
```

### Create Webhook

```python
webhook = client.webhooks.create(
    name='My Webhook',
    url='https://your-app.com/webhooks/mandates',
    events=['MandateCreated', 'MandateVerificationFailed'],
    secret='your-webhook-secret',
    tenant_id='your-tenant-id'
)
```

### Get Audit Logs

```python
logs = client.audit.list(
    tenant_id='your-tenant-id',
    event_type='CREATE',
    limit=100
)

for log in logs:
    print(f"{log['timestamp']}: {log['event_type']}")
```

## Error Handling

```python
from mandate_vault import (
    MandateVaultClient,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    RateLimitError
)

client = MandateVaultClient(api_key='mvk_...')

try:
    mandate = client.mandates.get('mandate-123')
except AuthenticationError:
    print("Invalid API key")
except NotFoundError:
    print("Mandate not found")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except ValidationError as e:
    print(f"Validation error: {e.message}")
```

## Configuration

### Custom Base URL

```python
# For staging/development
client = MandateVaultClient(
    api_key='mvk_...',
    base_url='https://staging-api.mandatevault.com'
)
```

### Custom Timeout

```python
client = MandateVaultClient(
    api_key='mvk_...',
    timeout=60  # 60 seconds
)
```

## Documentation

- [Full API Reference](https://docs.mandatevault.com/api)
- [Onboarding Guide](https://docs.mandatevault.com/onboarding)
- [Examples](https://github.com/mandate-vault/examples)

## Support

- Email: support@mandatevault.com
- GitHub Issues: https://github.com/mandate-vault/python-sdk/issues

## License

MIT License - see LICENSE file for details.

