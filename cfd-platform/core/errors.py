"""
Core error classes for the CFD Platform.
Provides a hierarchy of custom exceptions for different error scenarios.
"""

from typing import Optional, Any, Dict


class CFDPlatformException(Exception):
    """Base exception for all CFD Platform errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "CFD_PLATFORM_ERROR"
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ProjectNotFoundError(CFDPlatformException):
    """Raised when a project cannot be found."""
    
    def __init__(self, project_id: str):
        super().__init__(
            message=f"Project with ID '{project_id}' not found",
            error_code="PROJECT_NOT_FOUND",
            details={"project_id": project_id}
        )


class ResourceNotFoundError(CFDPlatformException):
    """Raised when a requested resource cannot be found."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details=details or {"resource_type": resource_type, "resource_id": resource_id}
        )


class ValidationError(CFDPlatformException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={"field": field} if field else {}
        )


class MeshGenerationError(CFDPlatformException):
    """Raised when mesh generation fails."""
    
    def __init__(self, message: str, geometry_file: Optional[str] = None):
        super().__init__(
            message=f"Mesh generation failed: {message}",
            error_code="MESH_GENERATION_ERROR",
            details={"geometry_file": geometry_file} if geometry_file else {}
        )


class SimulationError(CFDPlatformException):
    """Raised when CFD simulation fails."""
    
    def __init__(
        self,
        message: str,
        case_dir: Optional[str] = None,
        solver: Optional[str] = None
    ):
        super().__init__(
            message=f"Simulation failed: {message}",
            error_code="SIMULATION_ERROR",
            details={
                "case_dir": case_dir,
                "solver": solver
            }
        )


class GeometryRepairError(CFDPlatformException):
    """Raised when geometry repair fails."""
    
    def __init__(self, message: str, file_path: Optional[str] = None):
        super().__init__(
            message=f"Geometry repair failed: {message}",
            error_code="GEOMETRY_REPAIR_ERROR",
            details={"file_path": file_path} if file_path else {}
        )


class CADImportError(CFDPlatformException):
    """Raised when CAD import fails."""
    
    def __init__(self, message: str, file_path: Optional[str] = None):
        super().__init__(
            message=f"CAD import failed: {message}",
            error_code="CAD_IMPORT_ERROR",
            details={"file_path": file_path} if file_path else {}
        )


class PostProcessingError(CFDPlatformException):
    """Raised when post-processing fails."""
    
    def __init__(self, message: str, result_file: Optional[str] = None):
        super().__init__(
            message=f"Post-processing failed: {message}",
            error_code="POST_PROCESSING_ERROR",
            details={"result_file": result_file} if result_file else {}
        )


class VisualizationError(CFDPlatformException):
    """Raised when visualization generation fails."""
    
    def __init__(self, message: str, visualization_type: Optional[str] = None):
        super().__init__(
            message=f"Visualization failed: {message}",
            error_code="VISUALIZATION_ERROR",
            details={"visualization_type": visualization_type} if visualization_type else {}
        )


class PipelineExecutionError(CFDPlatformException):
    """Raised when pipeline execution fails."""
    
    def __init__(self, message: str, stage: Optional[str] = None):
        super().__init__(
            message=f"Pipeline execution failed: {message}",
            error_code="PIPELINE_EXECUTION_ERROR",
            details={"stage": stage} if stage else {}
        )


class ConfigurationError(CFDPlatformException):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message=f"Configuration error: {message}",
            error_code="CONFIGURATION_ERROR",
            details={"config_key": config_key} if config_key else {}
        )


class ServiceUnavailableError(CFDPlatformException):
    """Raised when a required service is unavailable."""
    
    def __init__(self, service_name: str):
        super().__init__(
            message=f"Service '{service_name}' is currently unavailable",
            error_code="SERVICE_UNAVAILABLE",
            details={"service_name": service_name}
        )


class AuthenticationError(CFDPlatformException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(CFDPlatformException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR"
        )


class DatabaseError(CFDPlatformException):
    """Raised when a database operation fails."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message=f"Database error: {message}",
            error_code="DATABASE_ERROR",
            details={"operation": operation} if operation else {}
        )


class FileOperationError(CFDPlatformException):
    """Raised when a file operation fails."""
    
    def __init__(self, message: str, file_path: Optional[str] = None):
        super().__init__(
            message=f"File operation failed: {message}",
            error_code="FILE_OPERATION_ERROR",
            details={"file_path": file_path} if file_path else {}
        )