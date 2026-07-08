from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class VisualizationData(BaseModel):
    mesh_data: Optional[Dict[str, Any]] = None
    scalar_field: Optional[str] = None
    vector_field: Optional[str] = None
    time_step: Optional[float] = None


class MeshDataPoint(BaseModel):
    x: float
    y: float
    z: float
    connectivity: List[int]


class ScalarFieldData(BaseModel):
    points: List[List[float]]
    values: List[float]
    min_value: float
    max_value: float


class VectorFieldData(BaseModel):
    points: List[List[float]]
    vectors: List[List[float]]
    scale: float = 1.0


class StreamlineData(BaseModel):
    seed_point: List[float]
    streamlines: List[List[List[float]]]


class VisualizationResponse(BaseModel):
    mesh: Optional[MeshDataPoint] = None
    scalar_fields: Optional[Dict[str, ScalarFieldData]] = None
    vector_fields: Optional[Dict[str, VectorFieldData]] = None
    streamlines: Optional[List[StreamlineData]] = None
    time_steps: Optional[List[float]] = None
    available_fields: Optional[List[str]] = None