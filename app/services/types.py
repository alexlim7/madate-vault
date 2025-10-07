"""
Shared types for services.

Common types used across multiple service modules.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class VerificationStatus(str, Enum):
    """Verification status codes (protocol-agnostic)."""
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    SIG_INVALID = "SIG_INVALID"
    ISSUER_UNKNOWN = "ISSUER_UNKNOWN"
    INVALID_FORMAT = "INVALID_FORMAT"
    SCOPE_INVALID = "SCOPE_INVALID"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    REVOKED = "REVOKED"


class VerificationResult:
    """
    Protocol-agnostic verification result.
    
    Returned by all protocol verifiers (AP2, ACP, etc.)
    
    Attributes:
        status: Verification status code
        reason: Human-readable reason
        expires_at: Credential expiration timestamp
        amount_limit: Maximum amount (numeric)
        currency: ISO 4217 currency code (e.g., "USD")
        issuer: Issuer identifier (DID, PSP ID, etc.)
        subject: Subject identifier (DID, merchant ID, etc.)
        scope: Protocol-specific scope/constraints
        details: Additional verification details
    """
    
    def __init__(
        self,
        status: VerificationStatus,
        reason: str,
        expires_at: Optional[datetime] = None,
        amount_limit: Optional[float] = None,
        currency: Optional[str] = None,
        issuer: Optional[str] = None,
        subject: Optional[str] = None,
        scope: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status = status
        self.reason = reason
        self.expires_at = expires_at
        self.amount_limit = amount_limit
        self.currency = currency
        self.issuer = issuer
        self.subject = subject
        self.scope = scope or {}
        self.details = details or {}
    
    @property
    def is_valid(self) -> bool:
        """Check if verification passed."""
        return self.status == VerificationStatus.VALID
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "reason": self.reason,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "amount_limit": float(self.amount_limit) if self.amount_limit else None,
            "currency": self.currency,
            "issuer": self.issuer,
            "subject": self.subject,
            "scope": self.scope,
            "details": self.details
        }
    
    def __repr__(self) -> str:
        return f"VerificationResult(status={self.status.value}, reason='{self.reason}')"


