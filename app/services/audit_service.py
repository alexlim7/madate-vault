"""
Audit service for logging events.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import uuid

from app.models.audit import AuditLog
from app.schemas.audit import AuditLogSearch


class AuditService:
    """Service class for audit operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_event(self, event_type: str, details: Optional[Dict[str, Any]] = None,
                       mandate_id: Optional[uuid.UUID] = None) -> AuditLog:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (CREATE, READ, UPDATE, DELETE, SOFT_DELETE, RESTORE, VERIFY)
            details: Optional event details (JSONB)
            mandate_id: Optional mandate ID this event relates to
            
        Returns:
            Created audit log entry
        """
        audit_log = AuditLog(
            mandate_id=mandate_id,
            event_type=event_type,
            details=details
        )
        
        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)
        
        return audit_log
    
    async def create_audit_log(self, audit_data) -> AuditLog:
        """
        Create an audit log entry.
        
        Args:
            audit_data: Dictionary with audit log data
            
        Returns:
            Created audit log entry
        """
        # Validate event_type
        valid_event_types = ["CREATE", "READ", "UPDATE", "DELETE", "SOFT_DELETE", "RESTORE", "VERIFY"]
        if audit_data["event_type"] not in valid_event_types:
            raise ValueError(f"Invalid event type: {audit_data['event_type']}")
        
        audit_log = AuditLog(
            mandate_id=uuid.UUID(audit_data["mandate_id"]) if audit_data.get("mandate_id") else None,
            event_type=audit_data["event_type"],
            details=audit_data.get("details")
        )
        
        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)
        
        return audit_log
    
    async def get_audit_log_by_id(self, audit_log_id: str) -> Optional[AuditLog]:
        """Get an audit log by ID."""
        query = select(AuditLog).where(AuditLog.id == uuid.UUID(audit_log_id))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def log_mandate_event(self, mandate_id: str, event_type: str, details: Optional[Dict[str, Any]] = None) -> AuditLog:
        """Log a mandate-specific event."""
        return await self.log_event(
            event_type=event_type,
            details=details,
            mandate_id=uuid.UUID(mandate_id)
        )
    
    async def search_audit_logs(self, mandate_id: Optional[str] = None, 
                               event_type: Optional[str] = None,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        Search audit logs with filters.
        
        Args:
            mandate_id: Optional mandate ID to filter by
            event_type: Optional event type to filter by
            start_date: Optional start date to filter by
            end_date: Optional end date to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            Dictionary with audit logs and pagination info
        """
        query = select(AuditLog)
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date must be before end date")
        
        # Apply filters
        conditions = []
        
        if mandate_id:
            conditions.append(AuditLog.mandate_id == uuid.UUID(mandate_id))
        
        if event_type:
            conditions.append(AuditLog.event_type == event_type)
        
        if start_date:
            conditions.append(AuditLog.timestamp >= start_date)
        
        if end_date:
            conditions.append(AuditLog.timestamp <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(AuditLog.id)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        query = query.order_by(AuditLog.timestamp.desc())
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return {
            "audit_logs": logs,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    async def get_audit_logs_by_mandate(self, mandate_id: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        Get audit logs for a specific mandate.
        
        Args:
            mandate_id: Mandate UUID as string
            limit: Maximum number of logs to return
            offset: Number of logs to skip
            
        Returns:
            Dictionary with audit logs and pagination info
        """
        # Validate parameters
        if limit <= 0:
            raise ValueError("Limit must be positive")
        if offset < 0:
            raise ValueError("Offset must be non-negative")
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")
        
        # Validate UUID format
        try:
            mandate_uuid = uuid.UUID(mandate_id)
        except ValueError:
            raise ValueError("Invalid UUID format")
        
        query = select(AuditLog).where(AuditLog.mandate_id == mandate_uuid)
        
        # Get total count
        count_query = select(AuditLog.id).where(AuditLog.mandate_id == mandate_uuid)
        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())
        
        # Apply pagination
        query = query.order_by(AuditLog.timestamp.desc())
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return {
            "logs": logs,
            "total": total,
            "limit": limit,
            "offset": offset
        }
