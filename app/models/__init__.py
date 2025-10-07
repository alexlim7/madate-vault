"""Database models."""

from .mandate import Mandate  # DEPRECATED: Use Authorization for new code
from .authorization import Authorization, ProtocolType, AuthorizationStatus
from .audit import AuditLog
from .customer import Customer
from .webhook import Webhook, WebhookDelivery
from .alert import Alert
from .user import User, UserRole, UserStatus
from .api_key import APIKey
from .acp_event import ACPEvent

__all__ = [
    "Mandate",  # DEPRECATED
    "Authorization",  # NEW: Multi-protocol table
    "ProtocolType",
    "AuthorizationStatus",
    "AuditLog",
    "Customer",
    "Webhook",
    "WebhookDelivery",
    "Alert",
    "User",
    "UserRole",
    "UserStatus",
    "APIKey",
    "ACPEvent",
]
