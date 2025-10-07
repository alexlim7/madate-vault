# Migration Guide: /mandates → /authorizations

## Overview

This guide helps you migrate from the deprecated `/mandates` endpoints to the new multi-protocol `/authorizations` endpoints.

**Timeline:**
- **Now (v1.x)**: `/mandates` endpoints are deprecated but fully functional
- **Q2 2026 (v2.0)**: `/mandates` endpoints will be removed

**Why Migrate?**
- ✅ Multi-protocol support (AP2 + ACP)
- ✅ Advanced search capabilities
- ✅ Evidence pack export
- ✅ Enhanced monitoring metrics
- ✅ Future-proof architecture

---

## Quick Migration Reference

| Old Endpoint (Deprecated) | New Endpoint | Notes |
|---------------------------|--------------|-------|
| `POST /api/v1/mandates` | `POST /api/v1/authorizations` | Add `protocol: "AP2"` |
| `GET /api/v1/mandates/{id}` | `GET /api/v1/authorizations/{id}` | Returns same data structure |
| `POST /api/v1/mandates/search` | `POST /api/v1/authorizations/search` | Enhanced with more filters |
| `DELETE /api/v1/mandates/{id}` | `DELETE /api/v1/authorizations/{id}` | Marks as REVOKED |

---

## Step-by-Step Migration

### 1. Creating Authorizations (AP2)

**Old Way (Deprecated):**
```bash
POST /api/v1/mandates
{
  "vc_jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tenant_id": "tenant-123"
}
```

**New Way:**
```bash
POST /api/v1/authorizations
{
  "protocol": "AP2",
  "payload": {
    "vc_jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
  },
  "tenant_id": "tenant-123"
}
```

**Response (Same Structure):**
```json
{
  "id": "auth-abc123",
  "protocol": "AP2",
  "issuer": "did:example:issuer123",
  "subject": "did:example:user456",
  "status": "VALID",
  "expires_at": "2026-12-31T23:59:59Z",
  "amount_limit": "500.00",
  "verification_status": "VALID",
  "created_at": "2025-10-01T12:00:00Z"
}
```

### 2. Retrieving Authorizations

**Old Way:**
```bash
GET /api/v1/mandates/{id}
```

**New Way (Identical Response):**
```bash
GET /api/v1/authorizations/{id}
```

### 3. Searching Authorizations

**Old Way:**
```bash
POST /api/v1/mandates/search
{
  "tenant_id": "tenant-123",
  "issuer_did": "did:example:issuer",
  "status": "active",
  "limit": 50,
  "offset": 0
}
```

**New Way (Enhanced):**
```bash
POST /api/v1/authorizations/search
{
  "tenant_id": "tenant-123",
  "protocol": "AP2",
  "issuer": "did:example:issuer",
  "status": "VALID",
  "expires_after": "2025-10-01T00:00:00Z",
  "min_amount": "100.00",
  "limit": 50,
  "offset": 0,
  "sort_by": "created_at",
  "sort_order": "desc"
}
```

**New Features:**
- Protocol filtering (`protocol: "AP2"`)
- Date range queries (`expires_before`, `expires_after`, `created_after`)
- Amount filtering (`min_amount`, `max_amount`, `currency`)
- JSON path queries (`scope_merchant`, `scope_category`)
- Sorting options (`sort_by`, `sort_order`)

### 4. Revoking Authorizations

**Old Way:**
```bash
DELETE /api/v1/mandates/{id}
```

**New Way (Same Behavior):**
```bash
DELETE /api/v1/authorizations/{id}
```

---

## Code Examples

### Python SDK Migration

**Old Code:**
```python
from mandate_vault import MandateVaultClient

client = MandateVaultClient(api_key="your-key")

# Create mandate
mandate = client.mandates.create(
    vc_jwt="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    tenant_id="tenant-123"
)

# Search mandates
results = client.mandates.search(
    tenant_id="tenant-123",
    issuer_did="did:example:issuer"
)
```

**New Code:**
```python
from mandate_vault import MandateVaultClient

client = MandateVaultClient(api_key="your-key")

# Create authorization (AP2)
authorization = client.authorizations.create(
    protocol="AP2",
    payload={
        "vc_jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    },
    tenant_id="tenant-123"
)

# Search authorizations (enhanced)
results = client.authorizations.search(
    tenant_id="tenant-123",
    protocol="AP2",
    issuer="did:example:issuer",
    min_amount="100.00",
    sort_by="created_at",
    sort_order="desc"
)
```

### Node.js SDK Migration

**Old Code:**
```javascript
const { MandateVaultClient } = require('@mandate-vault/sdk');

const client = new MandateVaultClient({ apiKey: 'your-key' });

// Create mandate
const mandate = await client.mandates.create({
  vcJwt: 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...',
  tenantId: 'tenant-123'
});

// Search mandates
const results = await client.mandates.search({
  tenantId: 'tenant-123',
  issuerDid: 'did:example:issuer'
});
```

