# Multi-Protocol Refactor Progress

Track progress on adding ACP support alongside AP2.

---

## ✅ **PHASE 1: DATABASE & TYPES - COMPLETE** (8/8 files)

### Completed Files

#### 1. Migration ✅
**File:** `alembic/versions/005_add_authorizations_table.py`

**What it does:**
- Creates `authorizations` table with protocol support
- Adds CHECK constraints for protocol ('AP2', 'ACP') and status
- Creates 10 indexes for performance
- Backfills existing mandates as AP2 protocol
- Creates `mandate_view` for backward compatibility
- Adds triggers for updated_at
- Marks `mandates` table as deprecated

#### 2. Shared Types ✅
**File:** `app/services/types.py`

**What it includes:**
- `VerificationStatus` enum (protocol-agnostic)
- `VerificationResult` class (shared across protocols)
- `to_dict()` method for serialization
- Clean, documented interface

#### 3. Verification Dispatcher ✅
**File:** `app/services/verification_dispatcher.py`

**What it does:**
- Routes verification to AP2 or ACP based on protocol
- Delegates to existing `verification_service` for AP2
- Includes ACP stub (to be implemented)
- Converts between old and new VerificationResult types
- Singleton pattern for easy access

**Usage:**
```python
from app.services.verification_dispatcher import verify_authorization

result = await verify_authorization(
    payload={'vc_jwt': 'eyJhbGc...'},
    protocol='AP2'
)
```

#### 6. ACP Protocol Schemas ✅
**Files:** 
- `app/protocols/__init__.py`
- `app/protocols/acp/__init__.py`
- `app/protocols/acp/schemas.py`

**What it includes:**
- `ACPDelegatedToken` - Pydantic model for ACP tokens
- `ACPConstraints` - Constraint validation
- Strict validation:
  - ✅ Currency: ISO 4217 codes only
  - ✅ Expiration: Must be in future
  - ✅ Amount: Max 2 decimal places, positive
  - ✅ Identifiers: XSS protection, no dangerous chars
  - ✅ Extra fields: Forbidden (strict mode)
- `from_dict()` - Create from dictionary
- `to_authorization_data()` - Convert to Authorization model format

**Example:**
```python
from app.protocols.acp.schemas import ACPDelegatedToken

token = ACPDelegatedToken(
    token_id="acp-123",
    psp_id="psp-456",
    merchant_id="merchant-789",
    max_amount=Decimal("5000.00"),
    currency="USD",
    expires_at=datetime(2026, 1, 1),
    constraints={"category": "retail"}
)
```

**Key Features:**
```sql
CREATE TABLE authorizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol TEXT CHECK (protocol IN ('AP2','ACP')),
    issuer TEXT NOT NULL,
    subject TEXT NOT NULL,
    scope JSONB,
    amount_limit NUMERIC(18,2),
    currency TEXT,
    expires_at TIMESTAMP NOT NULL,
    status TEXT CHECK (status IN ('VALID','EXPIRED','REVOKED','ACTIVE')),
    raw_payload JSONB NOT NULL,
    ...
);

CREATE VIEW mandate_view AS
    SELECT ... FROM authorizations WHERE protocol = 'AP2';
```

#### 2. Authorization Model ✅
**File:** `app/models/authorization.py`

**What it includes:**
- `Authorization` SQLAlchemy model
- `ProtocolType` enum (AP2, ACP)
- `AuthorizationStatus` enum (VALID, EXPIRED, REVOKED, ACTIVE)
- `to_dict()` method for JSON serialization
- `to_ap2_format()` method for backward compatibility
- `to_acp_format()` method for ACP-specific format
- Composite indexes for performance

**Usage:**
```python
from app.models import Authorization, ProtocolType

# Create AP2 authorization
auth = Authorization(
    protocol=ProtocolType.AP2,
    issuer="did:web:bank.com",
    subject="did:example:customer",
    scope={"scope": "payment.recurring"},
    ...
)

# Create ACP authorization
auth = Authorization(
    protocol=ProtocolType.ACP,
    issuer="psp-123",
    subject="merchant-456",
    scope={"constraints": {...}},
    ...
)
```

#### 3. Model Exports ✅
**File:** `app/models/__init__.py`

**Changes:**
- Exported `Authorization` model
- Exported `ProtocolType` enum
- Exported `AuthorizationStatus` enum
- Marked `Mandate` as DEPRECATED
- Maintains backward compatibility

#### 4. Mandate Model Deprecation ✅
**File:** `app/models/mandate.py`

**Changes:**
- Added deprecation warnings in module docstring
- Added deprecation warnings in class docstring
- Added TODO with removal target (v2.0, Q2 2026)
- Added comments pointing to Authorization model
- **All existing functionality preserved**

