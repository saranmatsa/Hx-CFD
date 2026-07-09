"""
Visualization schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class MeshDataPoint(BaseModel):
    """Schema for a mesh data point."""
    x: float
    y: float
    z: float
    index: int


class ScalarFieldData(BaseModel):
    """Schema for scalar field data (e.g., pressure, temperature)."""
    field_name: str
    values: List[float]
    min_value: float
    max_value: float
    units: Optional[str] = None


class VectorFieldData(BaseModel):
    """Schema for vector field data (e.g., velocity, force)."""
    field_name: str
    x_components: List[float]
    y_components: List[float]
    z_components: List[float]
    magnitude: List[float]
    units: Optional[str] = None


class VisualizationData(BaseModel):
    """Schema for visualization data."""
    mesh_points: List[MeshDataPoint]
    cells: List[List[int]]
    scalar_fields: List[ScalarFieldData]
    vector_fields: List[VectorFieldData]
    time_values: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


class VisualizationResponse(BaseModel):
    """Schema for visualization response."""
    id: str
    simulation_id: str
    visualization_type: str
    data: VisualizationData
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SliceConfig(BaseModel):
    """Configuration for mesh slicing."""
    axis: str = Field(..., description="Slice axis: x, y, or z")
    position: float = Field(..., description="Position along the axis")
    num_points: int = Field(default=100, ge=10, le=1000, description="Number of points in the slice")
    
    class Config:
        json_schema_extra = {
            "example": {
                "axis": "z",
                "position": 0.5,
                "num_points": 100
            }
        }


class ContourConfig(BaseModel):
    """Configuration for contour generation."""
    field_name: str = Field(..., description="Field to create contours from")
    num_levels: int = Field(default=10, ge=2, le=50, description="Number of contour levels")
    show_labels: bool = Field(default=True, description="Show contour labels")
    
    class Config:
        json_schema_extra = {
            "example": {
                "field_name": "pressure",
                "num_levels": 10,
                "show_labels": True
            }
        }


class ImageExportConfig(BaseModel):
    """Configuration for image export."""
    width: int = Field(default=1920, ge=100, le=4096, description="Image width in pixels")
    height: int = Field(default=1080, ge=100, le=4096, description="Image height in pixels")
    format: str = Field(default="png", description="Image format (png, jpg, svg)")
    background_color: str = Field(default="#ffffff", description="Background color")
    show_legend: bool = Field(default=True, description="Show color legend")
    show_axes: bool = Field(default=True, description="Show coordinate axes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "width": 1920,
                "height": 1080,
                "format": "png",
                "background_color": "#ffffff",
                "show_legend": True,
                "show_axes": True
            }
        }


class AnimationConfig(BaseModel):
    """Configuration for animation generation."""
    time_steps: List[float] = Field(..., description="Time steps to include in animation")
    fps: int = Field(default=24, ge=1, le=60, description="Frames per second")
    quality: str = Field(default="high", description="Video quality (low, medium, high)")
    format: str = Field(default="mp4", description="Video format (mp4, gif)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "time_steps": [0.0, 0.1, 0.2, 0.3],
                "fps": 24,
                "quality": "high",
                "format": "mp4"
            }
        }