from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from core.database import get_db
from core.security import get_current_user
from db.models import User, Project, Mesh
from schemas.mesh import MeshCreate, MeshResponse, MeshConfig, MeshStatus
from services.mesh_service import MeshService

router = APIRouter(prefix="/meshes", tags=["meshes"])


@router.post("", response_model=MeshResponse, status_code=201)
async def create_mesh(
    mesh: MeshCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == mesh.project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db_mesh = Mesh(
        name=mesh.name,
        project_id=mesh.project_id,
        status=MeshStatus.PENDING.value
    )
    db.add(db_mesh)
    db.commit()
    db.refresh(db_mesh)
    
    return db_mesh


@router.get("/project/{project_id}", response_model=List[MeshResponse])
async def list_project_meshes(
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
    
    meshes = db.query(Mesh).filter(Mesh.project_id == project_id).all()
    return meshes


@router.get("/{mesh_id}", response_model=MeshResponse)
async def get_mesh(
    mesh_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    mesh = db.query(Mesh).join(Project).filter(
        Mesh.id == mesh_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not mesh:
        raise HTTPException(status_code=404, detail="Mesh not found")
    
    return mesh


@router.delete("/{mesh_id}", status_code=204)
async def delete_mesh(
    mesh_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    mesh = db.query(Mesh).join(Project).filter(
        Mesh.id == mesh_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not mesh:
        raise HTTPException(status_code=404, detail="Mesh not found")
    
    db.delete(mesh)
    db.commit()
    return None