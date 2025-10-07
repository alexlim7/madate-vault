# Multi-Protocol Refactoring Plan

Implementation plan for adding ACP support alongside AP2 (JWT-VC) in a protocol-agnostic architecture.

---

## 🎯 Objectives

1. ✅ Make codebase protocol-agnostic
2. ✅ Add ACP (Authorization Credential Protocol) support
3. ✅ Keep existing AP2 (JWT-VC) endpoints working
4. ✅ Maintain backward compatibility
5. ✅ No breaking changes

---

## 📋 Files to Modify

### **1. DATABASE MODELS** (3 files + 1 migration)

#### Modified Files:
```
app/models/mandate.py
  └─ Add: protocol_type field (enum: "AP2", "ACP")
  └─ Add: protocol_version field
  └─ Add: protocol_data field (JSON for protocol-specific data)

app/models/__init__.py
  └─ Export: New protocol enums

alembic/versions/005_add_protocol_support.py  [NEW]
  └─ Migration to add protocol fields
```

#### Changes to `app/models/mandate.py`:
```python
# Add new fields:
protocol_type = Column(Enum("AP2", "ACP"), default="AP2", nullable=False, index=True)
protocol_version = Column(String(10), default="1.0", nullable=False)
protocol_data = Column(JSON, nullable=True)  # Protocol-specific metadata
```

---

### **2. SERVICES** (4 files + 2 new)

#### Modified Files:
```
app/services/verification_service.py
  └─ Refactor: Extract protocol-agnostic interface
  └─ Add: Protocol factory pattern
  └─ Keep: Existing AP2 verification (backward compatible)

app/services/mandate_service.py
  └─ Modify: create_mandate() to accept protocol_type
  └─ Add: Protocol-based verification routing
  └─ Keep: Existing API unchanged (defaults to AP2)

app/services/truststore_service.py
  └─ Extend: Support ACP issuer formats
  └─ Add: Protocol-specific key management
```

#### New Files:
```
app/services/protocols/__init__.py  [NEW]
  └─ Protocol interface definition

app/services/protocols/ap2_protocol.py  [NEW]
  └─ AP2/JWT-VC protocol implementation (refactored from verification_service)

app/services/protocols/acp_protocol.py  [NEW]
  └─ ACP protocol implementation

app/services/protocols/base_protocol.py  [NEW]
  └─ Abstract base class for protocols
```

---

### **3. ROUTERS / ENDPOINTS** (2 files + 1 new)

#### Modified Files:
```
app/api/v1/endpoints/mandates.py
  └─ Add: Optional protocol_type parameter (defaults to "AP2")
  └─ Keep: Existing behavior for backward compatibility
  └─ Add: Protocol validation

app/api/v1/router.py
  └─ Register: New ACP-specific endpoints (if needed)
```

#### New Files:
```
app/api/v1/endpoints/protocols.py  [NEW]
  └─ GET /api/v1/protocols - List supported protocols
  └─ GET /api/v1/protocols/{type}/info - Protocol details
```

---

### **4. SCHEMAS** (2 files)

#### Modified Files:
```
app/schemas/mandate.py
  └─ Add: protocol_type field (optional, defaults to "AP2")
  └─ Add: protocol_version field
  └─ Add: Protocol-specific validation
  └─ Keep: Existing schemas unchanged
```

#### New Files:
```
app/schemas/protocol.py  [NEW]
  └─ Protocol enums
  └─ Protocol info schemas
  └─ ACP-specific schemas
```

---

### **5. UTILITIES** (1 new folder)

#### New Files:
```
app/utils/acp_verification.py  [NEW]
  └─ ACP-specific verification logic

app/utils/protocol_detector.py  [NEW]
  └─ Auto-detect protocol from credential format
```

---

### **6. TESTS** (8 files + 3 new)

#### Modified Files:
```
tests/test_verification.py
  └─ Update: Add protocol parameter tests
  └─ Keep: Existing AP2 tests unchanged

tests/test_mandate_api_additional.py
  └─ Add: Protocol-specific endpoint tests

tests/integration/test_mandate_flow_integration.py
  └─ Add: Multi-protocol integration tests
```

