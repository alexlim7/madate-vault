"""
Mandate Vault Python SDK
========================

Official Python client for Mandate Vault API.

Installation:
    pip install mandate-vault

Usage:
    from mandate_vault import MandateVaultClient
    
    client = MandateVaultClient(api_key='mvk_your_key')
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

