"""Background workers for Mandate Vault."""

from .webhook_worker import webhook_worker

__all__ = ["webhook_worker"]

