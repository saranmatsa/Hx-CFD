"""
Mesh API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from core.security import get_current_user
from db.models import User
from schemas.mesh import MeshCreate, MeshUpdate, MeshResponse, MeshListResponse
from backend.services.base import MeshService
from backend.models.domain import MeshFormat, MeshStatus
from backend.tasks.mesh_tasks import generate_mesh, refine_mesh, convert_mesh

router = APIRouter(prefix="/meshes", tags=["meshes"])


@router.post("", response_model=MeshResponse, status_code=201)
async def create_mesh(
    mesh: MeshCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new mesh."""
    service = MeshService(db)
    
    mesh_data = {
        "project_id": mesh.project_id,
        "name": mesh.name,
        "description": mesh.description,
        "format": mesh.format,
        "file_path": mesh.file_path,
        "num_cells": mesh.num_cells,
        "num_points": mesh.num_points,
        "bounding_box": mesh.bounding_box,
    }
    
    created = service.create(mesh_data)
    return created


@router.get("", response_model=MeshListResponse)
async def list_meshes(
    project_id: Optional[str] = None,
    format: Optional[MeshFormat] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all meshes."""
    service = MeshService(db)
    
    # Build filters
    filters = {}
    if project_id:
        filters["project_id"] = project_id
    if format:
        filters["format"] = format
    
    # Get paginated results
    skip = (page - 1) * page_size
    meshes = service.get_all(skip=skip, limit=page_size, **filters)
    
    # Get total count
    total = len(service.get_all(**filters))
    
    return MeshListResponse(
        meshes=meshes,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{mesh_id}", response_model=MeshResponse)
async def get_mesh(
    mesh_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a mesh by ID."""
    service = MeshService(db)
    mesh = service.get_by_id_or_raise(mesh_id)
    return mesh


@router.patch("/{mesh_id}", response_model=MeshResponse)
async def update_mesh(
    mesh_id: str,
    mesh_update: MeshUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a mesh."""
    service = MeshService(db)
    
    update_data = mesh_update.model_dump(exclude_unset=True)
    updated = service.update(mesh_id, update_data)
    
    return updated


@router.delete("/{mesh_id}", status_code=204)
async def delete_mesh(
    mesh_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a mesh."""
    service = MeshService(db)
    service.delete(mesh_id)
    return None


@router.post("/{mesh_id}/generate")
async def trigger_mesh_generation(
    mesh_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger mesh generation for a geometry."""
    service = MeshService(db)
    
    mesh = service.get_by_id_or_raise(mesh_id)
    
    # Update mesh status to pending
    service.update(mesh_id, {"status": MeshStatus.PENDING})
    
    # Trigger Celery task
    task = generate_mesh.delay(mesh_id)
    
    return {
        "task_id": task.id,
        "mesh_id": mesh_id,
        "status": "queued",
    }


@router.post("/{mesh_id}/refine")
async def trigger_mesh_refinement(
    mesh_id: str,
    refinement_level: int = Query(1, ge=1, le=5),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger mesh refinement."""
    service = MeshService(db)
    
    mesh = service.get_by_id_or_raise(mesh_id)
    
    # Update mesh status to pending
    service.update(mesh_id, {"status": MeshStatus.PENDING})
    
    # Trigger Celery task
    task = refine_mesh.delay(mesh_id, refinement_level)
    
    return {
        "task_id": task.id,
        "mesh_id": mesh_id,
        "refinement_level": refinement_level,
        "status": "queued",
    }


@router.post("/{mesh_id}/convert")
async def convert_mesh_format(
    mesh_id: str,
    target_format: MeshFormat,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convert mesh to a different format."""
    service = MeshService(db)
    
    mesh = service.get_by_id_or_raise(mesh_id)
    
    # Trigger Celery task
    task = convert_mesh.delay(mesh_id, target_format)
    
    return {
        "task_id": task.id,
        "mesh_id": mesh_id,
        "target_format": target_format,
        "status": "queued",
    }