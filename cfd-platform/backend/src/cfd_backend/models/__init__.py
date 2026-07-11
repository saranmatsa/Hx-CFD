"""
Models package for CFD Backend.

Exports all SQLAlchemy models for database operations.
"""

from cfd_backend.models.base import Base, BaseModel, BaseModelWithSoftDelete
from cfd_backend.models.project import (
    Project,
    ProjectStatus,
    ProjectVisibility,
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
from cfd_backend.models.mesh import (
    MeshFormat,
    MeshQualityMetric,
    MeshGenerationMethod,
)
from cfd_backend.models.optimization import (
    OptimizationStudy,
    StudyType,
    StudyStatus,
    OptimizationTrial,
    TrialStatus,
    SurrogateModel,
    SurrogateType,
)
from cfd_backend.models.simulation import (
    Simulation,
    SimulationStatus,
    SolverType,
)
from cfd_backend.models.solver import (
    SolverConfig,
    SolverStatus,
)
from cfd_backend.models.simulation_result import (
    SimulationResult,
    ResultType,
    ResultStatus,
)

__all__ = [
    # Base
    "Base",
    "BaseModel",
    "BaseModelWithSoftDelete",
    # Project models
    "Project",
    "ProjectStatus",
    "ProjectVisibility",
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
    # Optimization models
    "OptimizationStudy",
    "StudyType",
    "StudyStatus",
    "OptimizationTrial",
    "TrialStatus",
    "SurrogateModel",
    "SurrogateType",
    # Simulation models
    "SolverType",
    "SolverConfig",
    "SolverStatus",
    "SimulationResult",
    "ResultType",
    "ResultStatus",
    # User models
    "User",
    "UserRole",
    "UserStatus",
    "APIKey",
    "UserSession",
    "ProjectMember",
    # Mesh enums (from mesh.py)
    "MeshFormat",
    "MeshQualityMetric",
    "MeshGenerationMethod",
]