---

## 📊 **VERIFICATION**

### Model Import Test ✅
```bash
✓ Authorization model imported
✓ ProtocolType enum: ['AP2', 'ACP']
✓ AuthorizationStatus enum: ['VALID', 'EXPIRED', 'REVOKED', 'ACTIVE']
✓ Mandate model (deprecated) still accessible
```

### Backward Compatibility ✅
- Old `Mandate` model still works
- Can import both models simultaneously
- No breaking changes to existing code
- All enums accessible

---

## 📋 **NEXT PHASES**

### Phase 2: Protocol Abstraction Layer (Not Started)

**Files to Create:**
```
[ ] app/services/protocols/__init__.py
[ ] app/services/protocols/base_protocol.py
[ ] app/services/protocols/ap2_protocol.py
[ ] app/services/protocols/acp_protocol.py
```

**Purpose:**
- Define protocol interface
- Extract existing AP2 logic
- Implement new ACP logic
- Create protocol factory

### Phase 3: Service Layer Updates (Not Started)

**Files to Modify:**
```
[ ] app/services/verification_service.py
[ ] app/services/mandate_service.py
[ ] app/services/truststore_service.py
```

**Changes:**
- Use protocol factory for verification
- Support Authorization model
- Maintain Mandate compatibility
- Add protocol routing

### Phase 4: API Layer Updates (Not Started)

**Files to Modify:**
```
[ ] app/api/v1/endpoints/mandates.py
[ ] app/api/v1/router.py
[ ] app/schemas/mandate.py
```

**Files to Create:**
```
[ ] app/api/v1/endpoints/protocols.py
[ ] app/schemas/protocol.py
```

**Changes:**
- Accept protocol_type parameter
- Support both vc_jwt and credential fields
- Add protocol info endpoints
- Update request/response schemas

### Phase 5: Utilities & Detection (Not Started)

**Files to Create:**
```
[ ] app/utils/acp_verification.py
[ ] app/utils/protocol_detector.py
```

### Phase 6: Testing (Not Started)

**Files to Create:**
```
[ ] tests/test_acp_verification.py
[ ] tests/test_protocol_detection.py
[ ] tests/test_multiprotocol_integration.py
[ ] tests/integration/test_acp_flow.py
```

**Files to Modify:**
```
[ ] tests/test_verification.py
[ ] tests/test_mandate_api_additional.py
[ ] tests/integration/test_mandate_flow_integration.py
```

### Phase 7: Documentation (Not Started)

**Files to Create:**
```
[ ] docs/guides/MULTI_PROTOCOL_GUIDE.md
[ ] docs/guides/ACP_INTEGRATION_GUIDE.md
```

---

## 📊 **OVERALL PROGRESS**

```
Phase 1: Database & Types        ✅ COMPLETE (8/8 files)
  ├─ Migration                   ✅ (1 file)
  ├─ Models                      ✅ (2 files)  
  ├─ Shared Types                ✅ (1 file)
  ├─ Dispatcher                  ✅ (1 file)
  └─ ACP Schemas                 ✅ (3 files)

Phase 2: Protocol Abstraction    ⏳ NOT STARTED (0/4 files)
Phase 3: Service Layer           ⏳ NOT STARTED (0/3 files)
Phase 4: API Layer               ⏳ NOT STARTED (0/5 files)
Phase 5: Utilities               ⏳ NOT STARTED (0/2 files)
Phase 6: Testing                 ⏳ NOT STARTED (0/7 files)
Phase 7: Documentation           ⏳ NOT STARTED (0/2 files)
─────────────────────────────────────────────────
Total Progress:                  8/31 files (26%)
```

---

## ✅ **WHAT'S DONE**

1. ✅ **Database schema designed** - Protocol-agnostic authorizations table
2. ✅ **Migration created** - Includes backfill and compatibility view
3. ✅ **Authorization model created** - Full SQLAlchemy model
4. ✅ **Enums defined** - ProtocolType and AuthorizationStatus
5. ✅ **Backward compatibility** - mandate_view and deprecated Mandate model
6. ✅ **Model exports updated** - All new types exported
7. ✅ **Deprecation warnings** - Clear migration path documented

---

## 🎯 **READY FOR NEXT PHASE**

Current branch: `feat/multiprotocol-acp` ✅  
Database layer: ✅ COMPLETE  
Tests passing: ✅ (existing tests unchanged)  

**Next:** Shall I proceed with Phase 2 (Protocol Abstraction Layer)?

This will create the clean protocol interface that makes adding ACP (and future protocols) trivial.

