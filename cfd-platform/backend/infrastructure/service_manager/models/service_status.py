"""Service status and type enumerations."""

from enum import Enum


class ServiceStatus(str, Enum):
    """Status of a managed service."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    UNHEALTHY = "unhealthy"
    STOPPING = "stopping"


class ServiceType(str, Enum):
    """Type of service managed by the Service Manager."""

    FASTAPI = "fastapi"
    OPENFOAM = "openfoam"
    FREECAD = "freecad"
    GMSH = "gmsh"
    AI_SERVICES = "ai_services"
    CELERY_WORKER = "celery_worker"
    REDIS = "redis"
    POSTGRESQL = "postgresql"
    WEBSOCKET = "websocket"