from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class VisualizationType(str, Enum):
    CONTOUR = 'contour'
    VECTOR = 'vector'
    STREAMLINE = 'streamline'
    ISO_SURFACE = 'iso-surface'
    SLICE = 'slice'


class VisualizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    visualization_type: VisualizationType


class VisualizationCreate(VisualizationBase):
    project_id: str
    simulation_id: Optional[str] = None


class VisualizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class VisualizationResponse(VisualizationBase):
    id: str
    project_id: str
    simulation_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MeshData(BaseModel):
    points: list[list[float]]
    connectivity: list[int]
    bounding_box: dict


class ScalarFieldData(BaseModel):
    field_name: str
    points: list[list[float]]
    values: list[float]
    min_value: float
    max_value: float
    time_step: int


class VectorFieldData(BaseModel):
    field_name: str
    points: list[list[float]]
    vectors: list[list[float]]
    scale: float
    time_step: int


class ResidualData(BaseModel):
    residuals: list[dict[str, float]]


class ForceData(BaseModel):
    forces: list[dict[str, float]]