from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class SolverType(str, Enum):
    SIMPLE_FOAM = 'simpleFoam'
    ICO_FOAM = 'icoFoam'
    PISO_FOAM = 'pisoFoam'
    PIMPLE_FOAM = 'pimpleFoam'
    BUOYANT_SIMPLE_FOAM = 'buoyantSimpleFoam'
    CHT_MULTI_REGION = 'chtMultiRegionSimpleFoam'


class SimulationStatus(str, Enum):
    DRAFT = 'draft'
    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class SolverConfig(BaseModel):
    start_time: Optional[float] = Field(None, ge=0)
    end_time: Optional[float] = Field(None, gt=0)
    delta_t: Optional[float] = Field(None, gt=0)
    write_interval: Optional[float] = Field(None, gt=0)
    residual_control: Optional[bool] = True
    residual_tolerance: Optional[float] = Field(None, gt=0, le=1)
    max_iterations: Optional[int] = Field(None, ge=1)


class SimulationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    solver: SolverType


class SimulationCreate(SimulationBase):
    project_id: str
    mesh_id: Optional[str] = None
    config: Optional[SolverConfig] = None


class SimulationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[SimulationStatus] = None
    config: Optional[SolverConfig] = None


class SimulationResponse(SimulationBase):
    id: str
    project_id: str
    mesh_id: Optional[str] = None
    status: SimulationStatus
    progress: Optional[float] = Field(None, ge=0, le=1)
    current_time: Optional[float] = None
    num_iterations: Optional[int] = None
    results_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SimulationListResponse(BaseModel):
    simulations: list[SimulationResponse]
    total: int