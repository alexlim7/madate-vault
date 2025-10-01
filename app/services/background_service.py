"""
Background service for running periodic tasks.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.services.webhook_service import WebhookService
from app.services.alert_service import AlertService
from app.services.mandate_service import MandateService

logger = logging.getLogger(__name__)


class BackgroundTaskService:
    """Service for running background tasks."""
    
    def __init__(self):
        self.running = False
        self.tasks = []
    
    async def start(self) -> None:
        """Start background tasks."""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting background tasks...")
        
        # Start webhook retry task
        self.tasks.append(asyncio.create_task(self._webhook_retry_loop()))
        
        # Start expiry check task
        self.tasks.append(asyncio.create_task(self._expiry_check_loop()))
        
        # Start alert cleanup task
        self.tasks.append(asyncio.create_task(self._alert_cleanup_loop()))
        
        logger.info("Background tasks started")
    
    async def stop(self) -> None:
        """Stop background tasks."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping background tasks...")
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.tasks.clear()
        logger.info("Background tasks stopped")
    
    async def _webhook_retry_loop(self) -> None:
        """Loop for retrying failed webhook deliveries."""
        while self.running:
            try:
                async with AsyncSessionLocal() as db:
                    webhook_service = WebhookService(db)
                    retry_count = await webhook_service.retry_failed_deliveries()
                    
                    if retry_count > 0:
                        logger.info(f"Retried {retry_count} failed webhook deliveries")
                    
                    await webhook_service.close()
                
                # Wait 5 minutes before next retry
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in webhook retry loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _expiry_check_loop(self) -> None:
        """Loop for checking expiring mandates and creating alerts."""
        while self.running:
            try:
                async with AsyncSessionLocal() as db:
                    alert_service = AlertService(db)
                    alerts_created = await alert_service.check_expiring_mandates(days_threshold=7)
                    
                    if alerts_created > 0:
                        logger.info(f"Created {alerts_created} alerts for expiring mandates")
                
                # Check every hour
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in expiry check loop: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _alert_cleanup_loop(self) -> None:
        """Loop for cleaning up old resolved alerts."""
        while self.running:
            try:
                async with AsyncSessionLocal() as db:
                    alert_service = AlertService(db)
                    cleaned_count = await alert_service.cleanup_resolved_alerts(days_old=30)
                    
                    if cleaned_count > 0:
                        logger.info(f"Cleaned up {cleaned_count} resolved alerts")
                
                # Run cleanup daily
                await asyncio.sleep(86400)  # 24 hours
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert cleanup loop: {str(e)}")
                await asyncio.sleep(3600)  # Wait 1 hour before retrying
    
    async def run_expiry_check_now(self) -> int:
        """Manually run expiry check and return number of alerts created."""
        try:
            async with AsyncSessionLocal() as db:
                alert_service = AlertService(db)
                return await alert_service.check_expiring_mandates(days_threshold=7)
        except Exception as e:
            logger.error(f"Error running manual expiry check: {str(e)}")
            return 0
    
    async def retry_webhooks_now(self) -> int:
        """Manually retry failed webhooks and return number of retries."""
        try:
            async with AsyncSessionLocal() as db:
                webhook_service = WebhookService(db)
                retry_count = await webhook_service.retry_failed_deliveries()
                await webhook_service.close()
                return retry_count
        except Exception as e:
            logger.error(f"Error running manual webhook retry: {str(e)}")
            return 0


# Global background service instance
background_service = BackgroundTaskService()


