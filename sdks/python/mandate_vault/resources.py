"""
Resource classes for API endpoints.
"""
from typing import Optional, Dict, Any, List


class Resource:
    """Base resource class."""
    
    def __init__(self, client):
        self.client = client


class Authorizations(Resource):
    """
    Authorization resource (multi-protocol: AP2 + ACP).
    
    This is the modern API for managing authorizations.
    Supports both AP2 (JWT-VC) and ACP (Delegated Token) protocols.
    """
    
    def create(
        self,
        protocol: str,
        payload: Dict[str, Any],
        tenant_id: str,
        retention_days: int = 90
    ) -> Dict[str, Any]:
        """
        Create a new authorization (AP2 or ACP).
        
        Args:
            protocol: Protocol type ('AP2' or 'ACP')
            payload: Protocol-specific payload
            tenant_id: Your tenant ID
            retention_days: Retention period
        
        Returns:
            Created authorization object
        
        Examples:
            AP2 (JWT-VC):
            >>> auth = client.authorizations.create(
            ...     protocol='AP2',
            ...     payload={'vc_jwt': 'eyJhbGc...'},
            ...     tenant_id='tenant-123'
            ... )
            
            ACP (Delegated Token):
            >>> auth = client.authorizations.create(
            ...     protocol='ACP',
            ...     payload={
            ...         'token_id': 'acp-token-123',
            ...         'psp_id': 'psp-stripe',
            ...         'merchant_id': 'merchant-456',
            ...         'max_amount': '5000.00',
            ...         'currency': 'USD',
            ...         'expires_at': '2026-01-01T00:00:00Z',
            ...         'constraints': {}
            ...     },
            ...     tenant_id='tenant-123'
            ... )
        """
        return self.client.post('/api/v1/authorizations/', json={
            'protocol': protocol,
            'payload': payload,
            'tenant_id': tenant_id,
            'retention_days': retention_days
        })
    
    def get(self, authorization_id: str) -> Dict[str, Any]:
        """
        Get authorization by ID.
        
        Args:
            authorization_id: Authorization ID
        
        Returns:
            Authorization object
        """
        return self.client.get(f'/api/v1/authorizations/{authorization_id}')
    
    def verify(self, authorization_id: str) -> Dict[str, Any]:
        """
        Re-verify an existing authorization.
        
        Args:
            authorization_id: Authorization ID
        
        Returns:
            Verification result with updated status
        """
        return self.client.post(f'/api/v1/authorizations/{authorization_id}/verify', json={})
    
    def search(
        self,
        tenant_id: str,
        protocol: Optional[str] = None,
        issuer: Optional[str] = None,
        subject: Optional[str] = None,
        status: Optional[str] = None,
        expires_before: Optional[str] = None,
        min_amount: Optional[str] = None,
        max_amount: Optional[str] = None,
        currency: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = 'created_at',
        sort_order: str = 'desc'
    ) -> Dict[str, Any]:
        """
        Search authorizations with advanced filters.
        
        Args:
            tenant_id: Your tenant ID
            protocol: Filter by protocol ('AP2' or 'ACP')
            issuer: Filter by issuer (DID or PSP ID)
            subject: Filter by subject (DID or merchant ID)
            status: Filter by status
            expires_before: ISO datetime string
            min_amount: Minimum amount filter
            max_amount: Maximum amount filter
            currency: Currency code filter
            limit: Max results per page
            offset: Pagination offset
            sort_by: Sort field
            sort_order: Sort order ('asc' or 'desc')
        
        Returns:
            Search results with authorizations list and total count
        
        Example:
            >>> results = client.authorizations.search(
            ...     tenant_id='tenant-123',
            ...     protocol='ACP',
            ...     status='VALID',
            ...     currency='USD',
            ...     min_amount='1000.00',
            ...     limit=50
            ... )
            >>> print(f"Found {results['total']} authorizations")
            >>> for auth in results['authorizations']:
            ...     print(f"  {auth['id']}: {auth['protocol']}")
        """
        params = {
            'tenant_id': tenant_id,
            'limit': limit,
            'offset': offset,
            'sort_by': sort_by,
            'sort_order': sort_order
        }
        
        if protocol:
            params['protocol'] = protocol
        if issuer:
            params['issuer'] = issuer
        if subject:
            params['subject'] = subject
        if status:
            params['status'] = status
        if expires_before:
            params['expires_before'] = expires_before
        if min_amount:
            params['min_amount'] = min_amount
        if max_amount:
            params['max_amount'] = max_amount
        if currency:
            params['currency'] = currency
        
        return self.client.post('/api/v1/authorizations/search', json=params)
    
    def revoke(self, authorization_id: str) -> Dict[str, Any]:
        """
        Revoke an authorization.
        
        Args:
            authorization_id: Authorization ID
        
        Returns:
            Revoked authorization object
        """
        return self.client.delete(f'/api/v1/authorizations/{authorization_id}')
    
    def export_evidence_pack(self, authorization_id: str, output_path: str) -> str:
        """
        Export evidence pack as ZIP file.
        
        Args:
            authorization_id: Authorization ID
            output_path: Path to save ZIP file
        
        Returns:
            Path to saved ZIP file
        
        Example:
            >>> path = client.authorizations.export_evidence_pack(
            ...     authorization_id='auth-123',
            ...     output_path='./evidence_pack.zip'
            ... )
            >>> print(f"Evidence pack saved to {path}")
        """
        response = self.client.get_raw(f'/api/v1/authorizations/{authorization_id}/evidence-pack')
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        return output_path


class Mandates(Resource):
    """
    Mandate resource (DEPRECATED).
    
    ⚠️ Use `client.authorizations` instead for new code.
    
    This resource only supports AP2 (JWT-VC) protocol.
    The new `Authorizations` resource supports both AP2 and ACP protocols.
    """
    
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

