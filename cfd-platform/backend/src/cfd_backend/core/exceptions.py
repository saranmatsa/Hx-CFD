"""
Custom exceptions for CFD Backend.

Provides a hierarchy of exceptions for different error categories
with proper HTTP status codes and error codes for API responses.
"""

from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import structlog

logger = structlog.get_logger(__name__)


class CFDException(Exception):
    """Base exception for CFD Platform errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "CFD_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ConfigurationError(CFDException):
    """Configuration-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class DependencyError(CFDException):
    """External dependency errors (OpenFOAM, Gmsh, ParaView, etc.)."""
    
    def __init__(
        self,
        message: str,
        dependency: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="DEPENDENCY_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={**(details or {}), "dependency": dependency},
        )


class SimulationError(CFDException):
    """Simulation execution errors."""
    
    def __init__(
        self,
        message: str,
        simulation_id: Optional[str] = None,
        stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="SIMULATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={**(details or {}), "simulation_id": simulation_id, "stage": stage},
        )


class MeshingError(SimulationError):
    """Mesh generation errors."""
    
    def __init__(
        self,
        message: str,
        simulation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            simulation_id=simulation_id,
            stage="meshing",
            details=details,
        )
        self.error_code = "MESHING_ERROR"


class SolverError(SimulationError):
    """CFD solver execution errors."""
    
    def __init__(
        self,
        message: str,
        simulation_id: Optional[str] = None,
        solver: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            simulation_id=simulation_id,
            stage="solving",
            details={**(details or {}), "solver": solver},
        )
        self.error_code = "SOLVER_ERROR"


class PostProcessingError(SimulationError):
    """Post-processing errors."""
    
    def __init__(
        self,
        message: str,
        simulation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            simulation_id=simulation_id,
            stage="post_processing",
            details=details,
        )
        self.error_code = "POST_PROCESSING_ERROR"


class ProjectError(CFDException):
    """Project management errors."""
    
    def __init__(
        self,
        message: str,
        project_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="PROJECT_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={**(details or {}), "project_id": project_id},
        )


class ValidationError(CFDException):
    """Input validation errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={**(details or {}), "field": field},
        )


class NotFoundError(CFDException):
    """Resource not found errors."""
    
    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={**(details or {}), "resource_type": resource_type, "resource_id": resource_id},
        )


class PermissionError(CFDException):
    """Permission/authorization errors."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class AuthenticationError(CFDException):
    """Authentication errors."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class TimeoutError(CFDException):
    """Operation timeout errors."""
    
    def __init__(
        self,
        message: str,
        operation: str,
        timeout_seconds: int,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="TIMEOUT",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details={**(details or {}), "operation": operation, "timeout_seconds": timeout_seconds},
        )


class ResourceExhaustedError(CFDException):
    """Resource exhaustion errors (memory, disk, CPU)."""
    
    def __init__(
        self,
        message: str,
        resource: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="RESOURCE_EXHAUSTED",
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            details={**(details or {}), "resource": resource},
        )


def setup_exception_handlers(app: FastAPI) -> None:
    """Set up global exception handlers for the FastAPI app."""
    
    @app.exception_handler(CFDException)
    async def cfd_exception_handler(request: Request, exc: CFDException) -> JSONResponse:
        logger.error(
            "CFD Exception",
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )
    
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
        logger.warning(
            "Validation Error",
            errors=exc.errors(),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {"errors": exc.errors()},
                }
            },
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled Exception",
            error_type=type(exc).__name__,
            message=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {"error_type": type(exc).__name__},
                }
            },
        )