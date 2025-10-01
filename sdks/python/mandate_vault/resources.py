"""
Resource classes for API endpoints.
"""
from typing import Optional, Dict, Any, List


class Resource:
    """Base resource class."""
    
    def __init__(self, client):
        self.client = client


class Mandates(Resource):
    """Mandate resource."""
    
    def create(
        self,
        vc_jwt: str,
        tenant_id: str,
        retention_days: int = 90
    ) -> Dict[str, Any]:
        """
        Create a new mandate.
        
        Args:
            vc_jwt: JWT-VC token
            tenant_id: Your tenant ID
            retention_days: Retention period
        
        Returns:
            Created mandate object
        
        Example:
            >>> mandate = client.mandates.create(
            ...     vc_jwt='eyJhbGc...',
            ...     tenant_id='tenant-123'
            ... )
        """
        return self.client.post('/api/v1/mandates', json={
            'vc_jwt': vc_jwt,
            'tenant_id': tenant_id,
            'retention_days': retention_days
        })
    
    def get(self, mandate_id: str) -> Dict[str, Any]:
        """
        Get mandate by ID.
        
        Args:
            mandate_id: Mandate ID
        
        Returns:
            Mandate object
        """
        return self.client.get(f'/api/v1/mandates/{mandate_id}')
    
    def search(
        self,
        tenant_id: str,
        issuer_did: Optional[str] = None,
        subject_did: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search mandates.
        
        Args:
            tenant_id: Your tenant ID
            issuer_did: Filter by issuer
            subject_did: Filter by subject
            status: Filter by status
            limit: Max results
            offset: Pagination offset
        
        Returns:
            Search results with mandates list
        """
        params = {
            'tenant_id': tenant_id,
            'limit': limit,
            'offset': offset
        }
        
        if issuer_did:
            params['issuer_did'] = issuer_did
        if subject_did:
            params['subject_did'] = subject_did
        if status:
            params['status'] = status
        
        return self.client.post('/api/v1/mandates/search', json=params)
    
    def revoke(self, mandate_id: str) -> Dict[str, Any]:
        """
        Revoke a mandate.
        
        Args:
            mandate_id: Mandate ID
        
        Returns:
            Revoked mandate object
        """
        return self.client.delete(f'/api/v1/mandates/{mandate_id}')


class Webhooks(Resource):
    """Webhook resource."""
    
    def create(
        self,
        name: str,
        url: str,
        events: List[str],
        secret: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Create a webhook.
        
        Args:
            name: Webhook name
            url: Webhook URL
            events: List of events to subscribe to
            secret: Webhook secret for signature verification
            tenant_id: Your tenant ID
        
        Returns:
            Created webhook object
        """
        return self.client.post('/api/v1/webhooks', json={
            'name': name,
            'url': url,
            'events': events,
            'secret': secret,
            'tenant_id': tenant_id
        })
    
    def list(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        List webhooks for tenant.
        
        Args:
            tenant_id: Your tenant ID
        
        Returns:
            List of webhooks
        """
        return self.client.get(f'/api/v1/webhooks?tenant_id={tenant_id}')


class Audit(Resource):
    """Audit log resource."""
    
    def list(
        self,
        tenant_id: str,
        mandate_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs.
        
        Args:
            tenant_id: Your tenant ID
            mandate_id: Filter by mandate
            event_type: Filter by event type
            limit: Max results
        
        Returns:
            List of audit log entries
        """
        params = {
            'tenant_id': tenant_id,
            'limit': limit
        }
        
        if mandate_id:
            params['mandate_id'] = mandate_id
        if event_type:
            params['event_type'] = event_type
        
        return self.client.get('/api/v1/audit', params=params)


class Users(Resource):
    """User resource."""
    
    def create(
        self,
        email: str,
        password: str,
        full_name: str,
        tenant_id: str,
        role: str = "CUSTOMER_USER"
    ) -> Dict[str, Any]:
        """
        Create a user.
        
        Args:
            email: User email
            password: User password
            full_name: User full name
            tenant_id: Tenant ID
            role: User role
        
        Returns:
            Created user object
        """
        return self.client.post('/api/v1/users/register', json={
            'email': email,
            'password': password,
            'full_name': full_name,
            'tenant_id': tenant_id,
            'role': role
        })

