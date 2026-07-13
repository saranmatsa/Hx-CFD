"""
Service container for CFD Backend.

This module provides the main service container for dependency injection,
re-exporting the ServiceContainer from core.dependencies.
"""

from cfd_backend.core.dependencies import (
    ServiceContainer,
    get_service_container,
    get_db_session,
    get_redis_client,
    get_settings_dependency,
)

__all__ = [
    "ServiceContainer",
    "get_service_container",
    "get_db_session",
    "get_redis_client",
    "get_settings_dependency",
]