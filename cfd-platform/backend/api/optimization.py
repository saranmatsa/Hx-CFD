from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core.security import get_current_user
from db.models import User, Project, Simulation
from schemas.optimization import (
    OptimizationCreate, OptimizationResponse, OptimizationConfig,
    OptimizationStatus, OptimizationResult
)
from services.optimization_service import OptimizationService

router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.post("", response_model=OptimizationResponse, status_code=201)
async def create_optimization(
    optimization: OptimizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == optimization.project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    simulation = db.query(Simulation).filter(
        Simulation.id == optimization.simulation_id,
        Simulation.project_id == project.id
    ).first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    opt_service = OptimizationService()
    opt_result = opt_service.create_optimization(
        name=optimization.name,
        project_id=optimization.project_id,
        simulation_id=optimization.simulation_id,
        config=optimization.config
    )
    
    return opt_result


@router.get("/project/{project_id}", response_model=List[OptimizationResponse])
async def list_project_optimizations(
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
    
    return []


@router.get("/{optimization_id}", response_model=OptimizationResponse)
async def get_optimization(
    optimization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return {"id": optimization_id, "name": "placeholder"}


@router.post("/{optimization_id}/start")
async def start_optimization(
    optimization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return {"message": "Optimization started", "optimization_id": optimization_id}


@router.delete("/{optimization_id}", status_code=204)
async def delete_optimization(
    optimization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return None