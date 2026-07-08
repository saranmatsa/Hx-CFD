from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class MeshStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class MeshQualityMetrics(BaseModel):
    min_quality: float
    max_quality: float
    avg_quality: float
    min_aspect_ratio: float
    max_aspect_ratio: float


class MeshBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class MeshCreate(MeshBase):
    project_id: str
    config: Optional[Dict[str, Any]] = None


class MeshConfig(BaseModel):
    element_size: float = 0.1
    growth_rate: float = 1.2
    min_cells: int = 10
    max_cells: int = 1000000
    boundary_layers: bool = True
    num_boundary_layers: int = 3


class MeshResponse(MeshBase):
    id: str
    project_id: str
    file_path: Optional[str] = None
    num_cells: Optional[int] = None
    num_points: Optional[int] = None
    quality_metrics: Optional[MeshQualityMetrics] = None
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True