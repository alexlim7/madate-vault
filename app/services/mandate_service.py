"""
Mandate service for business logic.

⚠️ DEPRECATED: This service is maintained for backward compatibility only.

USE app.services.authorization_service.AuthorizationService FOR NEW CODE.

This service now acts as a facade that writes to the multi-protocol
`authorizations` table with protocol='AP2', but returns legacy Mandate objects
to maintain API compatibility.

Migration Path:
- Legacy /mandates endpoints use this service internally
- Data is stored in authorizations table with protocol='AP2'
- mandate_view provides backward-compatible queries
- New code should use AuthorizationService directly

TODO: Remove this service once all clients migrate to /authorizations endpoint.
      Target: v2.0 (Q2 2026)
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
import uuid

from app.models.mandate import Mandate
from app.models.authorization import Authorization, ProtocolType
from app.models.customer import Customer
from app.schemas.mandate import MandateSearch, MandateUpdate
from app.services.verification_service import verification_service, VerificationResult
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.webhook_service import WebhookService, WebhookEvent
from app.services.alert_service import AlertService
from app.core.monitoring import (
    mandates_created_total,
    mandates_active,
    monitor_operation
)


class MandateService:
    """
    Service class for mandate operations.
    
    ⚠️ DEPRECATED: This service maintains backward compatibility for legacy clients.
    
    Internally uses AuthorizationService to write to the authorizations table
    with protocol='AP2', then converts results to Mandate objects for API compatibility.
    
    New integrations should use AuthorizationService directly.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_service = AuditService(db)
        self.authorization_service = AuthorizationService(db)
        self.webhook_service = WebhookService(db)
        self.alert_service = AlertService(db)
    
    async def create_mandate(self, vc_jwt: str, tenant_id: str, retention_days: int = 90,
                                user_id: Optional[str] = None, ip_address: Optional[str] = None,
                                user_agent: Optional[str] = None) -> Mandate:
        """
        Create a new mandate from JWT-VC token.
        
        ⚠️ DEPRECATED: This method now writes to authorizations table with protocol='AP2'
        for backward compatibility. New code should use AuthorizationService directly.

        Args:
            vc_jwt: JWT-VC token string
            tenant_id: Tenant ID for multi-tenancy
            retention_days: Number of days to retain after deletion
            user_id: Optional user ID for audit logging
            ip_address: Optional IP address for audit logging
            user_agent: Optional user agent for audit logging

        Returns:
            Created mandate object (facade over Authorization)

        Raises:
            ValueError: If JWT verification fails or tenant doesn't exist
        """
        # Verify tenant exists
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            # Log the tenant lookup failure
            await self.audit_service.log_event(
                mandate_id=None,
                event_type="TENANT_NOT_FOUND",
                details={
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "ip_address": ip_address,
                    "user_agent": user_agent
                }
            )
            raise ValueError(f"Tenant with ID {tenant_id} not found")
        
        # Perform comprehensive verification
        verification_result = await verification_service.verify_mandate(vc_jwt)
        
        # Check if verification passed
        if not verification_result.is_valid:
            raise ValueError(f"JWT verification failed: {verification_result.reason}")
        
        # Extract data from verification result
        extracted_data = verification_result.details
        
        # Create authorization using the new multi-protocol service
        # This stores in authorizations table with protocol='AP2'
        authorization = await self.authorization_service.create_ap2_authorization(
            vc_jwt=vc_jwt,
            issuer_did=extracted_data.get("issuer_did"),
            subject_did=extracted_data.get("subject_did"),
            scope=extracted_data.get("scope"),
            amount_limit=extracted_data.get("amount_limit"),
            expires_at=datetime.fromtimestamp(extracted_data["expires_at"]) if extracted_data.get("expires_at") else None,
            tenant_id=tenant_id,
            verification_status=verification_result.status.value,
            verification_reason=verification_result.reason,
            verification_details=verification_result.to_dict(),
            verified_at=datetime.utcnow(),
            user_id=user_id
        )
        
        # Record metrics
        mandates_created_total.labels(
            tenant_id=tenant_id,
            verification_status=verification_result.status.value
        ).inc()
        
        # Convert Authorization to Mandate for backward compatibility
        # This allows legacy API to return Mandate objects
        mandate = self._authorization_to_mandate(authorization)
        
        # Send webhook event
        try:
            await self.webhook_service.send_webhook_event(
                event_type=WebhookEvent.MANDATE_CREATED,
                mandate=mandate,
                tenant_id=tenant_id,
                additional_data={
                    "verification_result": verification_result.to_dict()
                }
            )
        except Exception as e:
            # Log webhook error but don't fail mandate creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send webhook event for mandate {mandate.id}: {str(e)}")
        
        # Create alert if verification failed
        if mandate.verification_status != "VALID":
            try:
                await self.alert_service.create_verification_failed_alert(
                    mandate=mandate,
                    verification_reason=mandate.verification_reason or "Unknown verification failure"
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create verification failed alert for mandate {mandate.id}: {str(e)}")
        
        return mandate
    
    async def get_mandate_by_id(self, mandate_id: str, tenant_id: str, include_deleted: bool = False) -> Optional[Mandate]:
        """Get mandate by database ID."""
        query = select(Mandate).where(
            and_(
                Mandate.id == uuid.UUID(mandate_id),
                Mandate.tenant_id == uuid.UUID(tenant_id)
            )
        )
        
        if not include_deleted:
            query = query.where(Mandate.deleted_at.is_(None))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_mandate(self, mandate_id: str, tenant_id: str, update_data: MandateUpdate,
                           user_id: Optional[str] = None, ip_address: Optional[str] = None,
                           user_agent: Optional[str] = None) -> Optional[Mandate]:
        """Update a mandate."""
        mandate = await self.get_mandate_by_id(mandate_id, tenant_id)
        if not mandate:
            return None
        
        # Update fields
        if update_data.status:
            mandate.status = update_data.status.value
        if update_data.scope is not None:
            mandate.scope = update_data.scope
        if update_data.amount_limit is not None:
            mandate.amount_limit = update_data.amount_limit
        if update_data.retention_days:
            mandate.retention_days = update_data.retention_days
        
        await self.db.commit()
        await self.db.refresh(mandate)
        
        # Log audit event
        await self.audit_service.log_event(
            mandate_id=mandate.id,
            event_type="UPDATE",
            details={
                "updated_fields": update_data.dict(exclude_unset=True),
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
        )
        
        return mandate
    
    async def soft_delete_mandate(self, mandate_id: str, tenant_id: str,
                                user_id: Optional[str] = None, ip_address: Optional[str] = None,
                                user_agent: Optional[str] = None) -> bool:
        """Soft delete a mandate."""
        mandate = await self.get_mandate_by_id(mandate_id, tenant_id)
        if not mandate:
            return False
        
        mandate.soft_delete()
        await self.db.commit()
        
        # Log audit event
        await self.audit_service.log_event(
            mandate_id=mandate.id,
            event_type="SOFT_DELETE",
            details={
                "deleted_at": mandate.deleted_at.isoformat(),
                "retention_days": mandate.retention_days,
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
        )
        
        return True
    
    async def restore_mandate(self, mandate_id: str, tenant_id: str,
                            user_id: Optional[str] = None, ip_address: Optional[str] = None,
                            user_agent: Optional[str] = None) -> bool:
        """Restore a soft-deleted mandate."""
        mandate = await self.get_mandate_by_id(mandate_id, tenant_id, include_deleted=True)
        if not mandate or not mandate.is_deleted:
            return False
        
        mandate.deleted_at = None
        mandate.status = "active"
        await self.db.commit()
        
        # Log audit event
        await self.audit_service.log_event(
            mandate_id=mandate.id,
            event_type="RESTORE",
            details={
                "restored_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
        )
        
        return True
    
    async def search_mandates(self, search_params: MandateSearch, tenant_id: str) -> Dict[str, Any]:
        """
        Search mandates with filters.
        
        Args:
            search_params: Search parameters
            tenant_id: Tenant ID for multi-tenancy
            
        Returns:
            Dictionary with mandates and pagination info
        """
        query = select(Mandate).where(Mandate.tenant_id == uuid.UUID(tenant_id))
        
        # Apply filters
        conditions = []
        
        if search_params.issuer_did:
            conditions.append(Mandate.issuer_did == search_params.issuer_did)
        
        if search_params.subject_did:
            conditions.append(Mandate.subject_did == search_params.subject_did)
        
        if search_params.status:
            conditions.append(Mandate.status == search_params.status.value)
        
        if search_params.scope:
            conditions.append(Mandate.scope == search_params.scope)
        
        if search_params.expires_before:
            conditions.append(Mandate.expires_at < search_params.expires_before)
        
        # Handle soft-delete filter
        if not search_params.include_deleted:
            conditions.append(Mandate.deleted_at.is_(None))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(Mandate.id).where(Mandate.tenant_id == uuid.UUID(tenant_id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())
        
        # Apply pagination
        query = query.offset(search_params.offset).limit(search_params.limit)
        query = query.order_by(Mandate.created_at.desc())
        
        result = await self.db.execute(query)
        mandates = result.scalars().all()
        
        return {
            "mandates": mandates,
            "total": total,
            "limit": search_params.limit,
            "offset": search_params.offset
        }
    
    async def get_tenant(self, tenant_id: str) -> Optional[Customer]:
        """Get tenant by ID."""
        result = await self.db.execute(
            select(Customer).where(Customer.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    async def cleanup_expired_retention(self) -> int:
        """
        Clean up mandates that have exceeded their retention period.
        
        Returns:
            Number of mandates cleaned up
        """
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=365)  # Max retention
        
        # Find mandates that should be cleaned up
        query = select(Mandate).where(
            and_(
                Mandate.deleted_at.is_not(None),
                Mandate.deleted_at < cutoff_date
            )
        )
        
        result = await self.db.execute(query)
        mandates_to_cleanup = result.scalars().all()
        
        count = 0
        for mandate in mandates_to_cleanup:
            if not mandate.should_be_retained:
                # Log cleanup event
                await self.audit_service.log_event(
                    mandate_id=mandate.id,
                    event_type="DELETE",
                    details={
                        "cleanup_reason": "retention_period_expired",
                        "deleted_at": mandate.deleted_at.isoformat(),
                        "retention_days": mandate.retention_days
                    }
                )
                
                # Delete the mandate permanently
                await self.db.delete(mandate)
                count += 1
        
        await self.db.commit()
        return count
    
    def _authorization_to_mandate(self, authorization: Authorization) -> Mandate:
        """
        Convert Authorization to Mandate for backward compatibility.
        
        Creates a Mandate facade object from an Authorization.
        This is a memory-only object that provides the legacy interface
        while the actual data lives in the authorizations table.
        
        Args:
            authorization: Authorization object (protocol must be AP2)
            
        Returns:
            Mandate object (not persisted)
        """
        if authorization.protocol != ProtocolType.AP2:
            raise ValueError("Can only convert AP2 authorizations to Mandate objects")
        
        # Create Mandate object from Authorization data
        # Note: This is a facade - not saved to mandates table
        mandate = Mandate(
            id=authorization.id,
            vc_jwt=authorization.raw_payload.get('vc_jwt', ''),
            issuer_did=authorization.issuer,
            subject_did=authorization.subject,
            scope=authorization.scope.get('scope') if authorization.scope else None,
            amount_limit=str(authorization.amount_limit) if authorization.amount_limit else None,
            expires_at=authorization.expires_at,
            status='active' if authorization.status == 'VALID' or authorization.status == 'ACTIVE' else 'expired',
            tenant_id=authorization.tenant_id,
            verification_status=authorization.verification_status,
            verification_reason=authorization.verification_reason,
            verification_details=authorization.verification_details,
            verified_at=authorization.verified_at,
            retention_days=authorization.retention_days or 90,
            deleted_at=authorization.deleted_at,
            created_at=authorization.created_at,
            updated_at=authorization.updated_at
        )
        
        # Mark that this object should not be persisted
        # (it's just a view over authorization data)
        mandate._sa_instance_state.detached = True
        
        return mandate
