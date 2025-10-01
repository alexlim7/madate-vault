"""
Exception classes for Mandate Vault SDK.
"""


class MandateVaultError(Exception):
    """Base exception for all Mandate Vault errors."""
    
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthenticationError(MandateVaultError):
    """Authentication failed (401)."""
    pass


class ValidationError(MandateVaultError):
    """Validation error (400, 422)."""
    pass


class NotFoundError(MandateVaultError):
    """Resource not found (404)."""
    pass


class RateLimitError(MandateVaultError):
    """Rate limit exceeded (429)."""
    
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message, 429)
        self.retry_after = retry_after


class ServerError(MandateVaultError):
    """Server error (500+)."""
    pass


def handle_error_response(response):
    """
    Handle error responses from API.
    
    Args:
        response: requests.Response object
    
    Raises:
        MandateVaultError: Appropriate exception
    """
    status_code = response.status_code
    
    try:
        error_data = response.json()
        message = error_data.get('detail', 'Unknown error')
    except:
        message = response.text or 'Unknown error'
    
    if status_code == 401:
        raise AuthenticationError(message, status_code)
    elif status_code in (400, 422):
        raise ValidationError(message, status_code)
    elif status_code == 404:
        raise NotFoundError(message, status_code)
    elif status_code == 429:
        retry_after = response.headers.get('Retry-After')
        raise RateLimitError(message, int(retry_after) if retry_after else None)
    elif status_code >= 500:
        raise ServerError(message, status_code)
    else:
        raise MandateVaultError(message, status_code)

