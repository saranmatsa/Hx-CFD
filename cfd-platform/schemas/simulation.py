"""
Simulation schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from backend.models.domain import SolverType, SimulationStatus


class SimulationConfig(BaseModel):
    """Configuration schema for simulation parameters."""
    solver_type: SolverType = Field(default=SolverType.SIMPLE, description="CFD solver type")
    start_time: float = Field(default=0.0, ge=0.0, description="Simulation start time")
    end_time: float = Field(default=1.0, ge=0.0, description="Simulation end time")
    time_step: float = Field(default=0.001, ge=1e-10, description="Time step size")
    num_processors: int = Field(default=1, ge=1, le=128, description="Number of processors")
    write_interval: int = Field(default=100, ge=1, description="Write results every N iterations")
    residual_tolerance: float = Field(default=1e-5, ge=1e-10, le=1e-2, description="Convergence tolerance")
    max_iterations: int = Field(default=1000, ge=1, description="Maximum iterations per time step")
    relaxation_factor: float = Field(default=0.3, ge=0.0, le=1.0, description="Relaxation factor for stability")
    enable_parallel: bool = Field(default=False, description="Enable parallel computation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "solver_type": "simple",
                "start_time": 0.0,
                "end_time": 1.0,
                "time_step": 0.001,
                "num_processors": 1,
                "write_interval": 100,
                "residual_tolerance": 1e-5,
                "max_iterations": 1000,
                "relaxation_factor": 0.3,
                "enable_parallel": False
            }
        }


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