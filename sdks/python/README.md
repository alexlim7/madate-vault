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

# Create a mandate
mandate = client.mandates.create(
    vc_jwt='eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...',
    tenant_id='your-tenant-id'
)

print(f"Mandate created: {mandate['id']}")
print(f"Status: {mandate['verification_status']}")
```

## Usage Examples

### Search Mandates

```python
# Search for mandates
results = client.mandates.search(
    tenant_id='your-tenant-id',
    issuer_did='did:web:bank.example.com',
    status='active',
    limit=50
)

for mandate in results['mandates']:
    print(f"{mandate['id']}: {mandate['subject_did']}")
```

### Get Mandate by ID

```python
mandate = client.mandates.get('mandate-123')
print(f"Issuer: {mandate['issuer_did']}")
print(f"Scope: {mandate['scope']}")
```

### Revoke Mandate

```python
revoked = client.mandates.revoke('mandate-123')
print(f"Revoked at: {revoked['updated_at']}")
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

