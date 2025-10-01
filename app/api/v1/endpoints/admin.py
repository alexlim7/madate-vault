"""
Admin API endpoints for system maintenance.
"""
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.mandate_service import MandateService
from app.services.verification_service import verification_service

router = APIRouter()


@router.post("/cleanup-retention")
async def cleanup_expired_retention(
    db: AsyncSession = Depends(get_db)
):
    """
    Clean up mandates that have exceeded their retention period.
    """
    try:
        mandate_service = MandateService(db)
        
        # Clean up expired retention mandates
        count = await mandate_service.cleanup_expired_retention()
        
        return {
            "message": f"Successfully cleaned up {count} mandates",
            "cleaned_count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/truststore-status")
async def get_truststore_status():
    """
    Get truststore status including cached issuers and refresh times.
    """
    try:
        status = await verification_service.get_truststore_status()
        return status
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