#### New Files:
```
tests/test_acp_verification.py  [NEW]
  └─ ACP-specific verification tests

tests/test_protocol_detection.py  [NEW]
  └─ Protocol auto-detection tests

tests/test_multiprotocol_integration.py  [NEW]
  └─ Test AP2 and ACP side-by-side

tests/integration/test_acp_flow.py  [NEW]
  └─ Complete ACP integration test
```

---

### **7. CONFIGURATION** (1 file)

#### Modified Files:
```
app/core/config.py
  └─ Add: Protocol configuration settings
  └─ Add: Enabled protocols list
```

---

### **8. DOCUMENTATION** (1 new)

#### New Files:
```
docs/guides/MULTI_PROTOCOL_GUIDE.md  [NEW]
  └─ Protocol comparison (AP2 vs ACP)
  └─ Migration guide
  └─ API usage examples
```

---

## 📊 REFACTORING SUMMARY

### Files to Modify:
```
Models:          3 files
Services:        3 files (modified) + 4 files (new)
Routers:         2 files (modified) + 1 file (new)
Schemas:         1 file (modified) + 1 file (new)
Utilities:       2 files (new)
Tests:           3 files (modified) + 4 files (new)
Config:          1 file
Migrations:      1 file (new)
Documentation:   1 file (new)
-------------------------------------------------
TOTAL:           22 files (11 modified, 11 new)
```

---

## 🏗️ ARCHITECTURE DESIGN

### Protocol Abstraction Layer

```
┌─────────────────────────────────────────────────┐
│           Mandate Service (Protocol-Agnostic)    │
└─────────────────┬───────────────────────────────┘
                  │
      ┌───────────┴───────────┐
      │   Protocol Factory     │
      └───────────┬───────────┘
                  │
         ┌────────┴────────┐
         │                 │
    ┌────▼────┐      ┌────▼────┐
    │ AP2     │      │  ACP    │
    │ Protocol│      │ Protocol│
    └────┬────┘      └────┬────┘
         │                │
         ├─ verify()      ├─ verify()
         ├─ parse()       ├─ parse()
         └─ validate()    └─ validate()
```

### Protocol Interface

```python
class BaseProtocol(ABC):
    @abstractmethod
    async def verify(self, credential: str) -> VerificationResult:
        """Verify credential according to protocol."""
        pass
    
    @abstractmethod
    def parse(self, credential: str) -> Dict[str, Any]:
        """Parse credential format."""
        pass
    
    @abstractmethod
    async def validate_issuer(self, issuer: str) -> bool:
        """Validate issuer according to protocol."""
        pass
```

---

## 🔄 MIGRATION STRATEGY

### Backward Compatibility

**Existing AP2 Endpoints (unchanged):**
```
POST /api/v1/mandates
{
  "vc_jwt": "eyJhbGc...",  # Still works!
  "tenant_id": "..."
}
# Automatically detected as AP2
```

**New Multi-Protocol Endpoints:**
```
POST /api/v1/mandates
{
  "credential": "eyJhbGc...",     # Generic field
  "protocol_type": "ACP",          # Explicit protocol
  "tenant_id": "..."
}
```

### Database Migration

```sql
-- Add protocol fields (backward compatible)
ALTER TABLE mandates ADD COLUMN protocol_type VARCHAR(10) DEFAULT 'AP2';
ALTER TABLE mandates ADD COLUMN protocol_version VARCHAR(10) DEFAULT '1.0';
ALTER TABLE mandates ADD COLUMN protocol_data JSON;

-- Update existing records
UPDATE mandates SET protocol_type = 'AP2' WHERE protocol_type IS NULL;
```

---

## 📝 IMPLEMENTATION PHASES

### Phase 1: Abstraction Layer (Foundation)
**Files:**
- `app/services/protocols/base_protocol.py`
- `app/services/protocols/__init__.py`
- `app/schemas/protocol.py`

**Tasks:**
- Define protocol interface
- Create protocol factory
- Add protocol enums

### Phase 2: AP2 Refactoring (No Breaking Changes)
**Files:**
- `app/services/protocols/ap2_protocol.py`
- `app/services/verification_service.py`

**Tasks:**
- Extract AP2 logic to separate protocol class
- Update verification_service to use protocol factory
- Ensure all existing tests still pass

### Phase 3: ACP Implementation
**Files:**
- `app/services/protocols/acp_protocol.py`
- `app/utils/acp_verification.py`
- `tests/test_acp_verification.py`

