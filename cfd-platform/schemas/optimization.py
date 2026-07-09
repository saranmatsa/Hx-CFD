"""
Optimization schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from backend.models.domain import OptimizationStatus


class OptimizationCreate(BaseModel):
    """Schema for creating an optimization."""
    project_id: str
    simulation_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    optimization_type: str = "shape"
    config: Optional[Dict[str, Any]] = None


class OptimizationUpdate(BaseModel):
    """Schema for updating an optimization."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[OptimizationStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    config: Optional[Dict[str, Any]] = None


class OptimizationResponse(BaseModel):
    """Schema for optimization response."""
    id: str
    project_id: str
    simulation_id: str
    name: str
    description: Optional[str]
    optimization_type: str
    status: OptimizationStatus
    progress: int
    config: Optional[Dict[str, Any]]
    best_parameters: Optional[Dict[str, Any]]
    best_objective_value: Optional[float]
    iteration_history: Optional[List[Dict[str, Any]]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OptimizationListResponse(BaseModel):
    """Schema for paginated optimization list response."""
    optimizations: List[OptimizationResponse]
    total: int
    page: int
    page_size: int


class OptimizationConfig(BaseModel):
    """Configuration for optimization runs."""
    algorithm: str = Field(default="nevergrad", description="Optimization algorithm")
    max_iterations: int = Field(default=100, ge=1, description="Maximum number of iterations")
    population_size: int = Field(default=50, ge=10, description="Population size for evolutionary algorithms")
    convergence_threshold: float = Field(default=1e-6, gt=0, description="Convergence threshold")
    num_workers: int = Field(default=1, ge=1, description="Number of parallel workers")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    
    class Config:
        json_schema_extra = {
            "example": {
                "algorithm": "nevergrad",
                "max_iterations": 100,
                "population_size": 50,
                "convergence_threshold": 1e-6,
                "num_workers": 1,
                "seed": 42
            }
        }


class OptimizationResult(BaseModel):
    """Schema for optimization result."""
    best_parameters: Dict[str, Any]
    best_objective_value: float
    convergence_history: List[float]
    elapsed_time: float
    num_evaluations: int
    final_population: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "best_parameters": {"x": 1.5, "y": 2.5},
                "best_objective_value": 0.001,
                "convergence_history": [0.1, 0.05, 0.01, 0.001],
                "elapsed_time": 120.5,
                "num_evaluations": 100
            }
        }


class OptimizationStatus(BaseModel):
    """Schema for optimization status."""
    status: str
    progress: int
    current_iteration: int
    best_objective_value: Optional[float] = None
    elapsed_time: float
    estimated_remaining_time: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "running",
                "progress": 50,
                "current_iteration": 50,
                "best_objective_value": 0.01,
                "elapsed_time": 60.0,
                "estimated_remaining_time": 60.0
            }
        }


class OptimizationRunRequest(BaseModel):
    """Schema for optimization run request."""
    max_iterations: int = Field(100, ge=1)
    population_size: int = Field(50, ge=10)
    convergence_threshold: float = Field(1e-6, gt=0)


class OptimizationStopRequest(BaseModel):
    """Schema for optimization stop request."""
    save_results: bool = True


class ApplyParametersRequest(BaseModel):
    """Schema for applying optimized parameters request."""
    parameters: Dict[str, Any]
    validate: bool = True


class MultiObjectiveRequest(BaseModel):
    """Schema for multi-objective optimization request."""
    objectives: List[str] = Field(..., min_items=1)
    constraints: Optional[Dict[str, Any]] = None
    max_iterations: int = Field(100, ge=1)
    population_size: int = Field(50, ge=10)