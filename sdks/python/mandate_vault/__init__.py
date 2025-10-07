"""
Mandate Vault Python SDK
========================

Official Python client for Mandate Vault API.

Installation:
    pip install mandate-vault

Usage:
    from mandate_vault import MandateVaultClient
    
    # Initialize client
    client = MandateVaultClient(api_key='mvk_your_key')
    
    # Multi-protocol authorizations (NEW - recommended)
    auth = client.authorizations.create(
        protocol='ACP',
        payload={
            'token_id': 'acp-123',
            'psp_id': 'psp-stripe',
            'merchant_id': 'merchant-456',
            'max_amount': '5000.00',
            'currency': 'USD',
            'expires_at': '2026-01-01T00:00:00Z',
            'constraints': {}
        },
        tenant_id='your-tenant-id'
    )
    
    # Legacy mandates (DEPRECATED - AP2 only)
    mandate = client.mandates.create(vc_jwt='...', tenant_id='...')
"""

from .client import MandateVaultClient
from .exceptions import (
    MandateVaultError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    RateLimitError
)

__version__ = '1.0.0'
__all__ = [
    'MandateVaultClient',
    'MandateVaultError',
    'AuthenticationError',
    'ValidationError',
    'NotFoundError',
    'RateLimitError'
]

