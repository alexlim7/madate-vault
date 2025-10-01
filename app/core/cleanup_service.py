"""
Token cleanup service for Mandate Vault.
Automatically cleans up expired tokens and sessions.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

logger = logging.getLogger(__name__)


class TokenCleanupService:
    """
    Automated cleanup service for expired tokens.
    
    Features:
    - Removes expired refresh tokens from blacklist
    - Cleans up old session data
    - Runs periodically in background
    """
    
    def __init__(
        self,
        cleanup_interval_seconds: int = 3600,  # 1 hour
        token_retention_days: int = 7
    ):
        """
        Initialize token cleanup service.
        
        Args:
            cleanup_interval_seconds: How often to run cleanup (default: 1 hour)
            token_retention_days: How long to keep expired tokens (default: 7 days)
        """
        self.cleanup_interval = cleanup_interval_seconds
        self.retention_days = token_retention_days
        self.is_running = False
    
    async def cleanup_expired_tokens(self, db: AsyncSession) -> dict:
        """
        Remove expired tokens from database.
        
        Args:
            db: Database session
            
        Returns:
            Cleanup statistics
        """
        stats = {
            "tokens_removed": 0,
            "sessions_removed": 0,
            "cleanup_time": datetime.utcnow().isoformat()
        }
        
        try:
            # Calculate cutoff date
            cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
            
            # In a real implementation, you would:
            # 1. Delete expired refresh tokens from blacklist
            # 2. Delete old session data
            # 3. Clean up any other temporary security data
            
            # Example (uncomment when you have token_blacklist table):
            # result = await db.execute(
            #     delete(TokenBlacklist).where(TokenBlacklist.created_at < cutoff)
            # )
            # stats["tokens_removed"] = result.rowcount
            
            # Example (uncomment when you have sessions table):
            # result = await db.execute(
            #     delete(Session).where(Session.expires_at < datetime.utcnow())
            # )
            # stats["sessions_removed"] = result.rowcount
            
            await db.commit()
            
            logger.info(f"Token cleanup completed: {stats}")
            
        except Exception as e:
            logger.error(f"Token cleanup failed: {e}")
            await db.rollback()
        
        return stats
    
    async def run_periodic_cleanup(self, db_session_factory) -> None:
        """
        Run cleanup periodically in background.
        
        Args:
            db_session_factory: Function to create database sessions
        """
        self.is_running = True
        logger.info(f"Token cleanup service started (interval: {self.cleanup_interval}s)")
        
        while self.is_running:
            try:
                # Create database session
                async with db_session_factory() as db:
                    await self.cleanup_expired_tokens(db)
                
            except Exception as e:
                logger.error(f"Periodic cleanup error: {e}")
            
            # Wait until next cleanup
            await asyncio.sleep(self.cleanup_interval)
    
    def stop(self) -> None:
        """Stop the cleanup service."""
        self.is_running = False
        logger.info("Token cleanup service stopped")


class SessionCleanupService:
    """
    Cleanup service for user sessions and login protection data.
    """
    
    def __init__(self, cleanup_interval_seconds: int = 300):  # 5 minutes
        """
        Initialize session cleanup service.
        
        Args:
            cleanup_interval_seconds: How often to run cleanup (default: 5 minutes)
        """
        self.cleanup_interval = cleanup_interval_seconds
        self.is_running = False
    
    async def cleanup_login_protection_data(self) -> dict:
        """
        Clean up old login protection data.
        
        Returns:
            Cleanup statistics
        """
        from app.core.login_protection import login_protection
        
        stats = {
            "attempts_cleaned": 0,
            "lockouts_cleaned": 0,
            "cleanup_time": datetime.utcnow().isoformat()
        }
        
        try:
            # Count before cleanup
            attempts_before = len(login_protection.failed_attempts)
            lockouts_before = len(login_protection.lockouts)
            
            # Clean up old attempts
            identifiers_to_remove = []
            for identifier in list(login_protection.failed_attempts.keys()):
                login_protection._cleanup_old_attempts(identifier)
                if not login_protection.failed_attempts.get(identifier):
                    identifiers_to_remove.append(identifier)
            
            for identifier in identifiers_to_remove:
                if identifier in login_protection.failed_attempts:
                    del login_protection.failed_attempts[identifier]
            
            # Clean up expired lockouts
            lockouts_to_remove = []
            for identifier, lockout_time in login_protection.lockouts.items():
                if datetime.utcnow() - lockout_time > login_protection.lockout_duration:
                    lockouts_to_remove.append(identifier)
            
            for identifier in lockouts_to_remove:
                login_protection._clear_lockout(identifier)
            
            # Calculate stats
            stats["attempts_cleaned"] = attempts_before - len(login_protection.failed_attempts)
            stats["lockouts_cleaned"] = lockouts_before - len(login_protection.lockouts)
            
            if stats["attempts_cleaned"] > 0 or stats["lockouts_cleaned"] > 0:
                logger.info(f"Session cleanup completed: {stats}")
            
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
        
        return stats
    
    async def run_periodic_cleanup(self) -> None:
        """Run session cleanup periodically in background."""
        self.is_running = True
        logger.info(f"Session cleanup service started (interval: {self.cleanup_interval}s)")
        
        while self.is_running:
            try:
                await self.cleanup_login_protection_data()
            except Exception as e:
                logger.error(f"Periodic session cleanup error: {e}")
            
            await asyncio.sleep(self.cleanup_interval)
    
    def stop(self) -> None:
        """Stop the cleanup service."""
        self.is_running = False
        logger.info("Session cleanup service stopped")


# Global instances
token_cleanup_service = TokenCleanupService(
    cleanup_interval_seconds=3600,  # 1 hour
    token_retention_days=7
)

session_cleanup_service = SessionCleanupService(
    cleanup_interval_seconds=300  # 5 minutes
)
