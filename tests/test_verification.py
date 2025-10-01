"""
Unit tests for verification pipeline.
"""
import pytest
import jwt
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.services.verification_service import VerificationService, VerificationStatus
from app.services.truststore_service import TruststoreService


class TestVerificationService:
    """Test cases for verification service."""
    
    @pytest.fixture
    def verification_service(self):
        """Create verification service instance."""
        return VerificationService()
    
    @pytest.fixture
    def private_key(self):
        """Generate RSA private key for testing."""
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
    
    @pytest.fixture
    def public_key(self, private_key):
        """Extract public key from private key."""
        return private_key.public_key()
    
    @pytest.fixture
    def jwk_key(self, public_key):
        """Convert public key to JWK format."""
        public_numbers = public_key.public_numbers()
        
        # Convert to PEM format first, then to JWK
        pem_public = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # For testing, create a simplified JWK
        return {
            "kty": "RSA",
            "kid": "test-key-1",
            "use": "sig",
            "alg": "RS256",
            "n": "test-n-value",
            "e": "AQAB"
        }
    
    def create_test_jwt(self, payload: dict, private_key, algorithm="RS256", header=None):
        """Create a test JWT token."""
        if header is None:
            header = {
                "typ": "JWT",
                "alg": algorithm,
                "kid": "test-key-1"
            }
        
        return jwt.encode(payload, private_key, algorithm=algorithm, headers=header)
    
    @pytest.mark.asyncio
    async def test_verify_valid_mandate(self, verification_service, private_key, jwk_key):
        """Test verification of a valid mandate."""
        # Create valid payload
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=1)
        
        payload = {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "scope": "payment",
            "amount_limit": "1000"
        }
        
        # Create JWT
        token = self.create_test_jwt(payload, private_key)
        
        # Mock truststore service
        with patch.object(verification_service.truststore, 'get_issuer_keys') as mock_get_keys, \
             patch.object(verification_service.truststore, 'verify_signature') as mock_verify:
            
            mock_get_keys.return_value = {"keys": [jwk_key]}
            mock_verify.return_value = True
            
            # Verify mandate
            result = await verification_service.verify_mandate(token)
            
            assert result.status == VerificationStatus.VALID
            assert result.reason == "All verification checks passed"
            assert result.details["issuer_did"] == "did:example:issuer123"
            assert result.details["subject_did"] == "did:example:subject456"
            assert result.details["scope"] == "payment"
    
    @pytest.mark.asyncio
    async def test_verify_expired_mandate(self, verification_service, private_key, jwk_key):
        """Test verification of an expired mandate."""
        # Create expired payload
        now = datetime.now(timezone.utc)
        exp = now - timedelta(hours=1)  # Expired 1 hour ago
        
        payload = {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int(exp.timestamp()),
            "scope": "payment"
        }
        
        # Create JWT
        token = self.create_test_jwt(payload, private_key)
        
        # Mock truststore service
        with patch.object(verification_service.truststore, 'get_issuer_keys') as mock_get_keys, \
             patch.object(verification_service.truststore, 'verify_signature') as mock_verify:
            
            mock_get_keys.return_value = {"keys": [jwk_key]}
            mock_verify.return_value = True
            
            # Verify mandate
            result = await verification_service.verify_mandate(token)
            
            assert result.status == VerificationStatus.EXPIRED
            assert "expired" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_verify_invalid_signature(self, verification_service, private_key, jwk_key):
        """Test verification with invalid signature."""
        # Create valid payload
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=1)
        
        payload = {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "scope": "payment"
        }
        
        # Create JWT
        token = self.create_test_jwt(payload, private_key)
        
        # Mock truststore service with signature verification failure
        with patch.object(verification_service.truststore, 'get_issuer_keys') as mock_get_keys, \
             patch.object(verification_service.truststore, 'verify_signature') as mock_verify:
            
            mock_get_keys.return_value = {"keys": [jwk_key]}
            mock_verify.return_value = False  # Signature verification fails
            
            # Verify mandate
            result = await verification_service.verify_mandate(token)
            
            assert result.status == VerificationStatus.SIG_INVALID
            assert result.reason == "Invalid signature"
    
    @pytest.mark.asyncio
    async def test_verify_unknown_issuer(self, verification_service, private_key):
        """Test verification with unknown issuer."""
        # Create valid payload
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=1)
        
        payload = {
            "iss": "did:example:unknownissuer",
            "sub": "did:example:subject456",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "scope": "payment"
        }
        
        # Create JWT
        token = self.create_test_jwt(payload, private_key)
        
        # Mock truststore service with unknown issuer
        with patch.object(verification_service.truststore, 'get_issuer_keys') as mock_get_keys:
            mock_get_keys.return_value = None  # Issuer not found
            
            # Verify mandate
            result = await verification_service.verify_mandate(token)
            
            assert result.status == VerificationStatus.ISSUER_UNKNOWN
            assert "not found in truststore" in result.reason
    
    @pytest.mark.asyncio
    async def test_verify_tampered_token(self, verification_service):
        """Test verification of tampered token."""
        # Create a tampered JWT (invalid format)
        tampered_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.tampered.signature"
        
        # Verify mandate
        result = await verification_service.verify_mandate(tampered_token)
        
        assert result.status == VerificationStatus.INVALID_FORMAT
        assert "Invalid JWT structure" in result.reason or "Failed to decode JWT" in result.reason
    
    @pytest.mark.asyncio
    async def test_verify_missing_required_fields(self, verification_service, private_key):
        """Test verification with missing required fields."""
        # Create payload missing required fields but with valid structure
        payload = {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            # Missing: iat, exp
            "scope": "payment"
        }
        
        # Create JWT
        token = self.create_test_jwt(payload, private_key)
        
        # Verify mandate
        result = await verification_service.verify_mandate(token)
        
        # The verification should fail at structure level due to missing required fields
        assert result.status in [VerificationStatus.MISSING_REQUIRED_FIELD, VerificationStatus.INVALID_FORMAT]
        assert "Missing required fields" in result.reason or "Invalid JWT structure" in result.reason
    
    @pytest.mark.asyncio
    async def test_verify_scope_validation(self, verification_service, private_key, jwk_key):
        """Test scope validation."""
        # Create valid payload
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=1)
        
        payload = {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "scope": "payment"
        }
        
        # Create JWT
        token = self.create_test_jwt(payload, private_key)
        
        # Mock truststore service
        with patch.object(verification_service.truststore, 'get_issuer_keys') as mock_get_keys, \
             patch.object(verification_service.truststore, 'verify_signature') as mock_verify:
            
            mock_get_keys.return_value = {"keys": [jwk_key]}
            mock_verify.return_value = True
            
            # Verify mandate with correct scope
            result = await verification_service.verify_mandate(token, expected_scope="payment")
            assert result.status == VerificationStatus.VALID
            
            # Verify mandate with incorrect scope
            result = await verification_service.verify_mandate(token, expected_scope="transfer")
            assert result.status == VerificationStatus.SCOPE_INVALID
            assert "Scope mismatch" in result.reason
    
    @pytest.mark.asyncio
    async def test_verify_scope_missing(self, verification_service, private_key, jwk_key):
        """Test verification when scope is missing but expected."""
        # Create payload without scope
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=1)
        
        payload = {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp())
            # No scope field
        }
        
        # Create JWT
        token = self.create_test_jwt(payload, private_key)
        
        # Mock truststore service
        with patch.object(verification_service.truststore, 'get_issuer_keys') as mock_get_keys, \
             patch.object(verification_service.truststore, 'verify_signature') as mock_verify:
            
            mock_get_keys.return_value = {"keys": [jwk_key]}
            mock_verify.return_value = True
            
            # Verify mandate expecting scope
            result = await verification_service.verify_mandate(token, expected_scope="payment")
            
            assert result.status == VerificationStatus.SCOPE_INVALID
            assert "Missing scope claim" in result.reason


