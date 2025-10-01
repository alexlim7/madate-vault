"""
Enhanced verification service with signature validation and detailed status codes.
"""
import jwt
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from app.services.truststore_service import truststore_service
from app.utils.jwt_verification import verify_jwt_vc, JWTVerificationError
from app.core.monitoring import jwt_verifications_total, monitor_operation

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Verification status enumeration."""
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    SIG_INVALID = "SIG_INVALID"
    ISSUER_UNKNOWN = "ISSUER_UNKNOWN"
    INVALID_FORMAT = "INVALID_FORMAT"
    SCOPE_INVALID = "SCOPE_INVALID"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"


class VerificationResult:
    """Result of mandate verification."""
    
    def __init__(self, status: VerificationStatus, reason: str = "", details: Optional[Dict] = None):
        self.status = status
        self.reason = reason
        self.details = details or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "reason": self.reason,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }
    
    @property
    def is_valid(self) -> bool:
        """Check if verification is valid."""
        return self.status == VerificationStatus.VALID


class VerificationService:
    """Service for comprehensive mandate verification."""
    
    def __init__(self):
        self.truststore = truststore_service
    
    async def verify_mandate(self, vc_jwt: str, expected_scope: Optional[str] = None) -> VerificationResult:
        """
        Perform comprehensive mandate verification.
        
        Args:
            vc_jwt: JWT-VC token
            expected_scope: Expected scope (optional)
            
        Returns:
            VerificationResult with status and details
        """
        try:
            # Step 1: Decode and basic structure validation
            structure_result = self._verify_structure(vc_jwt)
            if not structure_result.is_valid:
                return structure_result
            
            payload = structure_result.details.get("payload", {})
            issuer_did = payload.get("iss")
            
            # Step 2: Verify signature using issuer JWKs
            signature_result = await self._verify_signature(vc_jwt, issuer_did)
            if not signature_result.is_valid:
                return signature_result
            
            # Step 3: Validate expiry
            expiry_result = self._verify_expiry(payload)
            if not expiry_result.is_valid:
                return expiry_result
            
            # Step 4: Validate scope if provided
            if expected_scope:
                scope_result = self._verify_scope(payload, expected_scope)
                if not scope_result.is_valid:
                    return scope_result
            
            # All checks passed
            return VerificationResult(
                status=VerificationStatus.VALID,
                reason="All verification checks passed",
                details={
                    "issuer_did": issuer_did,
                    "subject_did": payload.get("sub"),
                    "scope": payload.get("scope"),
                    "amount_limit": payload.get("amount_limit"),
                    "expires_at": payload.get("exp"),
                    "issued_at": payload.get("iat"),
                    "payload": payload
                }
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during verification: {str(e)}")
            return VerificationResult(
                status=VerificationStatus.INVALID_FORMAT,
                reason=f"Unexpected error: {str(e)}"
            )
    
    def _verify_structure(self, vc_jwt: str) -> VerificationResult:
        """
        Verify JWT structure and basic format.
        
        Args:
            vc_jwt: JWT token
            
        Returns:
            VerificationResult
        """
        try:
            # Use existing JWT verification
            verification_result = verify_jwt_vc(vc_jwt)
            
            if not verification_result["is_valid"]:
                errors = verification_result.get("errors", [])
                return VerificationResult(
                    status=VerificationStatus.INVALID_FORMAT,
                    reason=f"Invalid JWT structure: {', '.join(errors)}",
                    details={"errors": errors}
                )
            
            # Extract payload
            payload = verification_result.get("parsed_payload", {})
            
            # Check required fields
            required_fields = ["iss", "sub", "iat", "exp"]
            missing_fields = [field for field in required_fields if field not in payload]
            
            if missing_fields:
                return VerificationResult(
                    status=VerificationStatus.MISSING_REQUIRED_FIELD,
                    reason=f"Missing required fields: {', '.join(missing_fields)}",
                    details={"missing_fields": missing_fields}
                )
            
            return VerificationResult(
                status=VerificationStatus.VALID,
                reason="JWT structure is valid",
                details={
                    "payload": payload,
                    "header": verification_result.get("header", {}),
                    "warnings": verification_result.get("warnings", [])
                }
            )
            
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.INVALID_FORMAT,
                reason=f"Failed to decode JWT: {str(e)}"
            )
    
    async def _verify_signature(self, vc_jwt: str, issuer_did: str) -> VerificationResult:
        """
        Verify JWT signature using issuer JWKs.
        
        Args:
            vc_jwt: JWT token
            issuer_did: Issuer DID
            
        Returns:
            VerificationResult
        """
        try:
            # Check if issuer is known
            jwk_set = await self.truststore.get_issuer_keys(issuer_did)
            if not jwk_set:
                return VerificationResult(
                    status=VerificationStatus.ISSUER_UNKNOWN,
                    reason=f"Issuer not found in truststore: {issuer_did}",
                    details={"issuer_did": issuer_did}
                )
            
            # Verify signature
            is_valid = await self.truststore.verify_signature(vc_jwt, issuer_did)
            
            if is_valid:
                return VerificationResult(
                    status=VerificationStatus.VALID,
                    reason="Signature verification successful",
                    details={"issuer_did": issuer_did}
                )
            else:
                return VerificationResult(
                    status=VerificationStatus.SIG_INVALID,
                    reason="Invalid signature",
                    details={"issuer_did": issuer_did}
                )
                
        except Exception as e:
            logger.error(f"Error during signature verification: {str(e)}")
            return VerificationResult(
                status=VerificationStatus.SIG_INVALID,
                reason=f"Signature verification failed: {str(e)}"
            )
    
    def _verify_expiry(self, payload: Dict) -> VerificationResult:
        """
        Verify token expiry.
        
        Args:
            payload: JWT payload
            
        Returns:
            VerificationResult
        """
        try:
            exp = payload.get("exp")
            if not exp:
                return VerificationResult(
                    status=VerificationStatus.MISSING_REQUIRED_FIELD,
                    reason="Missing expiration claim"
                )
            
            # Convert to datetime
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            
            if exp_datetime <= now:
                return VerificationResult(
                    status=VerificationStatus.EXPIRED,
                    reason=f"Token expired at {exp_datetime.isoformat()}",
                    details={
                        "expires_at": exp_datetime.isoformat(),
                        "current_time": now.isoformat()
                    }
                )
            
            return VerificationResult(
                status=VerificationStatus.VALID,
                reason="Token is not expired",
                details={
                    "expires_at": exp_datetime.isoformat(),
                    "current_time": now.isoformat()
                }
            )
            
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.INVALID_FORMAT,
                reason=f"Invalid expiration claim: {str(e)}"
            )
    
    def _verify_scope(self, payload: Dict, expected_scope: str) -> VerificationResult:
        """
        Verify token scope.
        
        Args:
            payload: JWT payload
            expected_scope: Expected scope
            
        Returns:
            VerificationResult
        """
        try:
            actual_scope = payload.get("scope")
            
            if not actual_scope:
                return VerificationResult(
                    status=VerificationStatus.SCOPE_INVALID,
                    reason="Missing scope claim"
                )
            
            if actual_scope != expected_scope:
                return VerificationResult(
                    status=VerificationStatus.SCOPE_INVALID,
                    reason=f"Scope mismatch: expected '{expected_scope}', got '{actual_scope}'",
                    details={
                        "expected_scope": expected_scope,
                        "actual_scope": actual_scope
                    }
                )
            
            return VerificationResult(
                status=VerificationStatus.VALID,
                reason="Scope verification successful",
                details={"scope": actual_scope}
            )
            
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.SCOPE_INVALID,
                reason=f"Scope verification failed: {str(e)}"
            )
    
    async def get_truststore_status(self) -> Dict[str, Any]:
        """
        Get truststore status.
        
        Returns:
            Truststore status information
        """
        return self.truststore.get_truststore_status()


# Global verification service instance
verification_service = VerificationService()


