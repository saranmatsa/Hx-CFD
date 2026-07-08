"""
Core module for CFD Platform.
"""

from .config import get_settings
from .database import get_db, engine
from .errors import (
    CFDPlatformException,
    CFDError,
    MeshGenerationError,
    SimulationError,
    FileProcessingError,
    ProjectNotFoundError,
    NotFoundError,
    UnauthorizedError,
    raise_http_exception,
)

__all__ = [
    "get_settings",
    "get_db",
    "engine",
    "CFDPlatformException",
    "CFDError",
    "MeshGenerationError",
    "SimulationError",
    "FileProcessingError",
    "ProjectNotFoundError",
    "NotFoundError",
    "UnauthorizedError",
    "raise_http_exception",
]