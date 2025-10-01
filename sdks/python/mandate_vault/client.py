"""
Main client for Mandate Vault API.
"""
import requests
from typing import Optional, Dict, Any, List
from .resources import Mandates, Webhooks, Audit, Users
from .exceptions import handle_error_response


class MandateVaultClient:
    """
    Mandate Vault API Client.
    
    Args:
        api_key: Your API key (starts with 'mvk_')
        base_url: API base URL (default: production)
        timeout: Request timeout in seconds
    
    Example:
        >>> client = MandateVaultClient(api_key='mvk_...')
        >>> mandate = client.mandates.create(vc_jwt='...', tenant_id='...')
        >>> print(mandate['id'])
    """
    
    DEFAULT_BASE_URL = 'https://api.mandatevault.com'
    DEFAULT_TIMEOUT = 30
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT
    ):
        if not api_key or not api_key.startswith('mvk_'):
            raise ValueError("Invalid API key. Must start with 'mvk_'")
        
        self.api_key = api_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip('/')
        self.timeout = timeout
        
        # Initialize resource clients
        self.mandates = Mandates(self)
        self.webhooks = Webhooks(self)
        self.audit = Audit(self)
        self.users = Users(self)
    
    def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            **kwargs: Additional arguments for requests
        
        Returns:
            Response JSON
        
        Raises:
            MandateVaultError: On API errors
        """
        url = f"{self.base_url}{path}"
        
        # Set headers
        headers = kwargs.pop('headers', {})
        headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'mandate-vault-python/1.0.0'
        })
        
        # Make request
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            
            # Handle errors
            if response.status_code >= 400:
                handle_error_response(response)
            
            # Return JSON
            if response.status_code == 204:  # No content
                return {}
            
            return response.json()
            
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Connection error: {str(e)}")
    
    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make GET request."""
        return self._request('GET', path, **kwargs)
    
    def post(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make POST request."""
        return self._request('POST', path, **kwargs)
    
    def patch(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make PATCH request."""
        return self._request('PATCH', path, **kwargs)
    
    def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make DELETE request."""
        return self._request('DELETE', path, **kwargs)

