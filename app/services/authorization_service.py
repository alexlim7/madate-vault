"""
Authorization Service (Multi-Protocol).

This service provides a unified interface for managing authorizations
across multiple protocols (AP2, ACP).

This is the modern replacement for mandate_service.py which only supports AP2.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.authorization import Authorization, ProtocolType, AuthorizationStatus
from app.services.audit_service import AuditService


class AuthorizationService:
    """
    Service for managing authorizations (multi-protocol).
    
    Supports both AP2 (JWT-VC) and ACP protocols.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_service = AuditService(db)
    
    async def create_ap2_authorization(
        self,
        vc_jwt: str,
        issuer_did: str,
        subject_did: str,
        scope: str,
        amount_limit: str,
        expires_at: datetime,
        tenant_id: str,
        verification_status: str,
        verification_reason: Optional[str] = None,
        verification_details: Optional[Dict[str, Any]] = None,
        verified_at: Optional[datetime] = None,
        user_id: Optional[str] = None
    ) -> Authorization:
        """
        Create an AP2 authorization (for backward compatibility with mandate system).
        
        This method provides the same interface as the legacy mandate creation
        but stores data in the multi-protocol authorizations table.
        
        Args:
            vc_jwt: JWT-VC credential string
            issuer_did: Issuer DID
            subject_did: Subject DID
            scope: Scope string (e.g., "payment.recurring")
            amount_limit: Amount limit as string
            expires_at: Expiration datetime
            tenant_id: Tenant identifier
            verification_status: Verification status
            verification_reason: Verification reason
            verification_details: Verification details
            verified_at: Verification timestamp
            user_id: User who created the authorization
            
        Returns:
            Created Authorization object
        """
        # Parse amount_limit to Decimal
        try:
            amount_decimal = Decimal(amount_limit) if amount_limit else None
        except:
            amount_decimal = None
        
        # Create authorization with AP2 protocol
        authorization = Authorization(
            protocol=ProtocolType.AP2,
            issuer=issuer_did,
            subject=subject_did,
            scope={'scope': scope} if scope else None,
            amount_limit=amount_decimal,
            currency=None,  # AP2 typically doesn't have separate currency field
            expires_at=expires_at,
            status=AuthorizationStatus.VALID if verification_status == 'VALID' else AuthorizationStatus.ACTIVE,
            raw_payload={
                'vc_jwt': vc_jwt,
                'issuer_did': issuer_did,
                'subject_did': subject_did
            },
            tenant_id=tenant_id,
            verification_status=verification_status,
            verification_reason=verification_reason,
            verification_details=verification_details,
            verified_at=verified_at,
            created_by=user_id
        )
        
        self.db.add(authorization)
        await self.db.commit()
        await self.db.refresh(authorization)
        
        # Log creation
        await self.audit_service.log_event(
            mandate_id=str(authorization.id),
            event_type="CREATED",
            details={
                "protocol": "AP2",
                "issuer": issuer_did,
                "subject": subject_did,
                "scope": scope,
                "amount_limit": amount_limit,
                "verification_status": verification_status,
                "created_via": "mandate_service_legacy_compatibility",
                "user_id": user_id
            }
        )
        
        return authorization
    
    async def get_authorization(self, authorization_id: str) -> Optional[Authorization]:
        """Get authorization by ID."""
        result = await self.db.execute(
            select(Authorization).where(
                and_(
                    Authorization.id == authorization_id,
                    Authorization.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_authorization_status(
        self,
        authorization_id: str,
        status: AuthorizationStatus,
        reason: Optional[str] = None
    ) -> Optional[Authorization]:
        """Update authorization status."""
        authorization = await self.get_authorization(authorization_id)
        
        if not authorization:
            return None
        
        old_status = authorization.status
        authorization.status = status
        
        if status == AuthorizationStatus.REVOKED:
            authorization.revoked_at = datetime.now(timezone.utc)
            authorization.revoke_reason = reason
        
        await self.db.commit()
        await self.db.refresh(authorization)
        
        # Log status change
        await self.audit_service.log_event(
            mandate_id=str(authorization.id),
            event_type="REVOKED" if status == AuthorizationStatus.REVOKED else "STATUS_CHANGED",
            details={
                "protocol": authorization.protocol,
                "old_status": old_status,
                "new_status": status,
                "reason": reason
            }
        )
        
        return authorization
    
    async def soft_delete_authorization(
        self,
        authorization_id: str,
        retention_days: int = 90
    ) -> Optional[Authorization]:
        """Soft delete an authorization."""
        authorization = await self.get_authorization(authorization_id)
        
        if not authorization:
            return None
        
        authorization.deleted_at = datetime.now(timezone.utc)
        authorization.retention_days = retention_days
        
        await self.db.commit()
        await self.db.refresh(authorization)
        
        # Log soft delete
        await self.audit_service.log_event(
            mandate_id=str(authorization.id),
            event_type="SOFT_DELETE",
            details={
                "protocol": authorization.protocol,
                "deleted_at": authorization.deleted_at.isoformat(),
                "retention_days": retention_days
            }
        )
        
        return authorization
    
    async def search_authorizations(
        self,
        tenant_id: str,
        protocol: Optional[ProtocolType] = None,
        status: Optional[AuthorizationStatus] = None,
        issuer: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[Authorization], int]:
        """
        Search authorizations with filters.
        
        Returns:
            Tuple of (authorizations, total_count)
        """
        conditions = [
            Authorization.tenant_id == tenant_id,
            Authorization.deleted_at.is_(None)
        ]
        
        if protocol:
            conditions.append(Authorization.protocol == protocol)
        
        if status:
            conditions.append(Authorization.status == status)
        
        if issuer:
            conditions.append(Authorization.issuer == issuer)
        
        if subject:
            conditions.append(Authorization.subject == subject)
        
        # Get total count
        count_query = select(func.count(Authorization.id)).where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = select(Authorization).where(and_(*conditions)).limit(limit).offset(offset)
        result = await self.db.execute(query)
        authorizations = result.scalars().all()
        
        return list(authorizations), total