**Tasks:**
- Implement ACP protocol class
- Add ACP-specific verification
- Write ACP tests

### Phase 4: Database & API Updates
**Files:**
- `app/models/mandate.py`
- `alembic/versions/005_add_protocol_support.py`
- `app/api/v1/endpoints/mandates.py`
- `app/schemas/mandate.py`

**Tasks:**
- Add protocol fields to model
- Create migration
- Update API endpoints
- Update schemas

### Phase 5: Testing & Documentation
**Files:**
- `tests/test_multiprotocol_integration.py`
- `tests/test_protocol_detection.py`
- `docs/guides/MULTI_PROTOCOL_GUIDE.md`

**Tasks:**
- Integration tests
- Protocol detection tests
- Documentation

---

## ✅ SUCCESS CRITERIA

- [ ] All existing AP2 tests pass (624 tests)
- [ ] New ACP tests pass
- [ ] Protocol auto-detection works
- [ ] No breaking API changes
- [ ] Database migration successful
- [ ] Documentation complete
- [ ] Performance maintained (< 500ms per verification)

---

## 🚀 ESTIMATED EFFORT

- Phase 1: 2 hours (abstraction)
- Phase 2: 2 hours (AP2 refactor)
- Phase 3: 3 hours (ACP implementation)
- Phase 4: 2 hours (DB & API)
- Phase 5: 2 hours (testing & docs)

**Total: 11 hours (1-2 days)**

---

## 📋 DETAILED FILE LIST

### MODELS (Modified: 2, New: 0)
1. ✏️ `app/models/mandate.py` - Add protocol fields
2. ✏️ `app/models/__init__.py` - Export protocol enums

### SERVICES (Modified: 3, New: 4)
3. ✏️ `app/services/verification_service.py` - Protocol factory integration
4. ✏️ `app/services/mandate_service.py` - Protocol-aware mandate creation
5. ✏️ `app/services/truststore_service.py` - Multi-protocol issuer management
6. ➕ `app/services/protocols/__init__.py` - Protocol exports
7. ➕ `app/services/protocols/base_protocol.py` - Abstract interface
8. ➕ `app/services/protocols/ap2_protocol.py` - AP2 implementation
9. ➕ `app/services/protocols/acp_protocol.py` - ACP implementation

### ROUTERS (Modified: 2, New: 1)
10. ✏️ `app/api/v1/endpoints/mandates.py` - Protocol parameter support
11. ✏️ `app/api/v1/router.py` - Register protocol endpoints
12. ➕ `app/api/v1/endpoints/protocols.py` - Protocol info endpoints

### SCHEMAS (Modified: 1, New: 1)
13. ✏️ `app/schemas/mandate.py` - Protocol fields in requests
14. ➕ `app/schemas/protocol.py` - Protocol schemas & enums

### UTILITIES (Modified: 0, New: 2)
15. ➕ `app/utils/acp_verification.py` - ACP verification helpers
16. ➕ `app/utils/protocol_detector.py` - Auto-detection logic

### TESTS (Modified: 3, New: 4)
17. ✏️ `tests/test_verification.py` - Add protocol tests
18. ✏️ `tests/test_mandate_api_additional.py` - Protocol endpoint tests
19. ✏️ `tests/integration/test_mandate_flow_integration.py` - Multi-protocol integration
20. ➕ `tests/test_acp_verification.py` - ACP verification tests
21. ➕ `tests/test_protocol_detection.py` - Detection tests
22. ➕ `tests/test_multiprotocol_integration.py` - Side-by-side tests
23. ➕ `tests/integration/test_acp_flow.py` - ACP end-to-end test

### CONFIG (Modified: 1, New: 0)
24. ✏️ `app/core/config.py` - Add protocol settings

### MIGRATIONS (Modified: 0, New: 1)
25. ➕ `alembic/versions/005_add_protocol_support.py` - Protocol fields migration

### DOCUMENTATION (Modified: 0, New: 1)
26. ➕ `docs/guides/MULTI_PROTOCOL_GUIDE.md` - Protocol comparison & migration guide

---

## 🎨 KEY DESIGN DECISIONS

### 1. Protocol Detection Strategy

