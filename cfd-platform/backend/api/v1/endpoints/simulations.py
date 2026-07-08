"""
Simulation API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from core.security import get_current_user
from db.models import User
from schemas.simulation import SimulationCreate, SimulationUpdate, SimulationResponse, SimulationListResponse
from backend.services.base import SimulationService
from backend.models.domain import SolverType, SimulationStatus
from backend.tasks.simulation_tasks import run_simulation, stop_simulation, extract_results, post_process

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=SimulationResponse, status_code=201)
async def create_simulation(
    simulation: SimulationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new simulation."""
    service = SimulationService(db)
    
    sim_data = {
        "project_id": simulation.project_id,
        "mesh_id": simulation.mesh_id,
        "name": simulation.name,
        "description": simulation.description,
        "solver_type": simulation.solver_type,
        "config": simulation.config,
    }
    
    created = service.create(sim_data)
    return created


@router.get("", response_model=SimulationListResponse)
async def list_simulations(
    project_id: Optional[str] = None,
    mesh_id: Optional[str] = None,
    solver_type: Optional[SolverType] = None,
    status: Optional[SimulationStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all simulations."""
    service = SimulationService(db)
    
    # Build filters
    filters = {}
    if project_id:
        filters["project_id"] = project_id
    if mesh_id:
        filters["mesh_id"] = mesh_id
    if solver_type:
        filters["solver_type"] = solver_type
    if status:
        filters["status"] = status
    
    # Get paginated results
    skip = (page - 1) * page_size
    simulations = service.get_all(skip=skip, limit=page_size, **filters)
    
    # Get total count
    total = len(service.get_all(**filters))
    
    return SimulationListResponse(
        simulations=simulations,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a simulation by ID."""
    service = SimulationService(db)
    simulation = service.get_by_id_or_raise(simulation_id)
    return simulation


@router.patch("/{simulation_id}", response_model=SimulationResponse)
async def update_simulation(
    simulation_id: str,
    simulation_update: SimulationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a simulation."""
    service = SimulationService(db)
    
    update_data = simulation_update.model_dump(exclude_unset=True)
    updated = service.update(simulation_id, update_data)
    
    return updated


@router.delete("/{simulation_id}", status_code=204)
async def delete_simulation(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a simulation."""
    service = SimulationService(db)
    service.delete(simulation_id)
    return None


@router.post("/{simulation_id}/run")
async def trigger_simulation_run(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger simulation run."""
    service = SimulationService(db)
    
    simulation = service.get_by_id_or_raise(simulation_id)
    
    # Update simulation status to running
    service.update(simulation_id, {"status": SimulationStatus.RUNNING})
    
    # Trigger Celery task
    task = run_simulation.delay(simulation_id)
    
    return {
        "task_id": task.id,
        "simulation_id": simulation_id,
        "status": "queued",
    }


@router.post("/{simulation_id}/stop")
async def stop_simulation_run(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stop a running simulation."""
    service = SimulationService(db)
    
    simulation = service.get_by_id_or_raise(simulation_id)
    
    # Trigger Celery task
    task = stop_simulation.delay(simulation_id)
    
    return {
        "task_id": task.id,
        "simulation_id": simulation_id,
        "status": "stopping",
    }


@router.post("/{simulation_id}/extract-results")
async def extract_simulation_results(
    simulation_id: str,
    fields: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract results from a completed simulation."""
    service = SimulationService(db)
    
    simulation = service.get_by_id_or_raise(simulation_id)
    
    # Trigger Celery task
    task = extract_results.delay(simulation_id, fields)
    
    return {
        "task_id": task.id,
        "simulation_id": simulation_id,
        "status": "processing",
    }


@router.post("/{simulation_id}/post-process")
async def post_process_simulation(
    simulation_id: str,
    operations: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Post-process simulation results."""
    service = SimulationService(db)
    
    simulation = service.get_by_id_or_raise(simulation_id)
    
    # Trigger Celery task
    task = post_process.delay(simulation_id, operations)
    
    return {
        "task_id": task.id,
        "simulation_id": simulation_id,
        "operations": operations,
        "status": "processing",
    }


@router.get("/{simulation_id}/residuals")
async def get_simulation_residuals(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get simulation residuals history."""
    service = SimulationService(db)
    
    simulation = service.get_by_id_or_raise(simulation_id)
    
    # Return residuals from simulation data
    residuals = simulation.residuals or {}
    
    return {
        "simulation_id": simulation_id,
        "residuals": residuals,
    }