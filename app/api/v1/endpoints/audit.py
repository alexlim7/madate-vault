"""
Audit API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.audit import AuditLogResponse, AuditLogSearch, AuditLogSearchResponse
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/{mandate_id}", response_model=AuditLogSearchResponse)
async def get_audit_logs_by_mandate(
    mandate_id: str,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> AuditLogSearchResponse:
    """
    Return all audit logs for a mandate.
    """
    try:
        audit_service = AuditService(db)
        
        # Get audit logs
        result = await audit_service.get_audit_logs_by_mandate(
            mandate_id=mandate_id,
            limit=limit,
            offset=offset
        )
        
        # Convert logs to response format
        log_responses = [AuditLogResponse.model_validate(log) for log in result["logs"]]
        
        return AuditLogSearchResponse(
            logs=log_responses,
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/", response_model=AuditLogSearchResponse)
async def search_audit_logs(
    mandate_id: Optional[str] = None,
    event_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> AuditLogSearchResponse:
    """
    Search audit logs with filters.
    """
    try:
        from datetime import datetime
        from app.schemas.audit import AuditEventType
        
        audit_service = AuditService(db)
        
        # Parse timestamps if provided
        start_date_dt = None
        end_date_dt = None
        
        if start_date:
            try:
                start_date_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use ISO format (e.g., 2024-01-01T00:00:00Z)"
                )
        
        if end_date:
            try:
                end_date_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use ISO format (e.g., 2024-12-31T23:59:59Z)"
                )
        
        # Create search parameters
        search_params = AuditLogSearch(
            mandate_id=mandate_id,
            event_type=AuditEventType(event_type) if event_type else None,
            start_date=start_date_dt,
            end_date=end_date_dt,
            limit=limit,
            offset=offset
        )
        
        # Search audit logs
        result = await audit_service.search_audit_logs(search_params)
        
        # Convert logs to response format
        log_responses = [AuditLogResponse.model_validate(log) for log in result["logs"]]
        
        return AuditLogSearchResponse(
            logs=log_responses,
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
