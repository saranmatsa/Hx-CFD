from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class OptimizationAlgorithm(str, Enum):
    NELDER_MEAD = 'Nelder-Mead'
    COBYLA = 'COBYLA'
    POWELL = 'Powell'
    DE = 'DE'
    CMA_ES = 'CMA-ES'
    NSGA_II = 'NSGA-II'


class OptimizationStatus(str, Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'


class OptimizationConfig(BaseModel):
    num_iterations: Optional[int] = Field(None, ge=1)
    population_size: Optional[int] = Field(None, ge=2)
    objective_function: Optional[str] = None
    constraints: Optional[dict[str, float]] = None


class OptimizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    algorithm: OptimizationAlgorithm


class OptimizationCreate(OptimizationBase):
    project_id: str
    simulation_id: Optional[str] = None
    config: Optional[OptimizationConfig] = None


class OptimizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[OptimizationStatus] = None


class OptimizationResponse(OptimizationBase):
    id: str
    project_id: str
    simulation_id: Optional[str] = None
    status: OptimizationStatus
    progress: Optional[float] = Field(None, ge=0, le=1)
    best_objective: Optional[float] = None
    results_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OptimizationListResponse(BaseModel):
    optimizations: list[OptimizationResponse]
    total: int