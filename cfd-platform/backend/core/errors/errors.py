"""
Custom exception classes for CFD Platform.
"""

from typing import Optional, Any


class CFDError(Exception):
    """Base exception for all CFD platform errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


class MeshGenerationError(CFDError):
    """Raised when mesh generation fails."""
    pass


class SimulationError(CFDError):
    """Raised when simulation fails."""
    pass


class OptimizationError(CFDError):
    """Raised when optimization fails."""
    pass


class VisualizationError(CFDError):
    """Raised when visualization operations fail."""
    pass


class GeometryError(CFDError):
    """Raised when geometry operations fail."""
    pass


class ValidationError(CFDError):
    """Raised when validation fails."""
    pass


class ConfigurationError(CFDError):
    """Raised when configuration is invalid."""
    pass


class ExternalToolError(CFDError):
    """Raised when external tool (Gmsh, OpenFOAM, etc.) fails."""
    
    def __init__(self, tool_name: str, message: str, return_code: Optional[int] = None):
        super().__init__(
            f"{tool_name} error: {message}",
            {"tool": tool_name, "return_code": return_code}
        )
        self.tool_name = tool_name


class AuthenticationError(CFDError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(CFDError):
    """Raised when authorization fails."""
    pass


class ResourceNotFoundError(CFDError):
    """Raised when a requested resource is not found."""
    pass


class JobError(CFDError):
    """Raised when a background job fails."""
    pass