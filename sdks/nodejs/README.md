# Mandate Vault Node.js SDK

Official Node.js/TypeScript client library for the Mandate Vault API.

## Installation

```bash
npm install mandate-vault
# or
yarn add mandate-vault
```

## Quick Start

### JavaScript

```javascript
const { MandateVaultClient } = require('mandate-vault');

const client = new MandateVaultClient({
  apiKey: 'mvk_your_api_key_here'
});

// Create a mandate
const mandate = await client.mandates.create({
  vcJwt: 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...',
  tenantId: 'your-tenant-id'
});

console.log(`Mandate created: ${mandate.id}`);
```

### TypeScript

```typescript
import { MandateVaultClient, Mandate } from 'mandate-vault';

const client = new MandateVaultClient({
  apiKey: 'mvk_your_api_key_here'
});

const mandate: Mandate = await client.mandates.create({
  vcJwt: 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...',
  tenantId: 'your-tenant-id'
});
```

## Usage Examples

### Search Mandates

```typescript
const results = await client.mandates.search({
  tenantId: 'your-tenant-id',
  issuerDid: 'did:web:bank.example.com',
  status: 'active',
  limit: 50
});

results.mandates.forEach(mandate => {
  console.log(`${mandate.id}: ${mandate.subject_did}`);
});
```

### Get Mandate by ID

```typescript
const mandate = await client.mandates.get('mandate-123');
console.log(`Issuer: ${mandate.issuer_did}`);
```

### Revoke Mandate

```typescript
const revoked = await client.mandates.revoke('mandate-123');
console.log(`Revoked at: ${revoked.updated_at}`);
```

### Create Webhook

```typescript
const webhook = await client.webhooks.create({
  name: 'My Webhook',
  url: 'https://your-app.com/webhooks/mandates',
  events: ['MandateCreated', 'MandateVerificationFailed'],
  secret: 'your-webhook-secret',
  tenantId: 'your-tenant-id'
});
```

### Get Audit Logs

```typescript
const logs = await client.audit.list({
  tenantId: 'your-tenant-id',
  eventType: 'CREATE',
  limit: 100
});

logs.forEach(log => {
  console.log(`${log.timestamp}: ${log.event_type}`);
});
```

## Error Handling

```typescript
import {
  MandateVaultClient,
  AuthenticationError,
  ValidationError,
  NotFoundError,
  RateLimitError
} from 'mandate-vault';

try {
  const mandate = await client.mandates.get('mandate-123');
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Invalid API key');
  } else if (error instanceof NotFoundError) {
    console.error('Mandate not found');
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limited. Retry after ${error.retryAfter} seconds`);
  } else if (error instanceof ValidationError) {
    console.error(`Validation error: ${error.message}`);
  }
}
```

## Configuration

### Custom Base URL

```typescript
const client = new MandateVaultClient({
  apiKey: 'mvk_...',
  baseUrl: 'https://staging-api.mandatevault.com'
});
```

### Custom Timeout

```typescript
const client = new MandateVaultClient({
  apiKey: 'mvk_...',
  timeout: 60000  // 60 seconds
});
```

## TypeScript Support

This SDK is written in TypeScript and includes full type definitions:

```typescript
import type { Mandate, MandateSearchParams, Webhook } from 'mandate-vault';

const params: MandateSearchParams = {
  tenantId: 'your-tenant-id',
  limit: 50
};
```

## Documentation

- [Full API Reference](https://docs.mandatevault.com/api)
- [Onboarding Guide](https://docs.mandatevault.com/onboarding)
- [Examples](https://github.com/mandate-vault/examples)

## Support

- Email: support@mandatevault.com
- GitHub Issues: https://github.com/mandate-vault/nodejs-sdk/issues

## License

MIT License - see LICENSE file for details.

