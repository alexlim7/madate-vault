"""
JWK Truststore service for managing issuer public keys.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from urllib.parse import urljoin
import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.backends import default_backend
import jwt
from jwt.algorithms import RSAAlgorithm, ECAlgorithm

from app.core.config import settings

logger = logging.getLogger(__name__)


class TruststoreService:
    """Service for managing JWK truststore with automatic refresh."""
    
    def __init__(self):
        self._truststore: Dict[str, Dict] = {}
        self._last_refresh: Dict[str, datetime] = {}
        self._refresh_interval = timedelta(hours=1)
        self._client = httpx.AsyncClient(timeout=30.0)
        self._lock = asyncio.Lock()
    
    async def get_issuer_keys(self, issuer_did: str) -> Optional[Dict]:
        """
        Get JWK keys for an issuer, refreshing if necessary.
        
        Args:
            issuer_did: The issuer DID
            
        Returns:
            Dictionary containing JWK keys or None if not found
        """
        async with self._lock:
            # Check if we need to refresh
            if self._should_refresh(issuer_did):
                await self._refresh_issuer_keys(issuer_did)
            
            return self._truststore.get(issuer_did)
    
    def _should_refresh(self, issuer_did: str) -> bool:
        """Check if keys need to be refreshed."""
        if issuer_did not in self._truststore:
            return True
        
        last_refresh = self._last_refresh.get(issuer_did)
        if not last_refresh:
            return True
        
        return datetime.utcnow() - last_refresh > self._refresh_interval
    
    async def _refresh_issuer_keys(self, issuer_did: str) -> None:
        """
        Refresh JWK keys for an issuer.
        
        Args:
            issuer_did: The issuer DID
        """
        try:
            # Extract JWK endpoint from DID
            jwk_endpoint = self._extract_jwk_endpoint(issuer_did)
            if not jwk_endpoint:
                logger.warning(f"No JWK endpoint found for issuer: {issuer_did}")
                return
            
            # Fetch JWK set
            response = await self._client.get(jwk_endpoint)
            response.raise_for_status()
            
            jwk_set = response.json()
            
            # Validate and store JWK set
            if self._validate_jwk_set(jwk_set):
                self._truststore[issuer_did] = jwk_set
                self._last_refresh[issuer_did] = datetime.utcnow()
                logger.info(f"Successfully refreshed JWK keys for issuer: {issuer_did}")
            else:
                logger.error(f"Invalid JWK set received for issuer: {issuer_did}")
                
        except Exception as e:
            logger.error(f"Failed to refresh JWK keys for issuer {issuer_did}: {str(e)}")
            # If this is the first time fetching, remove from truststore
            if issuer_did in self._truststore:
                del self._truststore[issuer_did]
    
    def _extract_jwk_endpoint(self, issuer_did: str) -> Optional[str]:
        """
        Extract JWK endpoint from DID.
        This is a simplified implementation - in production you'd use a proper DID resolver.
        
        Args:
            issuer_did: The issuer DID
            
        Returns:
            JWK endpoint URL or None
        """
        # For demo purposes, assume JWK endpoint follows pattern
        # In production, this would resolve the DID document
        if issuer_did.startswith("did:example:"):
            # Extract the identifier part
            identifier = issuer_did.replace("did:example:", "")
            return f"https://jwks.example.com/{identifier}/.well-known/jwks.json"
        elif issuer_did.startswith("did:web:"):
            # Web DIDs use https://domain/path/.well-known/did.json
            domain_path = issuer_did.replace("did:web:", "")
            return f"https://{domain_path}/.well-known/jwks.json"
        else:
            # For other DID methods, you'd implement proper DID resolution
            logger.warning(f"Unsupported DID method for: {issuer_did}")
            return None
    
    def _validate_jwk_set(self, jwk_set: Dict) -> bool:
        """
        Validate JWK set structure.
        
        Args:
            jwk_set: JWK set dictionary
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(jwk_set, dict):
                return False
            
            if "keys" not in jwk_set:
                return False
            
            keys = jwk_set["keys"]
            if not isinstance(keys, list) or len(keys) == 0:
                return False
            
            # Validate each key
            for key in keys:
                if not self._validate_jwk(key):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_jwk(self, jwk: Dict) -> bool:
        """
        Validate individual JWK.
        
        Args:
            jwk: JWK dictionary
            
        Returns:
            True if valid, False otherwise
        """
        try:
            required_fields = ["kty", "kid"]
            for field in required_fields:
                if field not in jwk:
                    return False
            
            # Validate key type
            kty = jwk["kty"]
            if kty not in ["RSA", "EC", "oct"]:
                return False
            
            # "use" and "alg" are optional in modern JWK specs
            # If present, validate them
            if "use" in jwk:
                use = jwk["use"]
                if use not in ["sig", "enc"]:
                    return False
            
            if "alg" in jwk:
                alg = jwk["alg"]
                if kty == "RSA" and alg not in ["RS256", "RS384", "RS512", "PS256", "PS384", "PS512"]:
                    return False
                elif kty == "EC" and alg not in ["ES256", "ES384", "ES512", "ES256K"]:
                    return False
                elif kty == "oct" and alg not in ["HS256", "HS384", "HS512"]:
                    return False
            
            # Validate RSA-specific fields
            if kty == "RSA":
                if "n" not in jwk or "e" not in jwk:
                    return False
            
            # Validate EC-specific fields  
            elif kty == "EC":
                if "crv" not in jwk or "x" not in jwk or "y" not in jwk:
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def verify_signature(self, token: str, issuer_did: str) -> bool:
        """
        Verify JWT signature using issuer's JWK keys.
        
        Args:
            token: JWT token
            issuer_did: Issuer DID
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Get issuer keys
            jwk_set = await self.get_issuer_keys(issuer_did)
            if not jwk_set:
                return False
            
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not kid:
                return False
            
            # Find matching key
            matching_key = None
            for key in jwk_set["keys"]:
                if key.get("kid") == kid:
                    matching_key = key
                    break
            
            if not matching_key:
                return False
            
            # Verify signature
            try:
                # Convert JWK to public key
                public_key = self._jwk_to_public_key(matching_key)
                
                # Verify token
                jwt.decode(
                    token,
                    public_key,
                    algorithms=[matching_key["alg"]],
                    options={"verify_signature": True}
                )
                
                return True
                
            except jwt.InvalidSignatureError:
                return False
            except jwt.ExpiredSignatureError:
                # Signature is valid but token is expired
                return True
            except Exception:
                return False
                
        except Exception as e:
            logger.error(f"Error verifying signature for issuer {issuer_did}: {str(e)}")
            return False
    
    def _jwk_to_public_key(self, jwk: Dict):
        """
        Convert JWK to cryptography public key.
        
        Args:
            jwk: JWK dictionary
            
        Returns:
            Public key object
        """
        if jwk["kty"] == "RSA":
            return RSAAlgorithm.from_jwk(jwk)
        elif jwk["kty"] == "EC":
            return ECAlgorithm.from_jwk(jwk)
        else:
            raise ValueError(f"Unsupported key type: {jwk['kty']}")
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def register_issuer(self, issuer_did: str, jwk_set: Dict) -> bool:
        """
        Manually register an issuer with their JWK set.
        Useful for testing or private/enterprise issuers.
        
        Args:
            issuer_did: The issuer DID
            jwk_set: The JWK set dictionary
            
        Returns:
            True if registration successful
        """
        async with self._lock:
            if self._validate_jwk_set(jwk_set):
                self._truststore[issuer_did] = jwk_set
                self._last_refresh[issuer_did] = datetime.utcnow()
                logger.info(f"Manually registered issuer: {issuer_did}")
                return True
            else:
                logger.error(f"Invalid JWK set for issuer: {issuer_did}")
                return False
    
    async def register_issuer_from_endpoint(self, issuer_did: str, jwk_endpoint: str) -> bool:
        """
        Register an issuer by fetching their JWK set from a custom endpoint.
        
        Args:
            issuer_did: The issuer DID
            jwk_endpoint: Custom JWK endpoint URL
            
        Returns:
            True if registration successful
        """
        try:
            response = await self._client.get(jwk_endpoint)
            response.raise_for_status()
            
            jwk_set = response.json()
            return await self.register_issuer(issuer_did, jwk_set)
            
        except Exception as e:
            logger.error(f"Failed to fetch JWK set from {jwk_endpoint}: {str(e)}")
            return False
    
    def remove_issuer(self, issuer_did: str) -> bool:
        """
        Remove an issuer from the truststore.
        
        Args:
            issuer_did: The issuer DID
            
        Returns:
            True if issuer was removed
        """
        if issuer_did in self._truststore:
            del self._truststore[issuer_did]
            if issuer_did in self._last_refresh:
                del self._last_refresh[issuer_did]
            logger.info(f"Removed issuer from truststore: {issuer_did}")
            return True
        return False
    
    def is_issuer_trusted(self, issuer_did: str) -> bool:
        """
        Check if an issuer is in the truststore.
        
        Args:
            issuer_did: The issuer DID
            
        Returns:
            True if issuer is trusted
        """
        return issuer_did in self._truststore
    
    def list_trusted_issuers(self) -> List[str]:
        """
        Get list of all trusted issuer DIDs.
        
        Returns:
            List of issuer DIDs
        """
        return list(self._truststore.keys())
    
    def get_truststore_status(self) -> Dict:
        """
        Get status of the truststore.
        
        Returns:
            Dictionary with truststore status
        """
        return {
            "issuers": list(self._truststore.keys()),
            "issuer_count": len(self._truststore),
            "last_refresh": {
                issuer: refresh.isoformat() if refresh else None
                for issuer, refresh in self._last_refresh.items()
            },
            "refresh_interval_hours": self._refresh_interval.total_seconds() / 3600
        }


# Global truststore instance
truststore_service = TruststoreService()


