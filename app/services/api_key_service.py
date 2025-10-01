"""
API Key Service for managing programmatic access.
"""
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.api_key import APIKey
from app.core.auth import PasswordContext


class APIKeyService:
    """Service for managing API keys."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pwd_context = PasswordContext()
    
    def generate_api_key(self) -> tuple[str, str]:
        """
        Generate a new API key.
        
        Returns:
            Tuple of (api_key, key_prefix)
        """
        # Generate random key (44 characters, URL-safe)
        raw_key = secrets.token_urlsafe(32)
        
        # Add prefix for identification
        prefix = raw_key[:8]
        full_key = f"mvk_{raw_key}"  # Mandate Vault Key
        
        return full_key, prefix
    
    def hash_api_key(self, api_key: str) -> str:
        """
        Hash an API key for storage.
        
        Args:
            api_key: The raw API key
            
        Returns:
            Hashed key
        """
        return self.pwd_context.hash(api_key)
    
    def verify_api_key(self, api_key: str, key_hash: str) -> bool:
        """
        Verify an API key against its hash.
        
        Args:
            api_key: The raw API key
            key_hash: The stored hash
            
        Returns:
            True if valid
        """
        return self.pwd_context.verify(api_key, key_hash)
    
    async def create_api_key(
        self,
        name: str,
        tenant_id: str,
        created_by: str,
        description: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        allowed_ips: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
        rate_limit_per_minute: int = 100,
        rate_limit_per_hour: int = 1000,
        rate_limit_per_day: int = 10000
    ) -> tuple[APIKey, str]:
        """
        Create a new API key.
        
        Args:
            name: Human-readable name
            tenant_id: Tenant ID
            created_by: User ID who created the key
            description: Optional description
            scopes: List of permission scopes
            allowed_ips: List of allowed IP addresses
            expires_in_days: Number of days until expiration
            rate_limit_per_minute: Rate limit per minute
            rate_limit_per_hour: Rate limit per hour
            rate_limit_per_day: Rate limit per day
            
        Returns:
            Tuple of (APIKey object, raw API key)
        """
        # Generate key
        raw_key, prefix = self.generate_api_key()
        key_hash = self.hash_api_key(raw_key)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        # Create API key
        api_key = APIKey(
            name=name,
            description=description,
            key_prefix=prefix,
            key_hash=key_hash,
            tenant_id=tenant_id,
            created_by=created_by,
            scopes=scopes or [],
            allowed_ips=allowed_ips or [],
            expires_at=expires_at,
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_hour=rate_limit_per_hour,
            rate_limit_per_day=rate_limit_per_day,
            is_active=True,
            is_revoked=False
        )
        
        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)
        
        return api_key, raw_key
    
    async def get_api_key_by_prefix(self, key_prefix: str) -> Optional[APIKey]:
        """Get API key by prefix."""
        result = await self.db.execute(
            select(APIKey).where(
                and_(
                    APIKey.key_prefix == key_prefix,
                    APIKey.is_active == True,
                    APIKey.is_revoked == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def validate_api_key(self, raw_key: str, client_ip: str) -> Optional[APIKey]:
        """
        Validate an API key and update usage statistics.
        
        Args:
            raw_key: The raw API key
            client_ip: Client IP address
            
        Returns:
            APIKey object if valid, None otherwise
        """
        # Extract prefix
        if not raw_key.startswith("mvk_"):
            return None
        
        prefix = raw_key[4:12]  # Extract prefix after "mvk_"
        
        # Get API key
        api_key = await self.get_api_key_by_prefix(prefix)
        if not api_key:
            return None
        
        # Verify hash
        if not self.verify_api_key(raw_key, api_key.key_hash):
            return None
        
        # Check if expired
        if api_key.expires_at and datetime.now(timezone.utc) > api_key.expires_at:
            return None
        
        # Check IP whitelist
        if api_key.allowed_ips and client_ip not in api_key.allowed_ips:
            # Check for CIDR ranges
            if not self._is_ip_allowed(client_ip, api_key.allowed_ips):
                return None
        
        # Update usage
        api_key.last_used_at = datetime.now(timezone.utc)
        api_key.last_used_ip = client_ip
        api_key.total_requests += 1
        await self.db.commit()
        
        return api_key
    
    def _is_ip_allowed(self, client_ip: str, allowed_ips: List[str]) -> bool:
        """
        Check if IP is in allowed list (supports CIDR notation).
        
        Args:
            client_ip: Client IP address
            allowed_ips: List of allowed IPs/ranges
            
        Returns:
            True if allowed
        """
        from ipaddress import ip_address, ip_network
        
        try:
            client_ip_obj = ip_address(client_ip)
            
            for allowed in allowed_ips:
                try:
                    # Check if it's a network range
                    if '/' in allowed:
                        network = ip_network(allowed, strict=False)
                        if client_ip_obj in network:
                            return True
                    # Check exact IP match
                    elif client_ip == allowed:
                        return True
                except ValueError:
                    continue
            
            return False
        except ValueError:
            return False
    
    async def revoke_api_key(
        self,
        key_id: str,
        revoked_by: str,
        reason: Optional[str] = None
    ) -> Optional[APIKey]:
        """
        Revoke an API key.
        
        Args:
            key_id: API key ID
            revoked_by: User ID who revoked the key
            reason: Reason for revocation
            
        Returns:
            Revoked APIKey object
        """
        result = await self.db.execute(
            select(APIKey).where(APIKey.id == key_id)
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            return None
        
        api_key.is_revoked = True
        api_key.is_active = False
        api_key.revoked_at = datetime.now(timezone.utc)
        api_key.revoked_by = revoked_by
        api_key.revoke_reason = reason
        
        await self.db.commit()
        await self.db.refresh(api_key)
        
        return api_key
    
    async def list_api_keys(
        self,
        tenant_id: str,
        include_revoked: bool = False
    ) -> List[APIKey]:
        """
        List API keys for a tenant.
        
        Args:
            tenant_id: Tenant ID
            include_revoked: Include revoked keys
            
        Returns:
            List of APIKey objects
        """
        query = select(APIKey).where(APIKey.tenant_id == tenant_id)
        
        if not include_revoked:
            query = query.where(APIKey.is_revoked == False)
        
        result = await self.db.execute(query.order_by(APIKey.created_at.desc()))
        return list(result.scalars().all())
    
    async def rotate_api_key(
        self,
        key_id: str,
        rotated_by: str
    ) -> tuple[APIKey, str]:
        """
        Rotate an API key (create new, revoke old).
        
        Args:
            key_id: Old API key ID
            rotated_by: User ID performing rotation
            
        Returns:
            Tuple of (new APIKey, raw key)
        """
        # Get old key
        result = await self.db.execute(
            select(APIKey).where(APIKey.id == key_id)
        )
        old_key = result.scalar_one_or_none()
        
        if not old_key:
            raise ValueError(f"API key {key_id} not found")
        
        # Create new key with same settings
        new_key, raw_key = await self.create_api_key(
            name=f"{old_key.name} (rotated)",
            tenant_id=old_key.tenant_id,
            created_by=rotated_by,
            description=f"Rotated from {old_key.id}",
            scopes=old_key.scopes,
            allowed_ips=old_key.allowed_ips,
            expires_in_days=365,  # 1 year
            rate_limit_per_minute=old_key.rate_limit_per_minute,
            rate_limit_per_hour=old_key.rate_limit_per_hour,
            rate_limit_per_day=old_key.rate_limit_per_day
        )
        
        # Revoke old key
        await self.revoke_api_key(
            key_id=old_key.id,
            revoked_by=rotated_by,
            reason="Rotated"
        )
        
        return new_key, raw_key

