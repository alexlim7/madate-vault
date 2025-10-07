"""
Verification Dispatcher - Protocol-agnostic verification routing.

This module routes verification requests to the appropriate protocol handler
(AP2, ACP, etc.) based on the protocol type.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.services.types import VerificationResult, VerificationStatus
from app.services.verification_service import verification_service as ap2_verifier

logger = logging.getLogger(__name__)


class VerificationDispatcher:
    """
    Dispatcher that routes verification to protocol-specific handlers.
    
    Supports:
    - AP2 (JWT-VC): Delegates to existing verification_service
    - ACP: New ACP verification logic (to be implemented)
    
    Usage:
        dispatcher = VerificationDispatcher()
        result = await dispatcher.verify_authorization(
            payload={'vc_jwt': '...'},
            protocol='AP2'
        )
    """
    
    def __init__(self):
        self.ap2_verifier = ap2_verifier
        # Future: self.acp_verifier = acp_verifier
    
    async def verify_authorization(
        self,
        payload: Dict[str, Any],
        protocol: str
    ) -> VerificationResult:
        """
        Verify an authorization credential based on protocol.
        
        Args:
            payload: Credential payload (protocol-specific format)
                     AP2: {"vc_jwt": "eyJhbGc...", ...}
                     ACP: {"credential": {...}, ...}
            protocol: Protocol type ("AP2" or "ACP")
        
        Returns:
            VerificationResult with verification status and details
        
        Raises:
            ValueError: If protocol is not supported
        
        Example:
            >>> result = await dispatcher.verify_authorization(
            ...     payload={'vc_jwt': 'eyJhbGc...'},
            ...     protocol='AP2'
            ... )
            >>> print(result.status)  # VerificationStatus.VALID
        """
        protocol = protocol.upper()
        
        if protocol == "AP2":
            return await self._verify_ap2(payload)
        elif protocol == "ACP":
            return await self._verify_acp(payload)
        else:
            logger.error(f"Unsupported protocol: {protocol}")
            return VerificationResult(
                status=VerificationStatus.INVALID_FORMAT,
                reason=f"Unsupported protocol: {protocol}"
            )
    
    async def _verify_ap2(self, payload: Dict[str, Any]) -> VerificationResult:
        """
        Verify AP2 (JWT-VC) credential.
        
        Delegates to existing verification_service for AP2 verification.
        
        Args:
            payload: Must contain 'vc_jwt' field
        
        Returns:
            VerificationResult
        """
        # Extract JWT from payload
        vc_jwt = payload.get('vc_jwt')
        if not vc_jwt:
            return VerificationResult(
                status=VerificationStatus.MISSING_REQUIRED_FIELD,
                reason="Missing required field: vc_jwt"
            )
        
        # Delegate to existing AP2 verifier
        ap2_result = await self.ap2_verifier.verify_mandate(vc_jwt)
        
        # Convert AP2 VerificationResult to shared VerificationResult
        return self._convert_ap2_result(ap2_result)
    
    async def _verify_acp(self, payload: Dict[str, Any]) -> VerificationResult:
        """
        Verify ACP (Authorization Credential Protocol) credential.
        
        Args:
            payload: ACP credential payload
        
        Returns:
            VerificationResult
        
        TODO: Implement full ACP verification logic.
              This is currently a stub that performs basic validation.
        """
        # TODO: Implement ACP verification
        # For now, this is a stub implementation
        
        logger.info("ACP verification requested (stub implementation)")
        
        # Basic validation
        if not payload:
            return VerificationResult(
                status=VerificationStatus.INVALID_FORMAT,
                reason="Empty ACP credential payload"
            )
        
        # Check for required ACP fields
        required_fields = ['credential', 'psp_id', 'merchant_id']
        missing_fields = [f for f in required_fields if f not in payload]
        
        if missing_fields:
            return VerificationResult(
                status=VerificationStatus.MISSING_REQUIRED_FIELD,
                reason=f"Missing required ACP fields: {', '.join(missing_fields)}"
            )
        
        # TODO: Implement actual ACP verification:
        # 1. Verify JSON-LD structure
        # 2. Validate linked data proof
        # 3. Check issuer (PSP) is trusted
        # 4. Validate constraints/scope
        # 5. Check expiration
        
        # Stub: Return valid for now (TO BE IMPLEMENTED)
        logger.warning("ACP verification stub - returning placeholder result")
        
        return VerificationResult(
            status=VerificationStatus.VALID,  # STUB: Should be actual verification
            reason="ACP verification stub (to be implemented)",
            issuer=payload.get('psp_id'),
            subject=payload.get('merchant_id'),
            expires_at=self._parse_acp_expiry(payload),
            amount_limit=self._parse_acp_amount(payload),
            currency=payload.get('currency'),
            scope=payload.get('constraints', {}),
            details={
                "stub": True,
                "message": "ACP verification not yet fully implemented"
            }
        )
    
    def _convert_ap2_result(
        self,
        ap2_result
    ) -> VerificationResult:
        """
        Convert AP2 VerificationResult to shared VerificationResult.
        
        Args:
            ap2_result: Result from verification_service.verify_mandate()
        
        Returns:
            Shared VerificationResult
        """
        # Parse amount and currency from AP2 details
        amount_limit = None
        currency = None
        
        details = ap2_result.details or {}
        amount_str = details.get('amount_limit', '')
        
        if amount_str and isinstance(amount_str, str):
            # Parse "5000.00 USD" format
            parts = amount_str.split()
            if len(parts) >= 1:
                try:
                    amount_limit = float(parts[0].replace(',', ''))
                except ValueError:
                    pass
            if len(parts) >= 2:
                currency = parts[1]
        
        # Parse expiration
        expires_at = None
        if details.get('expires_at'):
            try:
                expires_at = datetime.fromtimestamp(
                    details['expires_at'],
                    tz=timezone.utc
                )
            except (ValueError, TypeError):
                pass
        
        # Map AP2 scope to generic scope format
        scope = {}
        if details.get('scope'):
            scope = {'scope': details['scope']}
        
        return VerificationResult(
            status=VerificationStatus(ap2_result.status.value),
            reason=ap2_result.reason,
            expires_at=expires_at,
            amount_limit=amount_limit,
            currency=currency,
            issuer=details.get('issuer_did'),
            subject=details.get('subject_did'),
            scope=scope,
            details=details
        )
    
    def _parse_acp_expiry(self, payload: Dict[str, Any]) -> Optional[datetime]:
        """
        Parse expiration from ACP credential.
        
        TODO: Implement proper ACP expiry parsing
        """
        # Stub implementation
        exp = payload.get('credential', {}).get('expirationDate')
        if exp:
            try:
                return datetime.fromisoformat(exp.replace('Z', '+00:00'))
            except ValueError:
                pass
        return None
    
    def _parse_acp_amount(self, payload: Dict[str, Any]) -> Optional[float]:
        """
        Parse amount from ACP credential.
        
        TODO: Implement proper ACP amount parsing
        """
        # Stub implementation
        constraints = payload.get('constraints', {})
        max_amount = constraints.get('max_amount')
        
        if max_amount:
            try:
                return float(max_amount)
            except (ValueError, TypeError):
                pass
        
        return None


# Global singleton instance
verification_dispatcher = VerificationDispatcher()


# Convenience function for direct use
async def verify_authorization(
    payload: Dict[str, Any],
    protocol: str
) -> VerificationResult:
    """
    Verify an authorization credential (convenience function).
    
    Args:
        payload: Credential payload
        protocol: Protocol type ("AP2" or "ACP")
    
    Returns:
        VerificationResult
    
    Example:
        >>> result = await verify_authorization(
        ...     payload={'vc_jwt': 'eyJhbGc...'},
        ...     protocol='AP2'
        ... )
    """
    return await verification_dispatcher.verify_authorization(payload, protocol)

