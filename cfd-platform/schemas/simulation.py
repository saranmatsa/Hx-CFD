"""
Simulation schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from backend.models.domain import SolverType, SimulationStatus


class SimulationCreate(BaseModel):
    """Schema for creating a simulation."""
    project_id: str
    mesh_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    solver_type: SolverType = SolverType.SIMPLE
    config: Optional[Dict[str, Any]] = None


class SimulationUpdate(BaseModel):
    """Schema for updating a simulation."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[SimulationStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    config: Optional[Dict[str, Any]] = None


class SimulationResponse(BaseModel):
    """Schema for simulation response."""
    id: str
    project_id: str
    mesh_id: str
    name: str
    description: Optional[str]
    solver_type: SolverType
    status: SimulationStatus
    progress: int
    config: Optional[Dict[str, Any]]
    results_path: Optional[str]
    residuals: Optional[Dict[str, List[float]]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SimulationListResponse(BaseModel):
    """Schema for paginated simulation list response."""
    simulations: List[SimulationResponse]
    total: int
    page: int
    page_size: int


class SimulationRunRequest(BaseModel):
    """Schema for simulation run request."""
    start_time: Optional[float] = 0
    end_time: Optional[float] = 1
    time_step: Optional[float] = 0.001
    num_processors: int = Field(1, ge=1)


class SimulationStopRequest(BaseModel):
    """Schema for simulation stop request."""
    graceful: bool = True


class ExtractResultsRequest(BaseModel):
    """Schema for result extraction request."""
    fields: List[str] = ["velocity", "pressure"]
    time_points: Optional[List[float]] = None


class PostProcessRequest(BaseModel):
    """Schema for post-processing request."""
    operations: List[str] = Field(..., min_items=1)
    parameters: Optional[Dict[str, Any]] = None