"""Schemas package - Pydantic models for API request/response validation."""

from schemas.mesh import (
    MeshCreate,
    MeshUpdate,
    MeshResponse,
    MeshListResponse,
    MeshGenerateRequest,
    MeshRefineRequest,
    MeshConvertRequest,
)
from schemas.simulation import (
    SimulationCreate,
    SimulationUpdate,
    SimulationResponse,
    SimulationListResponse,
    SimulationRunRequest,
    SimulationStopRequest,
    ExtractResultsRequest,
    PostProcessRequest,
)
from schemas.optimization import (
    OptimizationCreate,
    OptimizationUpdate,
    OptimizationResponse,
    OptimizationListResponse,
    OptimizationRunRequest,
    OptimizationStopRequest,
    ApplyParametersRequest,
    MultiObjectiveRequest,
)

__all__ = [
    # Mesh schemas
    "MeshCreate",
    "MeshUpdate",
    "MeshResponse",
    "MeshListResponse",
    "MeshGenerateRequest",
    "MeshRefineRequest",
    "MeshConvertRequest",
    # Simulation schemas
    "SimulationCreate",
    "SimulationUpdate",
    "SimulationResponse",
    "SimulationListResponse",
    "SimulationRunRequest",
    "SimulationStopRequest",
    "ExtractResultsRequest",
    "PostProcessRequest",
    # Optimization schemas
    "OptimizationCreate",
    "OptimizationUpdate",
    "OptimizationResponse",
    "OptimizationListResponse",
    "OptimizationRunRequest",
    "OptimizationStopRequest",
    "ApplyParametersRequest",
    "MultiObjectiveRequest",
]