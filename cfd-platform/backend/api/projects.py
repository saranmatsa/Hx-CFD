"""
Project API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from core.security import get_current_user
from db.models import User
from schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from backend.services.base import ProjectService
from backend.models.domain import ProjectStatus

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new project."""
    service = ProjectService(db)
    
    project_data = {
        "name": project.name,
        "description": project.description,
        "owner_id": str(current_user.id),
    }
    
    created = service.create(project_data)
    return created


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ProjectStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all projects for the current user."""
    service = ProjectService(db)
    
    # Build filters
    filters = {"owner_id": str(current_user.id)}
    if status:
        filters["status"] = status
    
    # Get paginated results
    skip = (page - 1) * page_size
    projects = service.get_all(skip=skip, limit=page_size, **filters)
    
    # Get total count
    total = len(service.get_all(**filters))
    
    return ProjectListResponse(
        projects=projects,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a project by ID."""
    service = ProjectService(db)
    
    project = service.get_by_id_or_raise(project_id)
    
    # Check ownership
    if project.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this project")
    
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a project."""
    service = ProjectService(db)
    
    project = service.get_by_id_or_raise(project_id)
    
    # Check ownership
    if project.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this project")
    
    update_data = project_update.model_dump(exclude_unset=True)
    updated = service.update(project_id, update_data)
    
    return updated


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a project."""
    service = ProjectService(db)
    
    project = service.get_by_id_or_raise(project_id)
    
    # Check ownership
    if project.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this project")
    
    service.delete(project_id)
    return None


@router.post("/{project_id}/clone", response_model=ProjectResponse)
async def clone_project(
    project_id: str,
    new_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clone a project."""
    service = ProjectService(db)
    
    project = service.get_by_id_or_raise(project_id)
    
    # Check ownership
    if project.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this project")
    
    # Create clone
    clone_data = {
        "name": new_name or f"{project.name} (Copy)",
        "description": project.description,
        "owner_id": str(current_user.id),
    }
    
    cloned = service.create(clone_data)
    return cloned


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return None