"""
Default service configurations for the CFD Platform.

This module defines the default services that will be auto-started
when the application launches.
"""

from infrastructure.service_manager.models import ServiceConfig, ServiceType

# Default service configurations
DEFAULT_SERVICES: list[ServiceConfig] = [
    # Core infrastructure services
    ServiceConfig(
        name="redis",
        service_type=ServiceType.REDIS,
        default_port=6379,
        command="redis-server",
        args=["--port", "6379"],
        health_check_path=None,
        auto_start=True,
        start_timeout=10,
        stop_timeout=5,
    ),
    ServiceConfig(
        name="postgres",
        service_type=ServiceType.POSTGRESQL,
        default_port=5432,
        command="pg_ctl",
        args=["-D", "data", "-l", "logfile", "start"],
        health_check_path=None,
        auto_start=True,
        start_timeout=30,
        stop_timeout=10,
    ),
    # Application services
    ServiceConfig(
        name="backend-api",
        service_type=ServiceType.FASTAPI,
        default_port=8000,
        command="uvicorn",
        args=["backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
        env={"PYTHONPATH": "."},
        health_check_path="/api/health",
        auto_start=False,  # This is the main app itself
        start_timeout=15,
        stop_timeout=10,
    ),
    ServiceConfig(
        name="websocket",
        service_type=ServiceType.WEBSOCKET,
        default_port=8000,
        command="uvicorn",
        args=["backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--ws"],
        health_check_path="/api/health",
        auto_start=False,
        start_timeout=15,
        stop_timeout=10,
    ),
    # CFD tool services
    ServiceConfig(
        name="openfoam",
        service_type=ServiceType.OPENFOAM,
        default_port=0,  # No HTTP port
        command="bash",
        args=["-c", "source /opt/OpenFOAM/OpenFOAM-dev/etc/bashrc && foamVersion"],
        health_check_path=None,
        auto_start=False,
        start_timeout=5,
        stop_timeout=2,
    ),
    ServiceConfig(
        name="freecad",
        service_type=ServiceType.FREECAD,
        default_port=0,
        command="FreeCAD",
        args=["--version"],
        health_check_path=None,
        auto_start=False,
        start_timeout=10,
        stop_timeout=5,
    ),
    ServiceConfig(
        name="gmsh",
        service_type=ServiceType.GMSH,
        default_port=0,
        command="gmsh",
        args=["--version"],
        health_check_path=None,
        auto_start=False,
        start_timeout=5,
        stop_timeout=2,
    ),
    # Background task services
    ServiceConfig(
        name="celery-worker",
        service_type=ServiceType.CELERY_WORKER,
        default_port=0,
        command="celery",
        args=["-A", "backend.tasks.celery_app", "worker", "--loglevel=info"],
        env={"PYTHONPATH": "."},
        health_check_path=None,
        auto_start=False,
        start_timeout=20,
        stop_timeout=30,
    ),
    ServiceConfig(
        name="ai-services",
        service_type=ServiceType.AI_SERVICES,
        default_port=8001,
        command="python",
        args=["-m", "uvicorn", "backend.ai.service:app", "--host", "127.0.0.1", "--port", "8001"],
        env={"PYTHONPATH": "."},
        health_check_path="/health",
        auto_start=False,
        start_timeout=15,
        stop_timeout=10,
    ),
]


def get_default_services() -> list[ServiceConfig]:
    """Return the list of default service configurations."""
    return DEFAULT_SERVICES.copy()


def get_auto_start_services() -> list[ServiceConfig]:
    """Return only services that should auto-start."""
    return [s for s in DEFAULT_SERVICES if s.auto_start]