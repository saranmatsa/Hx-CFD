"""
Models package for CFD Backend.

Exports all SQLAlchemy models for database operations.
"""

from cfd_backend.models.base import Base, BaseModel, BaseModelWithSoftDelete
from cfd_backend.models.project import (
    Project,
    ProjectStatus,
    Simulation,
    SimulationStatus,
    Mesh,
    MeshType,
    MeshStatus,
    Optimization,
    OptimizationStatus,
    OptimizationAlgorithm,
    TurbulenceModel,
    SimulationType,
)
from cfd_backend.models.user import (
    User,
    UserRole,
    UserStatus,
    APIKey,
    UserSession,
    ProjectMember,
)

__all__ = [
    # Base
    "Base",
    "BaseModel",
    "BaseModelWithSoftDelete",
    # Project models
    "Project",
    "ProjectStatus",
    "Simulation",
    "SimulationStatus",
    "Mesh",
    "MeshType",
    "MeshStatus",
    "Optimization",
    "OptimizationStatus",
    "OptimizationAlgorithm",
    "TurbulenceModel",
    "SimulationType",
    # User models
    "User",
    "UserRole",
    "UserStatus",
    "APIKey",
    "UserSession",
    "ProjectMember",
]