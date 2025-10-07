"""
ACP Token Verification Logic.

Implements verification rules for ACP (Authorization Credential Protocol) tokens.
"""
from datetime import datetime, timezone
from typing import Optional

from app.protocols.acp.schemas import ACPDelegatedToken
from app.services.types import VerificationResult, VerificationStatus


def verify_acp_token(token: ACPDelegatedToken) -> VerificationResult:
    """
    Verify an ACP delegated token according to ACP protocol rules.
    
    Validation Rules:
    1. Expiration check: Token must not be expired
    2. Amount validation: max_amount must be positive
    3. Constraint validation: If constraints.merchant exists, must match merchant_id
    
    Args:
        token: ACPDelegatedToken to verify
    
    Returns:
        VerificationResult with verification status and details
    
    Example:
        >>> from decimal import Decimal
        >>> from datetime import datetime, timedelta
        >>> 
        >>> token = ACPDelegatedToken(
        ...     token_id="acp-123",
        ...     psp_id="psp-456",
        ...     merchant_id="merchant-789",
        ...     max_amount=Decimal("5000.00"),
        ...     currency="USD",
        ...     expires_at=datetime.utcnow() + timedelta(days=30),
        ...     constraints={}
        ... )
        >>> result = verify_acp_token(token)
        >>> print(result.status)  # VerificationStatus.VALID
    """
    
    # Rule 1: Check expiration
    now = datetime.now(timezone.utc)
    
    # Handle both timezone-aware and naive datetimes
    token_expires = token.expires_at
    if token_expires.tzinfo is None:
        # Token is naive, compare with naive now
        now = datetime.utcnow()
    
    if now >= token_expires:
        return VerificationResult(
            status=VerificationStatus.EXPIRED,
            reason=f"Token expired at {token_expires.isoformat()}",
            expires_at=token_expires,
            amount_limit=float(token.max_amount),
            currency=token.currency,
            issuer=token.psp_id,
            subject=token.merchant_id,
            scope={'constraints': token.constraints},
            details={
                'token_id': token.token_id,
                'expired_at': token_expires.isoformat(),
                'checked_at': now.isoformat()
            }
        )
    
    # Rule 2: Validate max_amount is positive
    if token.max_amount <= 0:
        return VerificationResult(
            status=VerificationStatus.REVOKED,
            reason=f"Invalid authorization limit: max_amount must be positive (got {token.max_amount})",
            expires_at=token_expires,
            amount_limit=float(token.max_amount),
            currency=token.currency,
            issuer=token.psp_id,
            subject=token.merchant_id,
            scope={'constraints': token.constraints},
            details={
                'token_id': token.token_id,
                'error_code': 'INVALID_LIMIT',
                'max_amount': str(token.max_amount)
            }
        )
    
    # Rule 3: Validate constraint matching
    constraint_merchant = token.constraints.get('merchant')
    
    if constraint_merchant is not None:
        # If merchant constraint exists, it must match the merchant_id
        if constraint_merchant != token.merchant_id:
            return VerificationResult(
                status=VerificationStatus.SCOPE_INVALID,
                reason=(
                    f"Constraint mismatch: constraint.merchant '{constraint_merchant}' "
                    f"does not match merchant_id '{token.merchant_id}'"
                ),
                expires_at=token_expires,
                amount_limit=float(token.max_amount),
                currency=token.currency,
                issuer=token.psp_id,
                subject=token.merchant_id,
                scope={'constraints': token.constraints},
                details={
                    'token_id': token.token_id,
                    'error_code': 'MERCHANT_MISMATCH',
                    'expected_merchant': token.merchant_id,
                    'constraint_merchant': constraint_merchant
                }
            )
    
    # All validations passed
    return VerificationResult(
        status=VerificationStatus.VALID,
        reason="ACP token verification successful",
        expires_at=token_expires,
        amount_limit=float(token.max_amount),
        currency=token.currency,
        issuer=token.psp_id,
        subject=token.merchant_id,
        scope={'constraints': token.constraints},
        details={
            'token_id': token.token_id,
            'protocol': 'ACP',
            'verified_at': now.isoformat(),
            'psp_id': token.psp_id,
            'merchant_id': token.merchant_id,
            'constraints': token.constraints
        }
    )


def verify_acp_credential(credential_dict: dict) -> VerificationResult:
    """
    Verify ACP credential from raw dictionary.
    
    Convenience function that parses the credential and verifies it.
    
    Args:
        credential_dict: Raw ACP credential dictionary
    
    Returns:
        VerificationResult
    
    Raises:
        ValueError: If credential format is invalid
    
    Example:
        >>> credential = {
        ...     'token_id': 'acp-123',
        ...     'psp_id': 'psp-456',
        ...     'merchant_id': 'merchant-789',
        ...     'max_amount': '5000.00',
        ...     'currency': 'USD',
        ...     'expires_at': '2026-01-01T00:00:00Z'
        ... }
        >>> result = verify_acp_credential(credential)
    """
    try:
        # Parse credential
        token = ACPDelegatedToken.from_dict(credential_dict)
    except Exception as e:
        # Invalid format
        return VerificationResult(
            status=VerificationStatus.INVALID_FORMAT,
            reason=f"Invalid ACP credential format: {str(e)}",
            details={'error': str(e)}
        )
    
    # Verify token
    return verify_acp_token(token)


