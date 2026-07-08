from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class MeshType(str, Enum):
    UNSTRUCTURED = 'unstructured'
    STRUCTURED = 'structured'
    HYBRID = 'hybrid'


class MeshStatus(str, Enum):
    PENDING = 'pending'
    GENERATING = 'generating'
    COMPLETED = 'completed'
    FAILED = 'failed'


class BoundingBox(BaseModel):
    min: tuple[float, float, float]
    max: tuple[float, float, float]


class MeshConfig(BaseModel):
    element_size: Optional[float] = Field(None, gt=0)
    growth_rate: Optional[float] = Field(None, gt=0, le=1)
    num_boundary_layers: Optional[int] = Field(None, ge=0)
    min_cells_x: Optional[int] = Field(None, ge=1)
    min_cells_y: Optional[int] = Field(None, ge=1)
    min_cells_z: Optional[int] = Field(None, ge=1)


class MeshBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    mesh_type: Optional[MeshType] = MeshType.UNSTRUCTURED


class MeshCreate(MeshBase):
    project_id: str
    config: Optional[MeshConfig] = None


class MeshUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[MeshStatus] = None


class MeshResponse(MeshBase):
    id: str
    project_id: str
    status: MeshStatus
    num_cells: Optional[int] = None
    num_points: Optional[int] = None
    num_boundaries: Optional[int] = None
    bounding_box: Optional[BoundingBox] = None
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True