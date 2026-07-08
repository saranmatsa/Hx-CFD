from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    MESHING = "meshing"
    READY = "ready"
    SIMULATING = "simulating"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    geometry_file: Optional[str] = None
    mesh_config: Optional[Dict[str, Any]] = None
    simulation_config: Optional[Dict[str, Any]] = None
    status: Optional[ProjectStatus] = None


class ProjectResponse(ProjectBase):
    id: str
    owner_id: str
    geometry_file: Optional[str] = None
    mesh_config: Optional[Dict[str, Any]] = None
    simulation_config: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
    page: int
    page_size: int