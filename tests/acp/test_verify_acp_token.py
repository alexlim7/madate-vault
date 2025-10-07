"""
Unit tests for ACP token verification.

Tests the ACP protocol verification logic including:
- Active token validation
- Expiration checking
- Amount validation
- Constraint matching
- Error handling
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from app.protocols.acp.schemas import ACPDelegatedToken
from app.protocols.acp.verify import verify_acp_token, verify_acp_credential
from app.services.types import VerificationStatus


class TestACPTokenVerification:
    """Test suite for ACP token verification."""
    
    def test_verify_active_token(self):
        """Test verification of a valid, active ACP token."""
        # Create valid token
        token = ACPDelegatedToken(
            token_id="acp-token-123",
            psp_id="psp-bank-456",
            merchant_id="merchant-acme-789",
            max_amount=Decimal("5000.00"),
            currency="USD",
            expires_at=datetime.utcnow() + timedelta(days=30),
            constraints={"category": "retail"}
        )
        
        # Verify
        result = verify_acp_token(token)
        
        # Assertions
        assert result.status == VerificationStatus.VALID
        assert result.reason == "ACP token verification successful"
        assert result.issuer == "psp-bank-456"
        assert result.subject == "merchant-acme-789"
        assert result.amount_limit == 5000.00
        assert result.currency == "USD"
        assert result.expires_at is not None
        assert result.is_valid is True
        assert result.details['token_id'] == "acp-token-123"
        assert result.details['protocol'] == "ACP"
    
    def test_verify_expired_token(self):
        """Test verification of an expired ACP token."""
        # Use model_construct to bypass Pydantic validation for testing
        expired_time = datetime.utcnow() - timedelta(days=1)
        
        token = ACPDelegatedToken.model_construct(
            token_id="acp-expired-123",
            psp_id="psp-456",
            merchant_id="merchant-789",
            max_amount=Decimal("1000.00"),
            currency="EUR",
            expires_at=expired_time,  # Expired
            constraints={}
        )
        
        # Verify
        result = verify_acp_token(token)
        
        # Assertions
        assert result.status == VerificationStatus.EXPIRED
        assert "expired" in result.reason.lower()
        assert result.is_valid is False
        assert result.expires_at == expired_time
    
    def test_verify_token_with_zero_amount(self):
        """Test that Pydantic validation rejects token with zero max_amount."""
        # Pydantic validation should prevent creation of zero-amount token
        with pytest.raises(Exception):  # Pydantic ValidationError
            token = ACPDelegatedToken(
                token_id="acp-zero-123",
                psp_id="psp-456",
                merchant_id="merchant-789",
                max_amount=Decimal("0.00"),  # Invalid: must be >= 0.01
                currency="USD",
                expires_at=datetime.utcnow() + timedelta(days=30),
                constraints={}
            )
    
    def test_verify_token_with_very_small_amount_accepted(self):
        """Test that verification accepts minimal valid amount (0.01)."""
        # Create token with minimal valid amount (bypasses zero check)
        token = ACPDelegatedToken(
            token_id="acp-small-123",
            psp_id="psp-456",
            merchant_id="merchant-789",
            max_amount=Decimal("0.01"),  # Minimum valid amount
            currency="USD",
            expires_at=datetime.utcnow() + timedelta(days=30),
            constraints={}
        )
        
        # Verify - should be valid
        result = verify_acp_token(token)
        
        assert result.status == VerificationStatus.VALID
        assert result.is_valid is True
        assert result.amount_limit == 0.01
    
    def test_verify_token_with_negative_amount(self):
        """Test verification rejects token with negative max_amount."""
        # Note: Pydantic validation should catch this, but if it somehow gets through...
        # We can't actually create a token with negative amount due to Pydantic validation
        # So this test verifies the Pydantic validation works
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            token = ACPDelegatedToken(
                token_id="acp-neg-123",
                psp_id="psp-456",
                merchant_id="merchant-789",
                max_amount=Decimal("-100.00"),
                currency="USD",
                expires_at=datetime.utcnow() + timedelta(days=30),
                constraints={}
            )
    
    def test_verify_token_with_matching_constraints(self):
        """Test verification succeeds when constraint.merchant matches merchant_id."""
        # Create token with matching merchant constraint
        token = ACPDelegatedToken(
            token_id="acp-match-123",
            psp_id="psp-456",
            merchant_id="merchant-acme",
            max_amount=Decimal("2500.00"),
            currency="USD",
            expires_at=datetime.utcnow() + timedelta(days=30),
            constraints={
                "merchant": "merchant-acme",  # Matches merchant_id
                "category": "electronics"
            }
        )
        
        # Verify
        result = verify_acp_token(token)
        
        # Assertions
        assert result.status == VerificationStatus.VALID
        assert result.is_valid is True
        assert result.subject == "merchant-acme"
    
    def test_verify_token_with_mismatched_constraints(self):
        """Test verification fails when constraint.merchant doesn't match merchant_id."""
        # Create token with mismatched merchant constraint
        token = ACPDelegatedToken(
            token_id="acp-mismatch-123",
            psp_id="psp-456",
            merchant_id="merchant-acme",
            max_amount=Decimal("1500.00"),
            currency="GBP",
            expires_at=datetime.utcnow() + timedelta(days=30),
            constraints={
                "merchant": "merchant-different",  # Does NOT match merchant_id
                "category": "food"
            }
        )
        
        # Verify
        result = verify_acp_token(token)
        
        # Assertions
        assert result.status == VerificationStatus.SCOPE_INVALID
        assert "mismatch" in result.reason.lower()
        assert "merchant-acme" in result.reason
        assert "merchant-different" in result.reason
        assert result.is_valid is False
        assert result.details.get('error_code') == 'MERCHANT_MISMATCH'
        assert result.details.get('expected_merchant') == "merchant-acme"
        assert result.details.get('constraint_merchant') == "merchant-different"
    
    def test_verify_token_without_merchant_constraint(self):
        """Test verification succeeds when no merchant constraint is present."""
        # Create token without merchant constraint
        token = ACPDelegatedToken(
            token_id="acp-no-constraint-123",
            psp_id="psp-456",
            merchant_id="merchant-xyz",
            max_amount=Decimal("3000.00"),
            currency="JPY",
            expires_at=datetime.utcnow() + timedelta(days=30),
            constraints={
                "category": "services",
                "item": "subscription"
            }
        )
        
        # Verify
        result = verify_acp_token(token)
        
        # Assertions
        assert result.status == VerificationStatus.VALID
        assert result.is_valid is True
    
    def test_verify_token_with_empty_constraints(self):
        """Test verification succeeds with no constraints."""
        # Create token with empty constraints
        token = ACPDelegatedToken(
            token_id="acp-empty-123",
            psp_id="psp-456",
            merchant_id="merchant-test",
            max_amount=Decimal("10000.00"),
            currency="CAD",
            expires_at=datetime.utcnow() + timedelta(days=30),
            constraints={}
        )
        
        # Verify
        result = verify_acp_token(token)
        
        # Assertions
        assert result.status == VerificationStatus.VALID
        assert result.is_valid is True
    
    def test_verify_token_result_contains_all_fields(self):
        """Test that verification result contains all expected fields."""
        # Create valid token
        token = ACPDelegatedToken(
            token_id="acp-full-123",
            psp_id="psp-789",
            merchant_id="merchant-test",
            max_amount=Decimal("7500.50"),
            currency="CHF",
            expires_at=datetime.utcnow() + timedelta(days=60),
            constraints={"location": "switzerland"}
        )
        
        # Verify
        result = verify_acp_token(token)
        
        # Assertions - Check all fields are populated
        assert result.status is not None
        assert result.reason is not None
        assert result.expires_at is not None
        assert result.amount_limit == 7500.50
        assert result.currency == "CHF"
        assert result.issuer == "psp-789"
        assert result.subject == "merchant-test"
        assert result.scope == {'constraints': {"location": "switzerland"}}
        assert isinstance(result.details, dict)
        assert result.details['token_id'] == "acp-full-123"
        assert result.details['protocol'] == "ACP"


