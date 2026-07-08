"""
Error handling utilities.
"""

from typing import Optional
from fastapi import HTTPException, status


class CFDPlatformException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class MeshGenerationError(CFDPlatformException):
    def __init__(self, message: str = "Mesh generation failed"):
        super().__init__(message, status_code=400)


class SimulationError(CFDPlatformException):
    def __init__(self, message: str = "Simulation failed"):
        super().__init__(message, status_code=400)


class FileProcessingError(CFDPlatformException):
    def __init__(self, message: str = "File processing failed"):
        super().__init__(message, status_code=400)


class ProjectNotFoundError(CFDPlatformException):
    def __init__(self, project_id: str):
        super().__init__(f"Project {project_id} not found", status_code=404)


class UnauthorizedError(CFDPlatformException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


def raise_http_exception(error: CFDPlatformException):
    raise HTTPException(status_code=error.status_code, detail=error.message)


# Aliases for backwards compatibility
CFDError = CFDPlatformException
NotFoundError = ProjectNotFoundError


__all__ = [
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