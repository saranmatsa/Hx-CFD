from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SolverType(str, Enum):
    SIMPLE = "simpleFoam"
    RHO = "rhoSimpleFoam"
    BUOYANT = "buoyantSimpleFoam"
    MULTIPHASE = "interFoam"
    LES = "pisoFoam"


class SimulationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class SimulationCreate(SimulationBase):
    project_id: str
    mesh_id: Optional[str] = None
    solver: SolverType = SolverType.SIMPLE
    config: Optional[Dict[str, Any]] = None


class SimulationConfig(BaseModel):
    solver: str = "simpleFoam"
    start_time: float = 0.0
    end_time: float = 1.0
    delta_t: float = 0.001
    write_interval: float = 0.05
    residual_control: bool = True
    max_iterations: int = 1000
    residual_tolerance: float = 1e-6
    
    # Turbulence model
    turbulence_model: str = "kEpsilon"
    
    # Boundary conditions
    inlet_velocity: float = 10.0
    inlet_direction: List[float] = [1.0, 0.0, 0.0]
    outlet_pressure: float = 0.0
    wall_condition: str = "noSlip"


class ResidualData(BaseModel):
    iteration: int
    continuity: float
    p: float
    U: float
    k: Optional[float] = None
    epsilon: Optional[float] = None


class ForceData(BaseModel):
    time: float
    Cd: float
    Cl: float
    Cm: float
    Cd_p: float
    Cd_f: float
    Cl_p: float
    Cl_f: float


class SimulationResponse(SimulationBase):
    id: str
    project_id: str
    mesh_id: Optional[str] = None
    solver: str
    case_path: Optional[str] = None
    results_path: Optional[str] = None
    progress: float
    residuals: Optional[List[ResidualData]] = None
    forces: Optional[List[ForceData]] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True