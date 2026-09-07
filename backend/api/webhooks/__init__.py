"""
Webhooks API package.
Exports storage and Eventarc webhook routers.
"""

from backend.api.webhooks.storage import storage_webhook_router

__all__ = ["storage_webhook_router"]
