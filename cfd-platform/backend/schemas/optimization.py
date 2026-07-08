from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OptimizationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class OptimizationAlgorithm(str, Enum):
    NGOpt = "ngopt"
    CMAES = "cmaes"
    PSO = "pso"
    COBYLA = "cobyla"


class ParameterDefinition(BaseModel):
    name: str
    min_value: float
    max_value: float
    initial_value: Optional[float] = None


class OptimizationConfig(BaseModel):
    algorithm: OptimizationAlgorithm = OptimizationAlgorithm.NGOpt
    max_iterations: int = 100
    population_size: int = 50
    parameters: List[ParameterDefinition]
    objective_function: str = "Cd"
    constraints: Optional[Dict[str, float]] = None


class OptimizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class OptimizationCreate(OptimizationBase):
    project_id: str
    simulation_id: str
    config: OptimizationConfig


class OptimizationResult(BaseModel):
    iteration: int
    parameters: Dict[str, float]
    objectives: Dict[str, float]
    constraints: Optional[Dict[str, float]] = None


class OptimizationResponse(OptimizationBase):
    id: str
    project_id: str
    simulation_id: str
    config: OptimizationConfig
    status: str
    best_parameters: Optional[Dict[str, float]] = None
    best_objectives: Optional[Dict[str, float]] = None
    results: Optional[List[OptimizationResult]] = None
    progress: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True