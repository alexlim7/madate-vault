"""
Background worker for webhook delivery and retries.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.core.database import AsyncSessionLocal
from app.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)


class WebhookWorker:
    """Background worker for processing webhook deliveries and retries."""
    
    def __init__(self, retry_interval: int = 60):
        """
        Initialize webhook worker.
        
        Args:
            retry_interval: Interval in seconds to check for failed deliveries (default: 60s)
        """
        self.retry_interval = retry_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the webhook worker."""
        if self._running:
            logger.warning("Webhook worker already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(f"Webhook worker started (retry interval: {self.retry_interval}s)")
    
    def stop(self):
        """Stop the webhook worker."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Webhook worker stopped")
    
    async def _run(self):
        """Main worker loop."""
        logger.info("Webhook worker running...")
        
        while self._running:
            try:
                await self._process_retries()
            except asyncio.CancelledError:
                logger.info("Webhook worker task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in webhook worker: {str(e)}", exc_info=True)
            
            # Wait before next iteration
            try:
                await asyncio.sleep(self.retry_interval)
            except asyncio.CancelledError:
                break
    
    async def _process_retries(self):
        """Process webhook delivery retries."""
        try:
            async with AsyncSessionLocal() as db:
                webhook_service = WebhookService(db)
                
                # Retry failed deliveries
                retry_count = await webhook_service.retry_failed_deliveries()
                
                if retry_count > 0:
                    logger.info(f"Processed {retry_count} webhook delivery retries")
                
                await webhook_service.close()
                
        except Exception as e:
            logger.error(f"Error processing webhook retries: {str(e)}")


# Global webhook worker instance
webhook_worker = WebhookWorker(retry_interval=60)  # Check every minute

