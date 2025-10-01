"""
Alert service for managing system alerts.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.alert import Alert
from app.models.mandate import Mandate

logger = logging.getLogger(__name__)


class AlertType:
    """Alert type constants."""
    MANDATE_EXPIRING = "MANDATE_EXPIRING"
    MANDATE_VERIFICATION_FAILED = "MANDATE_VERIFICATION_FAILED"
    WEBHOOK_DELIVERY_FAILED = "WEBHOOK_DELIVERY_FAILED"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class AlertSeverity:
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertService:
    """Service for managing system alerts."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_alert(
        self,
        tenant_id: str,
        alert_data
    ) -> Alert:
        """
        Create a new alert.
        
        Args:
            tenant_id: Tenant ID
            alert_data: AlertCreate object with alert data
            
        Returns:
            Created alert object
        """
        # Validate severity
        valid_severities = ["info", "warning", "error", "critical"]
        if alert_data.severity not in valid_severities:
            raise ValueError(f"Invalid severity: {alert_data.severity}. Must be one of {valid_severities}")
        
        alert = Alert(
            tenant_id=tenant_id,
            mandate_id=alert_data.mandate_id,
            alert_type=alert_data.alert_type,
            title=alert_data.title,
            message=alert_data.message,
            severity=alert_data.severity,
            is_read=False,
            is_resolved=False
        )
        
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        
        logger.info(f"Created alert: {alert_data.alert_type} for tenant {tenant_id}")
        return alert
    
    async def create_mandate_expiring_alert(
        self,
        mandate: Mandate,
        days_until_expiry: int
    ) -> Alert:
        """Create an alert for a mandate expiring soon."""
        severity = AlertSeverity.WARNING if days_until_expiry <= 3 else AlertSeverity.INFO
        
        title = f"Mandate Expiring in {days_until_expiry} Days"
        message = (
            f"Mandate {mandate.id[:8]}... issued by {mandate.issuer_did} "
            f"will expire on {mandate.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')} "
            f"({days_until_expiry} days from now)."
        )
        
        from app.schemas.alert import AlertCreate
        alert_data = AlertCreate(
            mandate_id=str(mandate.id),
            alert_type=AlertType.MANDATE_EXPIRING,
            title=title,
            message=message,
            severity=severity
        )
        return await self.create_alert(
            tenant_id=str(mandate.tenant_id),
            alert_data=alert_data
        )
    
    async def create_verification_failed_alert(
        self,
        mandate: Mandate,
        verification_reason: str
    ) -> Alert:
        """Create an alert for failed mandate verification."""
        title = "Mandate Verification Failed"
        message = (
            f"Mandate {mandate.id[:8]}... failed verification: {verification_reason}. "
            f"Issuer: {mandate.issuer_did}"
        )
        
        alert_data = AlertCreate(
            mandate_id=str(mandate.id),
            alert_type=AlertType.MANDATE_VERIFICATION_FAILED,
            title=title,
            message=message,
            severity=AlertSeverity.ERROR
        )
        return await self.create_alert(
            tenant_id=str(mandate.tenant_id),
            alert_data=alert_data
        )
    
    async def create_webhook_delivery_failed_alert(
        self,
        tenant_id: str,
        webhook_url: str,
        error_message: str,
        attempts: int
    ) -> Alert:
        """Create an alert for failed webhook delivery."""
        title = "Webhook Delivery Failed"
        message = (
            f"Failed to deliver webhook to {webhook_url} after {attempts} attempts. "
            f"Error: {error_message}"
        )
        
        severity = AlertSeverity.ERROR if attempts >= 3 else AlertSeverity.WARNING
        
        alert_data = AlertCreate(
            mandate_id=None,
            alert_type=AlertType.WEBHOOK_DELIVERY_FAILED,
            title=title,
            message=message,
            severity=severity
        )
        return await self.create_alert(
            tenant_id=tenant_id,
            alert_data=alert_data
        )
    
    async def check_expiring_mandates(self, days_threshold: int = 7) -> int:
        """
        Check for mandates expiring within the specified days and create alerts.
        
        Args:
            days_threshold: Number of days to check ahead
            
        Returns:
            Number of alerts created
        """
        try:
            # Calculate threshold date
            threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
            
            # Find mandates expiring within the threshold
            query = select(Mandate).where(
                and_(
                    Mandate.expires_at <= threshold_date,
                    Mandate.expires_at > datetime.utcnow(),
                    Mandate.deleted_at.is_(None)
                )
            )
            
            result = await self.db.execute(query)
            expiring_mandates = result.scalars().all()
            
            alerts_created = 0
            for mandate in expiring_mandates:
                # Calculate days until expiry
                days_until_expiry = (mandate.expires_at - datetime.utcnow()).days
                
                # Check if alert already exists for this mandate and expiry period
                existing_alert_query = select(Alert).where(
                    and_(
                        Alert.mandate_id == mandate.id,
                        Alert.alert_type == AlertType.MANDATE_EXPIRING,
                        Alert.is_resolved == False
                    )
                )
                
                existing_alert_result = await self.db.execute(existing_alert_query)
                existing_alert = existing_alert_result.scalar_one_or_none()
                
                if not existing_alert:
                    # Create new alert
                    await self.create_mandate_expiring_alert(mandate, days_until_expiry)
                    alerts_created += 1
                    logger.info(f"Created expiry alert for mandate {mandate.id} ({days_until_expiry} days)")
            
            return alerts_created
            
        except Exception as e:
            logger.error(f"Error checking expiring mandates: {str(e)}")
            return 0
    
    async def get_alerts(
        self,
        tenant_id: str,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        is_read: Optional[bool] = None,
        is_resolved: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get alerts with optional filtering.
        
        Args:
            tenant_id: Tenant ID
            alert_type: Filter by alert type
            severity: Filter by severity
            is_read: Filter by read status
            is_resolved: Filter by resolved status
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            Dictionary with alerts and pagination info
        """
        # Validate pagination parameters
        if limit <= 0:
            raise ValueError("Limit must be positive")
        if offset < 0:
            raise ValueError("Offset must be non-negative")
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")
        query = select(Alert).where(Alert.tenant_id == tenant_id)
        
        # Apply filters
        conditions = []
        
        if alert_type:
            conditions.append(Alert.alert_type == alert_type)
        
        if severity:
            conditions.append(Alert.severity == severity)
        
        if is_read is not None:
            conditions.append(Alert.is_read == is_read)
        
        if is_resolved is not None:
            conditions.append(Alert.is_resolved == is_resolved)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(Alert.id).where(Alert.tenant_id == tenant_id)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())
        
        # Apply pagination
        query = query.order_by(Alert.created_at.desc())
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        alerts = result.scalars().all()
        
        return {
            "alerts": alerts,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    async def get_alert_by_id(self, alert_id: str, tenant_id: str) -> Optional[Alert]:
        """Get an alert by ID."""
        query = select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.tenant_id == tenant_id
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_alert(self, alert_id: str, tenant_id: str, update_data) -> Optional[Alert]:
        """Update an alert."""
        alert = await self.get_alert_by_id(alert_id, tenant_id)
        
        if not alert:
            return None
        
        # Update fields if provided
        if hasattr(update_data, 'is_read') and update_data.is_read is not None:
            alert.is_read = update_data.is_read
        
        if hasattr(update_data, 'is_resolved') and update_data.is_resolved is not None:
            alert.is_resolved = update_data.is_resolved
            if update_data.is_resolved:
                alert.resolved_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(alert)
        return alert
    
    async def mark_alert_as_read(self, alert_id: str, tenant_id: str) -> Optional[Alert]:
        """Mark an alert as read."""
        alert = await self.get_alert_by_id(alert_id, tenant_id)
        
        if alert:
            alert.is_read = True
            await self.db.commit()
            await self.db.refresh(alert)
            return alert
        
        return None
    
    async def resolve_alert(self, alert_id: str, tenant_id: str) -> Optional[Alert]:
        """Resolve an alert."""
        alert = await self.get_alert_by_id(alert_id, tenant_id)
        
        if alert:
            alert.is_resolved = True
            alert.resolved_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(alert)
            return alert
        
        return None
    
    async def cleanup_resolved_alerts(self, days_old: int = 30) -> int:
        """
        Clean up resolved alerts older than specified days.
        
        Args:
            days_old: Number of days old alerts to clean up
            
        Returns:
            Number of alerts cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            query = select(Alert).where(
                and_(
                    Alert.is_resolved == True,
                    Alert.resolved_at <= cutoff_date
                )
            )
            
            result = await self.db.execute(query)
            old_alerts = result.scalars().all()
            
            count = 0
            for alert in old_alerts:
                await self.db.delete(alert)
                count += 1
            
            await self.db.commit()
            logger.info(f"Cleaned up {count} resolved alerts older than {days_old} days")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up resolved alerts: {str(e)}")
            return 0
    
    async def cleanup_old_resolved_alerts(self, days_threshold: int = 30) -> int:
        """Clean up old resolved alerts (alias for cleanup_resolved_alerts)."""
        return await self.cleanup_resolved_alerts(days_threshold)


