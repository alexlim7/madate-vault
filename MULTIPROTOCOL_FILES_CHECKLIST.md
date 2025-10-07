# Multi-Protocol Refactor - Complete File Checklist

All files that will be created or modified for ACP + AP2 support.

---

## ✅ **COMPLETED** (2 files)

### Migrations
- [x] `alembic/versions/005_add_authorizations_table.py` ✅ CREATED

### Models
- [x] `app/models/authorization.py` ✅ CREATED
- [x] `app/models/__init__.py` ✅ UPDATED

---

## 📋 **TO BE MODIFIED** (10 files)

### Models (1 file)
```
[ ] app/models/mandate.py
    └─ Add deprecation warnings in docstring
    └─ Add migration helper methods
    └─ Keep all existing functionality
```

### Services (3 files)
```
[ ] app/services/verification_service.py
    └─ Add protocol factory
    └─ Support protocol parameter
    └─ Route to AP2 or ACP verifier
    └─ Maintain backward compatibility

[ ] app/services/mandate_service.py
    └─ Update to use Authorization model
    └─ Support both Mandate (deprecated) and Authorization
    └─ Add protocol parameter to create_mandate()
    └─ Keep existing method signatures

[ ] app/services/truststore_service.py
    └─ Add ACP issuer support
    └─ Support multiple key formats
    └─ Protocol-specific key resolution
```

### Routers (2 files)
```
[ ] app/api/v1/endpoints/mandates.py
    └─ Add optional protocol_type parameter
    └─ Support both old (vc_jwt) and new (credential) fields
    └─ Return protocol info in responses
    └─ Maintain all existing endpoints

[ ] app/api/v1/router.py
    └─ Register new protocol endpoints
```

### Schemas (1 file)
```
[ ] app/schemas/mandate.py
    └─ Add protocol_type field (optional, default="AP2")
    └─ Add credential field (generic)
    └─ Keep vc_jwt field for backward compatibility
    └─ Add protocol-specific validation
```

### Config (1 file)
```
[ ] app/core/config.py
    └─ Add ENABLED_PROTOCOLS setting
    └─ Add ACP configuration options
```

### Tests (2 files)
```
[ ] tests/test_verification.py
    └─ Add protocol parameter tests
    └─ Ensure existing tests still pass

[ ] tests/integration/test_mandate_flow_integration.py
    └─ Add multi-protocol test scenarios
```

---

## ➕ **TO BE CREATED** (14 files)

### Protocol Implementation (4 files)
```
[ ] app/services/protocols/__init__.py
    └─ Protocol factory
    └─ Protocol registry
    └─ Export protocol classes

[ ] app/services/protocols/base_protocol.py
    └─ Abstract base class
    └─ Common interface: verify(), parse(), validate()
    └─ Protocol metadata

[ ] app/services/protocols/ap2_protocol.py
    └─ AP2/JWT-VC implementation
    └─ Refactored from existing verification_service
    └─ JWK-based signature verification

[ ] app/services/protocols/acp_protocol.py
    └─ ACP implementation
    └─ JSON-LD credential verification
    └─ Linked Data Proof verification
```

### Utilities (2 files)
```
[ ] app/utils/acp_verification.py
    └─ ACP-specific verification helpers
    └─ Linked Data Proof validation
    └─ JSON-LD processing

[ ] app/utils/protocol_detector.py
    └─ Auto-detect protocol from credential format
    └─ Smart detection: JWT → AP2, JSON-LD → ACP
```

### Schemas (1 file)
```
[ ] app/schemas/protocol.py
    └─ ProtocolType enum
    └─ ProtocolInfo schema
    └─ ACP-specific request/response schemas
```

### Routers (1 file)
```
[ ] app/api/v1/endpoints/protocols.py
    └─ GET /api/v1/protocols - List supported protocols
    └─ GET /api/v1/protocols/{type}/info - Protocol details
    └─ GET /api/v1/protocols/{type}/schema - Protocol JSON schema
```

### Tests - ACP (4 files)
```
[ ] tests/test_acp_verification.py
    └─ ACP credential parsing tests
    └─ ACP signature verification tests
    └─ ACP validation tests

[ ] tests/test_protocol_detection.py
    └─ Test auto-detection logic
    └─ Test edge cases
    └─ Test invalid formats

[ ] tests/test_multiprotocol_integration.py
    └─ Test AP2 and ACP side-by-side
    └─ Test protocol isolation
    └─ Test database queries across protocols

[ ] tests/integration/test_acp_flow.py
    └─ Complete ACP flow
    └─ ACP mandate creation
    └─ ACP verification
    └─ ACP webhook delivery
```

### Documentation (2 files)
```
[ ] docs/guides/MULTI_PROTOCOL_GUIDE.md
    └─ Protocol comparison
    └─ When to use AP2 vs ACP
    └─ Migration guide
    └─ API examples for both protocols

[ ] docs/guides/ACP_INTEGRATION_GUIDE.md
    └─ ACP-specific integration guide
    └─ ACP credential format
    └─ ACP issuer setup
    └─ Code examples
```

---

## 📊 **FILE SUMMARY**

```
COMPLETED:          2 files ✅
TO MODIFY:         10 files
TO CREATE:         14 files
────────────────────────────
TOTAL FILES:       26 files

Database Tables:    1 new (authorizations)
Database Views:     1 new (mandate_view)
Migrations:         1 new
Protocol Handlers:  2 (AP2 + ACP)
Test Files:         4 new ACP tests
Documentation:      2 new guides
```

---

## 🎯 **IMPLEMENTATION CHECKLIST**

### Phase 1: Protocol Abstraction ✅ (In Progress)
- [x] Create authorizations table migration
- [x] Create Authorization model
- [x] Update models/__init__.py
- [ ] Create protocol base classes
- [ ] Create protocol factory

### Phase 2: AP2 Refactoring
- [ ] Extract AP2 logic to ap2_protocol.py
- [ ] Update verification_service.py
- [ ] Run existing tests (should all pass)

### Phase 3: ACP Implementation  
- [ ] Implement acp_protocol.py
- [ ] Create ACP verification utilities
- [ ] Write ACP tests

### Phase 4: API Integration
- [ ] Update mandate_service.py
- [ ] Update mandates.py endpoint
- [ ] Update schemas
- [ ] Add protocol endpoints

### Phase 5: Testing
- [ ] Run all existing tests (624 should pass)
- [ ] Run new ACP tests
- [ ] Integration tests
- [ ] Performance tests

### Phase 6: Documentation
- [ ] Multi-protocol guide
- [ ] ACP integration guide
- [ ] Update README
- [ ] API documentation

---

## ⚠️ **CRITICAL SUCCESS FACTORS**

1. **Zero Breaking Changes**
   - All existing AP2 endpoints work unchanged
   - vc_jwt field still accepted
   - Legacy mandate queries work via view

2. **Performance**
   - No slowdown in AP2 verification
   - ACP verification < 500ms
   - Database queries optimized

3. **Testing**
   - All 624 existing tests pass
   - 50+ new ACP tests
   - Integration tests cover both protocols

4. **Documentation**
   - Clear migration guide
   - Protocol comparison
   - Code examples for both

---

## 🚀 **READY TO IMPLEMENT**

Current branch: `feat/multiprotocol-acp` ✅

**Next step:** Shall I proceed with Phase 1 (Protocol Abstraction)?

I'll create the base protocol classes and factory pattern while ensuring zero impact on existing functionality.

**Ready to proceed?** 🚀


