"""Service Manager endpoints module."""

# Re-export the router from infrastructure
from infrastructure.service_manager.api.routes import router

__all__ = ["router"]