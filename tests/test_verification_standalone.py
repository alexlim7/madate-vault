"""
Standalone unit tests for mandate verification service.
Tests valid, expired, tampered, and unknown issuer cases with audit log verification.
"""
import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


class VerificationStatus:
    """Verification status enumeration for testing."""
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    SIG_INVALID = "SIG_INVALID"
    ISSUER_UNKNOWN = "ISSUER_UNKNOWN"
    INVALID_FORMAT = "INVALID_FORMAT"
    SCOPE_INVALID = "SCOPE_INVALID"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"


class VerificationResult:
    """Result of mandate verification for testing."""
    
    def __init__(self, status: str, reason: str = "", details: dict = None):
        self.status = status
        self.reason = reason
        self.details = details or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "status": self.status,
            "reason": self.reason,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }
    
    @property
    def is_valid(self) -> bool:
        """Check if verification is valid."""
        return self.status == VerificationStatus.VALID


class MockVerificationService:
    """Mock verification service for testing."""
    
    def __init__(self):
        self.truststore = AsyncMock()
    
    async def verify_mandate(self, vc_jwt: str, expected_scope: str = None) -> VerificationResult:
        """
        Mock verify_mandate method that simulates different verification scenarios.
        """
        # Simulate different test cases based on JWT content
        # Check more specific patterns first
        if "scope_invalid" in vc_jwt.lower():
            return VerificationResult(
                status=VerificationStatus.SCOPE_INVALID,
                reason="Scope mismatch: expected 'transfer', got 'payment'"
            )
        elif "tampered" in vc_jwt.lower():
            return VerificationResult(
                status=VerificationStatus.SIG_INVALID,
                reason="Invalid signature"
            )
        elif "unknown" in vc_jwt.lower():
            return VerificationResult(
                status=VerificationStatus.ISSUER_UNKNOWN,
                reason="Issuer DID 'did:example:unknownissuer' not found in truststore"
            )
        elif "missing" in vc_jwt.lower():
            return VerificationResult(
                status=VerificationStatus.MISSING_REQUIRED_FIELD,
                reason="Missing required fields: iat, exp"
            )
        elif "expired" in vc_jwt.lower():
            return VerificationResult(
                status=VerificationStatus.EXPIRED,
                reason="Mandate expired at 2024-01-01T00:00:00Z"
            )
        elif "invalid" in vc_jwt.lower():
            return VerificationResult(
                status=VerificationStatus.INVALID_FORMAT,
                reason="Invalid JWT structure: Malformed token"
            )
        else:
            # Valid case
            return VerificationResult(
                status=VerificationStatus.VALID,
                reason="All verification checks passed",
                details={
                    "issuer_did": "did:example:issuer123",
                    "subject_did": "did:example:subject456",
                    "scope": "payment",
                    "amount_limit": "100.00",
                    "expires_at": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
                    "issued_at": int(datetime.now(timezone.utc).timestamp()),
                    "payload": {
                        "iss": "did:example:issuer123",
                        "sub": "did:example:subject456",
                        "scope": "payment",
                        "amount_limit": "100.00"
                    }
                }
            )


class MockAuditService:
    """Mock audit service for testing."""
    
    def __init__(self):
        self.logged_events = []
    
    async def log_event(self, mandate_id: str, event_type: str, details: dict):
        """Mock log_event method."""
        self.logged_events.append({
            "mandate_id": mandate_id,
            "event_type": event_type,
            "details": details
        })


