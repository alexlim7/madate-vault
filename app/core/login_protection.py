"""
Login protection middleware for Mandate Vault.
Implements failed login tracking and account lockout.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List
import asyncio


class LoginProtection:
    """
    Protects against brute force login attempts.
    
    Features:
    - Tracks failed login attempts per email/IP
    - Implements account lockout after threshold
    - Automatic cleanup of old attempts
    """
    
    def __init__(
        self,
        max_attempts: int = 5,
        lockout_duration_minutes: int = 15,
        tracking_window_hours: int = 1
    ):
        """
        Initialize login protection.
        
        Args:
            max_attempts: Maximum failed attempts before lockout (default: 5)
            lockout_duration_minutes: Lockout duration in minutes (default: 15)
            tracking_window_hours: How long to track attempts (default: 1 hour)
        """
        self.max_attempts = max_attempts
        self.lockout_duration = timedelta(minutes=lockout_duration_minutes)
        self.tracking_window = timedelta(hours=tracking_window_hours)
        
        # Track failed attempts: {identifier: [timestamp1, timestamp2, ...]}
        self.failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        
        # Track lockouts: {identifier: lockout_start_time}
        self.lockouts: Dict[str, datetime] = {}
    
    def record_failed_login(self, identifier: str) -> None:
        """
        Record a failed login attempt.
        
        Args:
            identifier: Email address or IP address
        """
        now = datetime.utcnow()
        self.failed_attempts[identifier].append(now)
        
        # Clean old attempts
        self._cleanup_old_attempts(identifier)
        
        # Check if should be locked out
        if len(self.failed_attempts[identifier]) >= self.max_attempts:
            self.lockouts[identifier] = now
    
    def is_locked_out(self, identifier: str) -> bool:
        """
        Check if identifier is currently locked out.
        
        Args:
            identifier: Email address or IP address
            
        Returns:
            True if locked out, False otherwise
        """
        if identifier not in self.lockouts:
            return False
        
        lockout_start = self.lockouts[identifier]
        lockout_end = lockout_start + self.lockout_duration
        
        if datetime.utcnow() >= lockout_end:
            # Lockout period has expired
            self._clear_lockout(identifier)
            return False
        
        return True
    
    def get_lockout_remaining_seconds(self, identifier: str) -> int:
        """
        Get remaining lockout time in seconds.
        
        Args:
            identifier: Email address or IP address
            
        Returns:
            Seconds remaining in lockout, or 0 if not locked out
        """
        if not self.is_locked_out(identifier):
            return 0
        
        lockout_start = self.lockouts[identifier]
        lockout_end = lockout_start + self.lockout_duration
        remaining = lockout_end - datetime.utcnow()
        
        return max(0, int(remaining.total_seconds()))
    
    def get_failed_attempts_count(self, identifier: str) -> int:
        """
        Get number of recent failed attempts.
        
        Args:
            identifier: Email address or IP address
            
        Returns:
            Number of failed attempts in tracking window
        """
        self._cleanup_old_attempts(identifier)
        return len(self.failed_attempts[identifier])
    
    def clear_failed_attempts(self, identifier: str) -> None:
        """
        Clear failed attempts (called on successful login).
        
        Args:
            identifier: Email address or IP address
        """
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]
        self._clear_lockout(identifier)
    
    def _cleanup_old_attempts(self, identifier: str) -> None:
        """Remove attempts older than tracking window."""
        if identifier not in self.failed_attempts:
            return
        
        cutoff = datetime.utcnow() - self.tracking_window
        self.failed_attempts[identifier] = [
            timestamp for timestamp in self.failed_attempts[identifier]
            if timestamp > cutoff
        ]
        
        # Remove if empty
        if not self.failed_attempts[identifier]:
            del self.failed_attempts[identifier]
    
    def _clear_lockout(self, identifier: str) -> None:
        """Clear lockout for identifier."""
        if identifier in self.lockouts:
            del self.lockouts[identifier]
    
    async def cleanup_old_data(self) -> None:
        """Periodic cleanup of old data (call from background task)."""
        while True:
            try:
                # Clean up old attempts
                identifiers_to_remove = []
                for identifier in list(self.failed_attempts.keys()):
                    self._cleanup_old_attempts(identifier)
                    if not self.failed_attempts.get(identifier):
                        identifiers_to_remove.append(identifier)
                
                for identifier in identifiers_to_remove:
                    if identifier in self.failed_attempts:
                        del self.failed_attempts[identifier]
                
                # Clean up expired lockouts
                lockouts_to_remove = []
                for identifier, lockout_time in self.lockouts.items():
                    if datetime.utcnow() - lockout_time > self.lockout_duration:
                        lockouts_to_remove.append(identifier)
                
                for identifier in lockouts_to_remove:
                    self._clear_lockout(identifier)
                
            except Exception as e:
                print(f"Login protection cleanup error: {e}")
            
            # Run cleanup every 5 minutes
            await asyncio.sleep(300)


# Global instance
login_protection = LoginProtection(
    max_attempts=5,
    lockout_duration_minutes=15,
    tracking_window_hours=1
)
