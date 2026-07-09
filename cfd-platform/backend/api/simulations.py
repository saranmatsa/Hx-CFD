from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from core.security import get_current_user
from db.models import User, Project, Simulation
from schemas.simulation import (
    SimulationCreate, SimulationResponse, SimulationConfig, SimulationStatus
)
from backend.services.simulation_service import SimulationService

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=SimulationResponse, status_code=201)
async def create_simulation(
    simulation: SimulationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == simulation.project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db_simulation = Simulation(
        name=simulation.name,
        project_id=simulation.project_id,
        mesh_id=simulation.mesh_id,
        solver=simulation.solver.value,
        status=SimulationStatus.PENDING.value
    )
    db.add(db_simulation)
    db.commit()
    db.refresh(db_simulation)
    
    return db_simulation


@router.get("/project/{project_id}", response_model=List[SimulationResponse])
async def list_project_simulations(
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
    
    simulations = db.query(Simulation).filter(
        Simulation.project_id == project_id
    ).all()
    return simulations


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    simulation = db.query(Simulation).join(Project).filter(
        Simulation.id == simulation_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return simulation


@router.post("/{simulation_id}/start")
async def start_simulation(
    simulation_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    simulation = db.query(Simulation).join(Project).filter(
        Simulation.id == simulation_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    if simulation.status == SimulationStatus.RUNNING.value:
        raise HTTPException(status_code=400, detail="Simulation already running")
    
    simulation.status = SimulationStatus.RUNNING.value
    db.commit()
    
    return {"message": "Simulation started", "simulation_id": simulation_id}


@router.post("/{simulation_id}/stop")
async def stop_simulation(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    simulation = db.query(Simulation).join(Project).filter(
        Simulation.id == simulation_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    simulation.status = SimulationStatus.CANCELLED.value
    db.commit()
    
    return {"message": "Simulation stopped", "simulation_id": simulation_id}


@router.delete("/{simulation_id}", status_code=204)
async def delete_simulation(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    simulation = db.query(Simulation).join(Project).filter(
        Simulation.id == simulation_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    db.delete(simulation)
    db.commit()
    return None