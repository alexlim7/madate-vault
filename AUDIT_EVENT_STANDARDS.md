# Audit Event Standards

This document defines the standardized audit event types used across all protocols (AP2, ACP) in the Mandate Vault system.

## Standard Event Types

All audit logs MUST use one of these standardized event types:

| Event Type | Description | When Used | Protocols |
|------------|-------------|-----------|-----------|
| `CREATED` | Authorization created | When a new authorization is stored | AP2, ACP |
| `VERIFIED` | Authorization verified | When verification is performed | AP2, ACP |
| `USED` | Authorization used | When authorization is used for transaction | ACP (via webhook) |
| `REVOKED` | Authorization revoked | When authorization is revoked/deleted | AP2, ACP |
| `EXPORTED` | Evidence pack generated | When evidence pack is downloaded | AP2, ACP |

## Structured Details Schema

Each event type has a standardized details structure:

### CREATED

```json
{
  "protocol": "AP2|ACP",
  "issuer": "issuer_did or psp_id",
  "subject": "subject_did or merchant_id",
  "scope": {...},
  "amount_limit": "1000.00",
  "currency": "USD",
  "verification_status": "VALID|EXPIRED|...",
  "user_id": "user-uuid",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0..."
}
```

**AP2-specific fields:**
- `issuer` = DID
- `subject` = DID
- `scope` = `{"scope": "payment.recurring"}`

**ACP-specific fields:**
- `psp_id` = PSP identifier
- `merchant_id` = Merchant identifier
- `token_id` = Unique token ID
- `max_amount` = Maximum amount
- `constraints` = Constraint object

---

### VERIFIED

```json
{
  "protocol": "AP2|ACP",
  "verification_status": "VALID|EXPIRED|REVOKED|...",
  "verification_reason": "Token verified successfully",
  "verification_details": {...},
  "authorization_id": "auth-uuid",
  "old_status": "ACTIVE",
  "new_status": "VALID",
  "user_id": "user-uuid",
  "ip_address": "192.168.1.1"
}
```

---

### USED

**ACP Only** - Triggered by `token.used` webhook

```json
{
  "protocol": "ACP",
  "actor_id": "acp-system",
  "resource_type": "authorization",
  "resource_id": "auth-uuid",
  "action": "token_used",
  "token_id": "acp-token-123",
  "amount": "50.00",
  "currency": "USD",
  "transaction_id": "txn_xyz789",
  "merchant_id": "merchant-acme",
  "metadata": {...},
  "tenant_id": "tenant-uuid",
  "status": "SUCCESS",
  "reason": "ACP token used for transaction txn_xyz789"
}
```

---

### REVOKED

```json
{
  "protocol": "AP2|ACP",
  "issuer": "issuer_did or psp_id",
  "subject": "subject_did or merchant_id",
  "reason": "User requested revocation",
  "user_id": "user-uuid",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0..."
}
```

**From ACP Webhook:**
```json
{
  "protocol": "ACP",
  "actor_id": "user-123",
  "resource_type": "authorization",
  "resource_id": "auth-uuid",
  "action": "token_revoked",
  "token_id": "acp-token-123",
  "old_status": "VALID",
  "new_status": "REVOKED",
  "reason": "User requested cancellation",
  "revoked_by": "user-123",
  "tenant_id": "tenant-uuid",
  "status": "SUCCESS"
}
```

---

### EXPORTED

```json
{
  "protocol": "AP2|ACP",
  "export_type": "evidence_pack",
  "user_id": "user-uuid",
  "user_email": "user@example.com",
  "ip_address": "192.168.1.1",
  "filename": "evidence_pack_AP2_abc12345_20251001_143000.zip",
  "authorization_id": "auth-uuid",
  "issuer": "issuer_did or psp_id",
  "subject": "subject_did or merchant_id",
  "status": "VALID|REVOKED|..."
}
```

---

## Code Locations

### Where Events Are Logged

