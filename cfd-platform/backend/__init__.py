"""Backend package - services, API routes, tasks, and WebSocket management."""

from backend.models.domain import (
    ProjectStatus,
    GeometryFormat,
    MeshFormat,
    SolverType,
    SimulationStatus,
    OptimizationStatus,
    JobStatus,
    UUIDModel,
    TimestampModel,
    Project,
    Geometry,
    Mesh,
    Simulation,
    SimulationConfig,
    Optimization,
    OptimizationConfig,
    Job,
    Visualization,
    VisualizationConfig,
    AIProviderConfig,
    AIConversation,
)

__all__ = [
    # Enums
    "ProjectStatus",
    "GeometryFormat",
    "MeshFormat",
    "SolverType",
    "SimulationStatus",
    "OptimizationStatus",
    "JobStatus",
    # Base models
    "UUIDModel",
    "TimestampModel",
    # Domain models
    "Project",
    "Geometry",
    "Mesh",
    "Simulation",
    "SimulationConfig",
    "Optimization",
    "OptimizationConfig",
    "Job",
    "Visualization",
    "VisualizationConfig",
    "AIProviderConfig",
    "AIConversation",
]