class TestTruststoreService:
    """Test cases for truststore service."""
    
    @pytest.fixture
    def truststore_service(self):
        """Create truststore service instance."""
        return TruststoreService()
    
    def test_should_refresh_new_issuer(self, truststore_service):
        """Test that new issuers should be refreshed."""
        assert truststore_service._should_refresh("did:example:newissuer") is True
    
    def test_should_refresh_expired_cache(self, truststore_service):
        """Test that expired cache should be refreshed."""
        # Add issuer to truststore
        truststore_service._truststore["did:example:issuer123"] = {"keys": []}
        truststore_service._last_refresh["did:example:issuer123"] = datetime.utcnow() - timedelta(hours=2)
        
        assert truststore_service._should_refresh("did:example:issuer123") is True
    
    def test_should_not_refresh_valid_cache(self, truststore_service):
        """Test that valid cache should not be refreshed."""
        # Add issuer to truststore with recent refresh
        truststore_service._truststore["did:example:issuer123"] = {"keys": []}
        truststore_service._last_refresh["did:example:issuer123"] = datetime.utcnow() - timedelta(minutes=30)
        
        assert truststore_service._should_refresh("did:example:issuer123") is False
    
    def test_validate_jwk_set_valid(self, truststore_service):
        """Test validation of valid JWK set."""
        jwk_set = {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "key-1",
                    "use": "sig",
                    "alg": "RS256",
                    "n": "test-n",
                    "e": "AQAB"
                }
            ]
        }
        
        assert truststore_service._validate_jwk_set(jwk_set) is True
    
    def test_validate_jwk_set_invalid_structure(self, truststore_service):
        """Test validation of invalid JWK set structure."""
        # Missing keys field
        jwk_set = {"invalid": "structure"}
        assert truststore_service._validate_jwk_set(jwk_set) is False
        
        # Empty keys array
        jwk_set = {"keys": []}
        assert truststore_service._validate_jwk_set(jwk_set) is False
        
        # Invalid keys type
        jwk_set = {"keys": "not-an-array"}
        assert truststore_service._validate_jwk_set(jwk_set) is False
    
    def test_validate_jwk_valid(self, truststore_service):
        """Test validation of valid JWK."""
        jwk = {
            "kty": "RSA",
            "kid": "key-1",
            "use": "sig",
            "alg": "RS256",
            "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx",
            "e": "AQAB"
        }
        
        assert truststore_service._validate_jwk(jwk) is True
    
    def test_validate_jwk_missing_fields(self, truststore_service):
        """Test validation of JWK with missing fields."""
        jwk = {
            "kty": "RSA",
            "kid": "key-1"
            # Missing use and alg
        }
        
        assert truststore_service._validate_jwk(jwk) is False
    
    def test_validate_jwk_invalid_values(self, truststore_service):
        """Test validation of JWK with invalid values."""
        # Invalid key type
        jwk = {
            "kty": "INVALID",
            "kid": "key-1",
            "use": "sig",
            "alg": "RS256"
        }
        assert truststore_service._validate_jwk(jwk) is False
        
        # Invalid usage
        jwk = {
            "kty": "RSA",
            "kid": "key-1",
            "use": "invalid",
            "alg": "RS256"
        }
        assert truststore_service._validate_jwk(jwk) is False
        
        # Invalid algorithm for key type
        jwk = {
            "kty": "RSA",
            "kid": "key-1",
            "use": "sig",
            "alg": "ES256"  # EC algorithm for RSA key
        }
        assert truststore_service._validate_jwk(jwk) is False


# Sample mandate data for integration tests
SAMPLE_MANDATES = {
    "valid": {
        "payload": {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            "iat": int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "scope": "payment",
            "amount_limit": "1000"
        },
        "expected_status": VerificationStatus.VALID
    },
    "expired": {
        "payload": {
            "iss": "did:example:issuer123",
            "sub": "did:example:subject456",
            "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
            "scope": "payment"
        },
        "expected_status": VerificationStatus.EXPIRED
    },
    "unknown_issuer": {
        "payload": {
            "iss": "did:example:unknownissuer",
            "sub": "did:example:subject456",
            "iat": int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "scope": "payment"
        },
        "expected_status": VerificationStatus.ISSUER_UNKNOWN
    }
}