**Auto-detect by format:**
```python
def detect_protocol(credential: str) -> str:
    # JWT format → AP2
    if credential.count('.') == 2:
        return "AP2"
    
    # JSON-LD format → ACP
    if credential.startswith('{') and '"@context"' in credential:
        return "ACP"
    
    raise ValueError("Unknown protocol")
```

### 2. Backward Compatibility

**Existing API calls work unchanged:**
```python
# OLD (still works)
POST /api/v1/mandates
{
  "vc_jwt": "eyJhbGc...",  # Detected as AP2
  "tenant_id": "..."
}

# NEW (explicit protocol)
POST /api/v1/mandates
{
  "credential": "eyJhbGc...",
  "protocol_type": "AP2",  # or "ACP"
  "tenant_id": "..."
}
```

### 3. Verification Interface

**Protocol-agnostic verification:**
```python
class VerificationService:
    async def verify_mandate(
        self,
        credential: str,
        protocol_type: Optional[str] = None  # Auto-detect if None
    ) -> VerificationResult:
        # Get protocol handler
        protocol = self.protocol_factory.get_protocol(
            protocol_type or self.detect_protocol(credential)
        )
        
        # Verify using protocol-specific logic
        return await protocol.verify(credential)
```

---

## 🔍 AP2 vs ACP COMPARISON

| Aspect | AP2 (JWT-VC) | ACP |
|--------|-------------|-----|
| **Format** | JWT (3-part) | JSON-LD |
| **Signature** | JWS (RS256/ES256) | Linked Data Proofs |
| **Issuer ID** | DID (did:web:...) | DID or URL |
| **Verification** | JWK Set | Verification Method |
| **Standards** | W3C VC Data Model | W3C VC + ACP spec |

### Example Credentials

**AP2 (JWT-VC):**
```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJkaWQ6d2ViOmJhbmsuY29tIi...
```

**ACP (JSON-LD):**
```json
{
  "@context": ["https://www.w3.org/2018/credentials/v1"],
  "type": ["VerifiableCredential", "PaymentMandate"],
  "issuer": "did:web:bank.com",
  "credentialSubject": {...},
  "proof": {
    "type": "Ed25519Signature2020",
    "created": "2025-10-01T12:00:00Z",
    "verificationMethod": "did:web:bank.com#key-1",
    "proofPurpose": "assertionMethod",
    "proofValue": "z..."
  }
}
```

---

## 🧪 TESTING STRATEGY

### Test Coverage

```
Existing AP2 Tests:  624 (all must pass)
New ACP Tests:       ~50
Protocol Tests:      ~20
Integration:         ~10
-----------------------------------------
Total:               ~704 tests
```

### Test Categories

1. **AP2 Regression Tests** - Ensure nothing breaks
2. **ACP Unit Tests** - New protocol verification
3. **Protocol Detection Tests** - Auto-detection
4. **Multi-Protocol Integration** - Both protocols working together
5. **Performance Tests** - Verify no slowdown

---

## ⚠️ BREAKING CHANGE PREVENTION

### What We WON'T Break

✅ Existing `vc_jwt` field in API requests  
✅ Current AP2 verification logic  
✅ Database schema (additive only)  
✅ Existing test suite  
✅ SDK compatibility  

### Migration Path

```
Version 1.0 (Current): AP2 only
Version 1.1 (This refactor): AP2 + ACP (dual support)
Version 2.0 (Future): Fully protocol-agnostic
```

---

## 📅 IMPLEMENTATION ORDER

**Recommended sequence:**

1. ✅ Create protocol abstraction (`base_protocol.py`)
2. ✅ Refactor AP2 to use abstraction (`ap2_protocol.py`)
3. ✅ Run tests - confirm no regression
4. ✅ Implement ACP protocol (`acp_protocol.py`)
5. ✅ Add database migration (`005_add_protocol_support.py`)
6. ✅ Update models (`mandate.py`)
7. ✅ Update services (`verification_service.py`, `mandate_service.py`)
8. ✅ Update API endpoints (`mandates.py`)
9. ✅ Add protocol detection (`protocol_detector.py`)
10. ✅ Write ACP tests
11. ✅ Write integration tests
12. ✅ Update documentation
13. ✅ Final testing & verification

---

**Ready to start implementation!** 🚀

Let me know when you want to begin, and I'll start with Phase 1 (Protocol Abstraction Layer).