class TestACPCredentialVerification:
    """Test suite for verify_acp_credential (from dict)."""
    
    def test_verify_valid_credential_dict(self):
        """Test verification from valid credential dictionary."""
        credential = {
            'token_id': 'acp-dict-123',
            'psp_id': 'psp-456',
            'merchant_id': 'merchant-789',
            'max_amount': '5000.00',
            'currency': 'USD',
            'expires_at': (datetime.utcnow() + timedelta(days=30)).isoformat(),
            'constraints': {'category': 'retail'}
        }
        
        result = verify_acp_credential(credential)
        
        assert result.status == VerificationStatus.VALID
        assert result.is_valid is True
    
    def test_verify_invalid_credential_format(self):
        """Test verification handles invalid credential format."""
        # Missing required field
        credential = {
            'token_id': 'acp-invalid',
            'psp_id': 'psp-456',
            # missing merchant_id
            'max_amount': '1000.00',
            'currency': 'USD'
        }
        
        result = verify_acp_credential(credential)
        
        assert result.status == VerificationStatus.INVALID_FORMAT
        assert "invalid" in result.reason.lower()
        assert result.is_valid is False
    
    def test_verify_credential_with_invalid_currency(self):
        """Test verification handles invalid currency code."""
        credential = {
            'token_id': 'acp-bad-curr',
            'psp_id': 'psp-456',
            'merchant_id': 'merchant-789',
            'max_amount': '1000.00',
            'currency': 'INVALID',  # Invalid currency code
            'expires_at': (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        result = verify_acp_credential(credential)
        
        assert result.status == VerificationStatus.INVALID_FORMAT
        assert result.is_valid is False


class TestACPEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_verify_token_expiring_soon(self):
        """Test token expiring in 1 second (should still be valid)."""
        # Token expires in 1 second
        token = ACPDelegatedToken(
            token_id="acp-soon-123",
            psp_id="psp-456",
            merchant_id="merchant-789",
            max_amount=Decimal("100.00"),
            currency="USD",
            expires_at=datetime.utcnow() + timedelta(seconds=1),
            constraints={}
        )
        
        result = verify_acp_token(token)
        
        # Should be valid (not yet expired)
        assert result.status == VerificationStatus.VALID
        assert result.is_valid is True
    
    def test_verify_token_with_minimal_amount(self):
        """Test token with minimal valid amount (0.01)."""
        token = ACPDelegatedToken(
            token_id="acp-minimal-123",
            psp_id="psp-456",
            merchant_id="merchant-789",
            max_amount=Decimal("0.01"),  # Minimum valid
            currency="USD",
            expires_at=datetime.utcnow() + timedelta(days=1),
            constraints={}
        )
        
        result = verify_acp_token(token)
        
        assert result.status == VerificationStatus.VALID
        assert result.amount_limit == 0.01
    
    def test_verify_token_with_large_amount(self):
        """Test token with large amount."""
        token = ACPDelegatedToken(
            token_id="acp-large-123",
            psp_id="psp-456",
            merchant_id="merchant-789",
            max_amount=Decimal("999999.99"),
            currency="USD",
            expires_at=datetime.utcnow() + timedelta(days=1),
            constraints={}
        )
        
        result = verify_acp_token(token)
        
        assert result.status == VerificationStatus.VALID
        assert result.amount_limit == 999999.99
    
    def test_verify_token_with_multiple_constraints(self):
        """Test token with multiple constraints (none matching merchant)."""
        token = ACPDelegatedToken(
            token_id="acp-multi-123",
            psp_id="psp-456",
            merchant_id="merchant-test",
            max_amount=Decimal("2000.00"),
            currency="EUR",
            expires_at=datetime.utcnow() + timedelta(days=30),
            constraints={
                "category": "food",
                "item": "groceries",
                "location": "france"
                # No merchant constraint = should pass
            }
        )
        
        result = verify_acp_token(token)
        
        assert result.status == VerificationStatus.VALID
        assert result.is_valid is True
    
    def test_verify_token_timezone_aware(self):
        """Test verification with timezone-aware datetime."""
        # Create timezone-aware expiration
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        
        token = ACPDelegatedToken(
            token_id="acp-tz-123",
            psp_id="psp-456",
            merchant_id="merchant-789",
            max_amount=Decimal("3000.00"),
            currency="USD",
            expires_at=expires,
            constraints={}
        )
        
        result = verify_acp_token(token)
        
        assert result.status == VerificationStatus.VALID
        assert result.is_valid is True
    
    def test_verify_result_to_dict(self):
        """Test that verification result can be serialized to dict."""
        token = ACPDelegatedToken(
            token_id="acp-dict-123",
            psp_id="psp-456",
            merchant_id="merchant-789",
            max_amount=Decimal("1500.00"),
            currency="GBP",
            expires_at=datetime.utcnow() + timedelta(days=30),
            constraints={"category": "services"}
        )
        
        result = verify_acp_token(token)
        result_dict = result.to_dict()
        
        # Assertions
        assert isinstance(result_dict, dict)
        assert result_dict['status'] == 'VALID'
        assert result_dict['issuer'] == 'psp-456'
        assert result_dict['subject'] == 'merchant-789'
        assert result_dict['amount_limit'] == 1500.00
        assert result_dict['currency'] == 'GBP'
        assert 'expires_at' in result_dict
        assert 'details' in result_dict


class TestACPConstraintValidation:
    """Test constraint-specific validation logic."""
    
    def test_constraint_merchant_exact_match(self):
        """Test exact merchant constraint matching."""
        token = ACPDelegatedToken(
            token_id="acp-exact-123",
            psp_id="psp-456",
            merchant_id="merchant-acme-corp",
            max_amount=Decimal("5000.00"),
            currency="USD",
            expires_at=datetime.utcnow() + timedelta(days=30),
            constraints={
                "merchant": "merchant-acme-corp"  # Exact match
            }
        )
        
        result = verify_acp_token(token)
        
        assert result.status == VerificationStatus.VALID
        assert result.is_valid is True
    
    def test_constraint_merchant_case_sensitive(self):
        """Test that merchant matching is case-sensitive."""
        token = ACPDelegatedToken(
            token_id="acp-case-123",
            psp_id="psp-456",
            merchant_id="merchant-acme",
            max_amount=Decimal("1000.00"),
            currency="USD",
            expires_at=datetime.utcnow() + timedelta(days=30),
            constraints={
                "merchant": "MERCHANT-ACME"  # Different case
            }
        )
        
        result = verify_acp_token(token)
        
        # Should fail due to case mismatch
        assert result.status == VerificationStatus.SCOPE_INVALID
        assert result.is_valid is False
    
    def test_constraint_other_fields_ignored(self):
        """Test that other constraint fields don't affect merchant validation."""
        token = ACPDelegatedToken(
            token_id="acp-other-123",
            psp_id="psp-456",
            merchant_id="merchant-test",
            max_amount=Decimal("500.00"),
            currency="USD",
            expires_at=datetime.utcnow() + timedelta(days=30),
            constraints={
                "category": "wrong-value",  # Other constraints ignored
                "item": "invalid-item"
            }
        )
        
        result = verify_acp_token(token)
        
        # Should be valid (only merchant constraint checked)
        assert result.status == VerificationStatus.VALID
        assert result.is_valid is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

