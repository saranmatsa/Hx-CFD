"""
Mesh schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from backend.models.domain import MeshFormat, MeshStatus


class MeshCreate(BaseModel):
    """Schema for creating a mesh."""
    project_id: str
    geometry_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    format: MeshFormat = MeshFormat.UNSTRUCTURED
    element_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class MeshUpdate(BaseModel):
    """Schema for updating a mesh."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[MeshStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    config: Optional[Dict[str, Any]] = None


class MeshConfig(BaseModel):
    """Configuration schema for mesh generation."""
    mesh_size: float = Field(default=0.1, ge=0.001, le=10.0, description="Global mesh element size")
    refinement_level: int = Field(default=0, ge=0, le=5, description="Mesh refinement level")
    boundary_layers: bool = Field(default=True, description="Enable boundary layer meshing")
    num_boundary_layers: int = Field(default=3, ge=1, le=10, description="Number of boundary layers")
    growth_rate: float = Field(default=1.2, ge=1.0, le=2.0, description="Boundary layer growth rate")
    min_quality: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum mesh quality threshold")
    optimize_mesh: bool = Field(default=True, description="Optimize mesh after generation")
    algorithm: Optional[str] = Field(default="auto", description="Meshing algorithm (frontal, del2d, etc.)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "mesh_size": 0.1,
                "refinement_level": 0,
                "boundary_layers": True,
                "num_boundary_layers": 3,
                "growth_rate": 1.2,
                "min_quality": 0.3,
                "optimize_mesh": True,
                "algorithm": "auto"
            }
        }


class MeshResponse(BaseModel):
    """Schema for mesh response."""
    id: str
    project_id: str
    geometry_id: Optional[str]
    name: str
    description: Optional[str]
    format: MeshFormat
    element_type: Optional[str]
    num_cells: Optional[int]
    num_points: Optional[int]
    status: MeshStatus
    progress: int
    file_path: Optional[str]
    config: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MeshListResponse(BaseModel):
    """Schema for paginated mesh list response."""
    meshes: List[MeshResponse]
    total: int
    page: int
    page_size: int


class MeshGenerateRequest(BaseModel):
    """Schema for mesh generation request."""
    geometry_id: str
    mesh_size: float = Field(0.1, gt=0)
    element_type: str = "tet"
    optimization_level: int = Field(2, ge=0, le=3)
    num_processors: int = Field(1, ge=1)


class MeshRefineRequest(BaseModel):
    """Schema for mesh refinement request."""
    refinement_level: int = Field(1, ge=1, le=5)
    cell_zones: Optional[List[str]] = None


class MeshConvertRequest(BaseModel):
    """Schema for mesh format conversion request."""
    target_format: MeshFormat
    overwrite: bool = False