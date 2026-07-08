"""
Service Manager Infrastructure

Provides local desktop deployment capabilities for the CFD platform.
Manages local services, health checks, and graceful shutdown.
"""

from .manager import ServiceManager, get_service_manager
from .models import (
    ServiceStatus,
    ServiceInfo,
    ServiceConfig,
    HealthCheckResult,
    ServiceType,
)

__all__ = [
    "ServiceManager",
    "get_service_manager",
    "ServiceStatus",
    "ServiceInfo",
    "ServiceConfig",
    "HealthCheckResult",
    "ServiceType",
]