**New Code:**
```javascript
const { MandateVaultClient } = require('@mandate-vault/sdk');

const client = new MandateVaultClient({ apiKey: 'your-key' });

// Create authorization (AP2)
const authorization = await client.authorizations.create({
  protocol: 'AP2',
  payload: {
    vcJwt: 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...'
  },
  tenantId: 'tenant-123'
});

// Search authorizations (enhanced)
const results = await client.authorizations.search({
  tenantId: 'tenant-123',
  protocol: 'AP2',
  issuer: 'did:example:issuer',
  minAmount: '100.00',
  sortBy: 'created_at',
  sortOrder: 'desc'
});
```

---

## Migration Checklist

### Phase 1: Preparation (Week 1)
- [ ] Review current `/mandates` usage patterns
- [ ] Identify all systems calling `/mandates` endpoints
- [ ] Review new `/authorizations` API documentation
- [ ] Update SDK dependencies to latest version
- [ ] Test new endpoints in staging environment

### Phase 2: Implementation (Weeks 2-4)
- [ ] Update API calls to use `/authorizations`
- [ ] Add `protocol: "AP2"` to all requests
- [ ] Update response parsing (if needed)
- [ ] Implement new search filters (optional but recommended)
- [ ] Test evidence pack export functionality

### Phase 3: Verification (Week 5)
- [ ] Run integration tests
- [ ] Verify data consistency
- [ ] Check monitoring dashboards
- [ ] Validate webhook delivery
- [ ] Review audit logs

### Phase 4: Cleanup (Week 6)
- [ ] Remove old `/mandates` code
- [ ] Update documentation
- [ ] Train team on new endpoints
- [ ] Monitor for errors

---

## Database Changes

**Good News:** No database migration required! The new `/authorizations` endpoints use the same underlying data.

**Behind the Scenes:**
- Old `/mandates` endpoints write to `authorizations` table with `protocol='AP2'`
- `mandate_view` provides backward compatibility for legacy queries
- All audit logs are preserved
- Webhook events continue to work

---

## Troubleshooting

### Issue: "Missing protocol field"
**Error:** `{"detail": "Field required: protocol"}`

**Solution:**
```json
{
  "protocol": "AP2",  // ← Add this field
  "payload": {
    "vc_jwt": "..."
  },
  "tenant_id": "tenant-123"
}
```

### Issue: "Invalid payload structure"
**Error:** `{"detail": "Field required: payload.vc_jwt"}`

**Solution:** Wrap JWT in `payload` object:
```json
{
  "protocol": "AP2",
  "payload": {          // ← Wrap in payload
    "vc_jwt": "..."
  },
  "tenant_id": "tenant-123"
}
```

### Issue: Search returns no results
**Problem:** Old `issuer_did` field doesn't work in new search

**Solution:** Use `issuer` instead:
```json
{
  "tenant_id": "tenant-123",
  "issuer": "did:example:issuer",  // ← Use 'issuer' not 'issuer_did'
  "protocol": "AP2"
}
```

---

## Backward Compatibility

During the deprecation period (until v2.0):
- ✅ Old `/mandates` endpoints continue to work
- ✅ Data is automatically stored in new format
- ✅ Both endpoint styles access same data
- ✅ No data loss or migration required
- ✅ Webhooks continue to function

**Recommendation:** Migrate as soon as possible to take advantage of new features.

---

## New Features You'll Get

### 1. Multi-Protocol Support
Add ACP (delegated tokens) alongside AP2:
```json
{
  "protocol": "ACP",
  "payload": {
    "token_id": "acp-token-123",
    "psp_id": "psp-stripe",
    "merchant_id": "merchant-acme",
    "max_amount": "5000.00",
    "currency": "USD",
    "expires_at": "2026-01-31T23:59:59Z"
  },
  "tenant_id": "tenant-123"
}
```

### 2. Evidence Pack Export
```bash
GET /api/v1/authorizations/{id}/evidence-pack
```
Returns a ZIP file with:
- Raw credential/token data
- Verification results
- Complete audit trail
- Human-readable summary

### 3. Advanced Search
```json
{
  "tenant_id": "tenant-123",
  "protocol": "AP2",
  "expires_before": "2026-12-31T23:59:59Z",
  "min_amount": "1000.00",
  "currency": "USD",
  "scope_merchant": "merchant-acme",
  "sort_by": "created_at",
  "sort_order": "desc",
  "limit": 100
}
```

### 4. Re-Verification
```bash
POST /api/v1/authorizations/{id}/verify
```
Re-run verification checks on demand.

---

## Support

Need help with migration?

- 📧 **Email**: support@mandatevault.com
- 📚 **Documentation**: https://docs.mandatevault.com
- 💬 **Slack**: #mandate-vault-support
- 🐛 **Issues**: https://github.com/mandate-vault/api/issues

---

## FAQ

**Q: When will `/mandates` be removed?**
A: Q2 2026 (v2.0 release)

**Q: Do I need to migrate my data?**
A: No, data is automatically compatible.

**Q: Will my webhooks break?**
A: No, webhooks continue to work with both endpoints.

**Q: Can I use both endpoints during migration?**
A: Yes, both access the same data.

**Q: What about my SDK version?**
A: Update to the latest SDK version for full support.

**Q: Do I lose any functionality?**
A: No, you gain new features while keeping all existing functionality.

---

**Updated:** October 2025  
**Version:** 1.0