| Event | File | Function/Endpoint |
|-------|------|-------------------|
| `CREATED` | `app/api/v1/endpoints/authorizations.py` | `create_authorization()` |
| `VERIFIED` | `app/api/v1/endpoints/authorizations.py` | `create_authorization()` (pre-verification) |
| `VERIFIED` | `app/api/v1/endpoints/authorizations.py` | `verify_authorization_endpoint()` (re-verification) |
| `USED` | `app/api/v1/endpoints/acp_webhooks.py` | `handle_token_used()` |
| `REVOKED` | `app/api/v1/endpoints/authorizations.py` | `revoke_authorization()` |
| `REVOKED` | `app/api/v1/endpoints/acp_webhooks.py` | `handle_token_revoked()` |
| `EXPORTED` | `app/api/v1/endpoints/authorizations.py` | `get_evidence_pack()` |

---

## Migration Notes

### Deprecated Event Types

The following event types have been **deprecated** and replaced:

| Old Event Type | New Event Type | Notes |
|---------------|----------------|-------|
| `CREATE` | `CREATED` | Past tense for consistency |
| `VERIFY` | `VERIFIED` | Past tense for consistency |
| `REVOKE` | `REVOKED` | Past tense for consistency |
| `EVIDENCE_PACK_GENERATED` | `EXPORTED` | Shorter, more generic |

### Backward Compatibility

For backward compatibility, queries should check for both old and new event types:

```python
# Example: Query for creation events
result = await db.execute(
    select(AuditLog).where(
        AuditLog.event_type.in_(['CREATED', 'CREATE'])  # Support both
    )
)
```

---

## Testing

All event types are tested in:
- `tests/test_acp_verification.py` - VERIFIED
- `tests/test_authorization_search.py` - Search audit trail
- `tests/test_acp_webhooks.py` - USED, REVOKED (webhook)
- `tests/test_evidence_pack.py` - EXPORTED

---

## Best Practices

### When Logging Events

1. **Always include `protocol`** - Essential for multi-protocol queries
2. **Include user context** - `user_id`, `user_email`, `ip_address` when available
3. **Include resource IDs** - `authorization_id`, `token_id`, `resource_id`
4. **Use structured data** - JSON objects, not strings
5. **Include timestamps** - Use ISO 8601 format
6. **Add status** - Include `old_status` and `new_status` for state changes

### Example: Logging a CREATED Event

```python
await audit_service.log_event(
    mandate_id=str(authorization.id),
    event_type="CREATED",  # Use standard type
    details={
        "protocol": authorization.protocol,  # Required
        "issuer": authorization.issuer,
        "subject": authorization.subject,
        "amount_limit": str(authorization.amount_limit),
        "currency": authorization.currency,
        "verification_status": authorization.verification_status,
        "user_id": current_user.id,  # User context
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent")
    }
)
```

---

## Querying Audit Logs

### By Event Type

```python
# Get all CREATED events
result = await db.execute(
    select(AuditLog).where(
        AuditLog.event_type == "CREATED"
    )
)
```

### By Protocol

```python
# Get all ACP events
result = await db.execute(
    select(AuditLog).where(
        AuditLog.details['protocol'].astext == 'ACP'
    )
)
```

### By Authorization

```python
# Get all events for an authorization
result = await db.execute(
    select(AuditLog).where(
        AuditLog.mandate_id == authorization_id
    )
)
```

---

## Compliance & Reporting

### Required Events for Compliance

For each authorization, the following audit trail should exist:

1. **`CREATED`** - When authorization was stored
2. **`VERIFIED`** - When verification was performed
3. **`USED`** (ACP only) - When authorization was used (from webhooks)
4. **`REVOKED`** (if applicable) - When authorization was revoked
5. **`EXPORTED`** (if applicable) - When evidence pack was generated

### Evidence Pack Contents

All evidence packs include `audit.json` with complete event history, ensuring compliance with:
- PCI DSS audit requirements
- GDPR data access requests
- SOC 2 audit trails
- Regulatory reporting

---

**Version:** 1.0  
**Last Updated:** 2025-10-01  
**Status:** ✅ Production Ready