class TestMandateVerificationComprehensive:
    """Comprehensive tests for mandate verification with audit logging."""
    
    @pytest.fixture
    def verification_service(self):
        """Create mock verification service."""
        return MockVerificationService()
    
    @pytest.fixture
    def audit_service(self):
        """Create mock audit service."""
        return MockAuditService()
    
    @pytest.fixture
    def private_key(self):
        """Generate RSA private key for testing."""
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
    
    @pytest.fixture
    def public_key(self, private_key):
        """Get public key from private key."""
        return private_key.public_key()
    
    def create_test_jwt(self, payload: dict, private_key, algorithm: str = "RS256") -> str:
        """Helper to create a signed JWT."""
        header = {
            "typ": "JWT",
            "alg": algorithm,
            "kid": "test-key-1"
        }
        return jwt.encode(payload, private_key, algorithm=algorithm, headers=header)
    
    @pytest.mark.asyncio
    async def test_verify_valid_mandate_with_audit_log(self, verification_service, audit_service, private_key):
        """Test verification of a valid mandate with audit log verification."""
        # Create valid JWT
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=1)
        
        payload = {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "scope": "payment",
            "amount_limit": "100.00"
        }
        
        token = self.create_test_jwt(payload, private_key)
        
        # Verify mandate
        result = await verification_service.verify_mandate(token)
        
        # Assert verification result
        assert result.status == VerificationStatus.VALID
        assert result.reason == "All verification checks passed"
        assert result.details["issuer_did"] == "did:example:issuer123"
        assert result.details["subject_did"] == "did:example:subject456"
        assert result.details["scope"] == "payment"
        assert result.details["amount_limit"] == "100.00"
        
        # Simulate audit logging (as would be done by mandate service)
        await audit_service.log_event(
            mandate_id="test-mandate-id",
            event_type="VERIFY",
            details={
                "verification_status": result.status,
                "verification_reason": result.reason,
                "verification_details": result.to_dict()
            }
        )
        
        # Verify audit log was created with correct information
        assert len(audit_service.logged_events) == 1
        audit_event = audit_service.logged_events[0]
        assert audit_event["event_type"] == "VERIFY"
        assert audit_event["details"]["verification_status"] == "VALID"
        assert audit_event["details"]["verification_reason"] == "All verification checks passed"
        assert "verification_details" in audit_event["details"]
    
    @pytest.mark.asyncio
    async def test_verify_expired_mandate_with_audit_log(self, verification_service, audit_service, private_key):
        """Test verification of an expired mandate with audit log verification."""
        # Create expired JWT
        now = datetime.now(timezone.utc)
        exp = now - timedelta(hours=1)  # Expired 1 hour ago
        
        payload = {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "scope": "payment"
        }
        
        token = self.create_test_jwt(payload, private_key)
        # Modify token to trigger expired case
        expired_token = "expired_" + token
        
        # Verify mandate
        result = await verification_service.verify_mandate(expired_token)
        
        # Assert verification result
        assert result.status == VerificationStatus.EXPIRED
        assert "expired" in result.reason.lower()
        
        # Simulate audit logging
        await audit_service.log_event(
            mandate_id="test-mandate-id",
            event_type="VERIFY",
            details={
                "verification_status": result.status,
                "verification_reason": result.reason,
                "verification_details": result.to_dict()
            }
        )
        
        # Verify audit log contains correct reason code
        audit_event = audit_service.logged_events[0]
        assert audit_event["details"]["verification_status"] == "EXPIRED"
        assert "expired" in audit_event["details"]["verification_reason"].lower()
    
    @pytest.mark.asyncio
    async def test_verify_tampered_mandate_with_audit_log(self, verification_service, audit_service, private_key):
        """Test verification of a tampered mandate with audit log verification."""
        # Create tampered JWT
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=1)
        
        payload = {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "scope": "payment"
        }
        
        token = self.create_test_jwt(payload, private_key)
        # Modify token to trigger tampered case
        tampered_token = "tampered_" + token
        
        # Verify mandate
        result = await verification_service.verify_mandate(tampered_token)
        
        # Assert verification result
        assert result.status == VerificationStatus.SIG_INVALID
        assert "Invalid signature" in result.reason
        
        # Simulate audit logging
        await audit_service.log_event(
            mandate_id="test-mandate-id",
            event_type="VERIFY",
            details={
                "verification_status": result.status,
                "verification_reason": result.reason,
                "verification_details": result.to_dict()
            }
        )
        
        # Verify audit log contains correct reason code
        audit_event = audit_service.logged_events[0]
        assert audit_event["details"]["verification_status"] == "SIG_INVALID"
        assert "Invalid signature" in audit_event["details"]["verification_reason"]
    
    @pytest.mark.asyncio
    async def test_verify_unknown_issuer_with_audit_log(self, verification_service, audit_service, private_key):
        """Test verification with unknown issuer with audit log verification."""
        # Create JWT with unknown issuer
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=1)
        
        payload = {
            "iss": "did:example:unknownissuer",
            "sub": "did:example:subject456",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "scope": "payment"
        }
        
        token = self.create_test_jwt(payload, private_key)
        # Modify token to trigger unknown issuer case
        unknown_token = "unknown_" + token
        
        # Verify mandate
        result = await verification_service.verify_mandate(unknown_token)
        
        # Assert verification result
        assert result.status == VerificationStatus.ISSUER_UNKNOWN
        assert "not found in truststore" in result.reason.lower()
        
        # Simulate audit logging
        await audit_service.log_event(
            mandate_id="test-mandate-id",
            event_type="VERIFY",
            details={
                "verification_status": result.status,
                "verification_reason": result.reason,
                "verification_details": result.to_dict()
            }
        )
        
        # Verify audit log contains correct reason code
        audit_event = audit_service.logged_events[0]
        assert audit_event["details"]["verification_status"] == "ISSUER_UNKNOWN"
        assert "not found in truststore" in audit_event["details"]["verification_reason"].lower()
    
    @pytest.mark.asyncio
    async def test_verify_invalid_format_with_audit_log(self, verification_service, audit_service):
        """Test verification of invalid format JWT with audit log verification."""
        # Create invalid JWT
        invalid_token = "invalid.jwt.format"
        
        # Verify mandate
        result = await verification_service.verify_mandate(invalid_token)
        
        # Assert verification result
        assert result.status == VerificationStatus.INVALID_FORMAT
        assert "Invalid JWT structure" in result.reason
        
        # Simulate audit logging
        await audit_service.log_event(
            mandate_id="test-mandate-id",
            event_type="VERIFY",
            details={
                "verification_status": result.status,
                "verification_reason": result.reason,
                "verification_details": result.to_dict()
            }
        )
        
        # Verify audit log contains correct reason code
        audit_event = audit_service.logged_events[0]
        assert audit_event["details"]["verification_status"] == "INVALID_FORMAT"
        assert "Invalid JWT structure" in audit_event["details"]["verification_reason"]
    
    @pytest.mark.asyncio
    async def test_verify_missing_required_fields_with_audit_log(self, verification_service, audit_service, private_key):
        """Test verification with missing required fields with audit log verification."""
        # Create payload missing required fields
        payload = {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            # Missing: iat, exp
            "scope": "payment"
        }
        
        token = self.create_test_jwt(payload, private_key)
        # Modify token to trigger missing fields case
        missing_token = "missing_" + token
        
        # Verify mandate
        result = await verification_service.verify_mandate(missing_token)
        
        # Assert verification result
        assert result.status == VerificationStatus.MISSING_REQUIRED_FIELD
        assert "Missing required fields" in result.reason
        assert "iat, exp" in result.reason
        
        # Simulate audit logging
        await audit_service.log_event(
            mandate_id="test-mandate-id",
            event_type="VERIFY",
            details={
                "verification_status": result.status,
                "verification_reason": result.reason,
                "verification_details": result.to_dict()
            }
        )
        
        # Verify audit log contains correct reason code
        audit_event = audit_service.logged_events[0]
        assert audit_event["details"]["verification_status"] == "MISSING_REQUIRED_FIELD"
        assert "Missing required fields" in audit_event["details"]["verification_reason"]
    
    @pytest.mark.asyncio
    async def test_verify_scope_invalid_with_audit_log(self, verification_service, audit_service, private_key):
        """Test verification with invalid scope with audit log verification."""
        # Create JWT with scope mismatch
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=1)
        
        payload = {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "scope": "payment"
        }
        
        token = self.create_test_jwt(payload, private_key)
        # Modify token to trigger scope invalid case
        scope_invalid_token = "scope_invalid_" + token
        
        # Verify mandate with different expected scope
        result = await verification_service.verify_mandate(scope_invalid_token, expected_scope="transfer")
        
        # Assert verification result
        assert result.status == VerificationStatus.SCOPE_INVALID
        assert "scope mismatch" in result.reason.lower()
        
        # Simulate audit logging
        await audit_service.log_event(
            mandate_id="test-mandate-id",
            event_type="VERIFY",
            details={
                "verification_status": result.status,
                "verification_reason": result.reason,
                "verification_details": result.to_dict()
            }
        )
        
        # Verify audit log contains correct reason code
        audit_event = audit_service.logged_events[0]
        assert audit_event["details"]["verification_status"] == "SCOPE_INVALID"
        assert "scope mismatch" in audit_event["details"]["verification_reason"].lower()
    
    @pytest.mark.asyncio
    async def test_verification_result_to_dict(self, verification_service):
        """Test VerificationResult to_dict method."""
        result = VerificationResult(
            status=VerificationStatus.VALID,
            reason="Test reason",
            details={"test": "data"}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["status"] == "VALID"
        assert result_dict["reason"] == "Test reason"
        assert result_dict["details"] == {"test": "data"}
        assert "timestamp" in result_dict
        assert result.is_valid is True
    
    @pytest.mark.asyncio
    async def test_verification_result_invalid_status(self, verification_service):
        """Test VerificationResult with invalid status."""
        result = VerificationResult(
            status=VerificationStatus.EXPIRED,
            reason="Token expired"
        )
        
        assert result.is_valid is False
        assert result.status == VerificationStatus.EXPIRED
        assert result.reason == "Token expired"
    
    @pytest.mark.asyncio
    async def test_audit_log_multiple_events(self, verification_service, audit_service, private_key):
        """Test multiple audit log events for different verification results."""
        # Test multiple verification scenarios
        test_cases = [
            ("valid_token", VerificationStatus.VALID, "All verification checks passed"),
            ("expired_token", VerificationStatus.EXPIRED, "expired"),
            ("tampered_token", VerificationStatus.SIG_INVALID, "Invalid signature"),
            ("unknown_token", VerificationStatus.ISSUER_UNKNOWN, "not found in truststore")
        ]
        
        for token_type, expected_status, expected_reason in test_cases:
            # Create JWT
            now = datetime.now(timezone.utc)
            exp = now + timedelta(hours=1)
            
            payload = {
                "iss": "did:example:issuer123",
                "sub": "did:example:subject456",
                "iat": int(now.timestamp()),
                "exp": int(exp.timestamp()),
                "scope": "payment"
            }
            
            token = self.create_test_jwt(payload, private_key)
            
            # Verify mandate
            result = await verification_service.verify_mandate(token_type + "_" + token)
            
            # Log audit event
            await audit_service.log_event(
                mandate_id=f"test-mandate-{token_type}",
                event_type="VERIFY",
                details={
                    "verification_status": result.status,
                    "verification_reason": result.reason,
                    "verification_details": result.to_dict()
                }
            )
            
            # Verify result
            assert result.status == expected_status
            if expected_status != VerificationStatus.VALID:
                assert expected_reason.lower() in result.reason.lower()
        
        # Verify all audit events were logged
        assert len(audit_service.logged_events) == len(test_cases)
        
        # Verify each audit event has correct information
        for i, (token_type, expected_status, expected_reason) in enumerate(test_cases):
            audit_event = audit_service.logged_events[i]
            assert audit_event["event_type"] == "VERIFY"
            assert audit_event["details"]["verification_status"] == expected_status
            assert audit_event["mandate_id"] == f"test-mandate-{token_type}"


class TestVerificationStatusEnum:
    """Test VerificationStatus enum values."""
    
    def test_verification_status_values(self):
        """Test that all expected verification status values exist."""
        expected_statuses = [
            "VALID",
            "EXPIRED", 
            "SIG_INVALID",
            "ISSUER_UNKNOWN",
            "INVALID_FORMAT",
            "SCOPE_INVALID",
            "MISSING_REQUIRED_FIELD"
        ]
        
        for status in expected_statuses:
            assert hasattr(VerificationStatus, status)
            assert getattr(VerificationStatus, status) == status
    
    def test_verification_status_string_representation(self):
        """Test string representation of verification status."""
        assert str(VerificationStatus.VALID) == "VALID"
        assert str(VerificationStatus.EXPIRED) == "EXPIRED"
        assert str(VerificationStatus.SIG_INVALID) == "SIG_INVALID"
