"""
Optimization API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from core.security import get_current_user
from db.models import User
from schemas.optimization import OptimizationCreate, OptimizationUpdate, OptimizationResponse, OptimizationListResponse
from backend.services.base import OptimizationService
from backend.models.domain import OptimizationStatus, OptimizationAlgorithm
from backend.tasks.optimization_tasks import run_optimization, stop_optimization, apply_optimized_parameters, multi_objective_optimization

router = APIRouter(prefix="/optimizations", tags=["optimizations"])


@router.post("", response_model=OptimizationResponse, status_code=201)
async def create_optimization(
    optimization: OptimizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new optimization."""
    service = OptimizationService(db)
    
    opt_data = {
        "project_id": optimization.project_id,
        "simulation_id": optimization.simulation_id,
        "name": optimization.name,
        "description": optimization.description,
        "algorithm": optimization.algorithm,
        "parameters": optimization.parameters,
        "objectives": optimization.objectives,
        "constraints": optimization.constraints,
    }
    
    created = service.create(opt_data)
    return created


@router.get("", response_model=OptimizationListResponse)
async def list_optimizations(
    project_id: Optional[str] = None,
    simulation_id: Optional[str] = None,
    algorithm: Optional[OptimizationAlgorithm] = None,
    status: Optional[OptimizationStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all optimizations."""
    service = OptimizationService(db)
    
    # Build filters
    filters = {}
    if project_id:
        filters["project_id"] = project_id
    if simulation_id:
        filters["simulation_id"] = simulation_id
    if algorithm:
        filters["algorithm"] = algorithm
    if status:
        filters["status"] = status
    
    # Get paginated results
    skip = (page - 1) * page_size
    optimizations = service.get_all(skip=skip, limit=page_size, **filters)
    
    # Get total count
    total = len(service.get_all(**filters))
    
    return OptimizationListResponse(
        optimizations=optimizations,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{optimization_id}", response_model=OptimizationResponse)
async def get_optimization(
    optimization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get an optimization by ID."""
    service = OptimizationService(db)
    optimization = service.get_by_id_or_raise(optimization_id)
    return optimization


@router.patch("/{optimization_id}", response_model=OptimizationResponse)
async def update_optimization(
    optimization_id: str,
    optimization_update: OptimizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an optimization."""
    service = OptimizationService(db)
    
    update_data = optimization_update.model_dump(exclude_unset=True)
    updated = service.update(optimization_id, update_data)
    
    return updated


@router.delete("/{optimization_id}", status_code=204)
async def delete_optimization(
    optimization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an optimization."""
    service = OptimizationService(db)
    service.delete(optimization_id)
    return None


@router.post("/{optimization_id}/run")
async def trigger_optimization_run(
    optimization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger optimization run."""
    service = OptimizationService(db)
    
    optimization = service.get_by_id_or_raise(optimization_id)
    
    # Update optimization status to running
    service.update(optimization_id, {"status": OptimizationStatus.RUNNING})
    
    # Trigger Celery task
    task = run_optimization.delay(optimization_id)
    
    return {
        "task_id": task.id,
        "optimization_id": optimization_id,
        "status": "queued",
    }


@router.post("/{optimization_id}/stop")
async def stop_optimization_run(
    optimization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stop a running optimization."""
    service = OptimizationService(db)
    
    optimization = service.get_by_id_or_raise(optimization_id)
    
    # Trigger Celery task
    task = stop_optimization.delay(optimization_id)
    
    return {
        "task_id": task.id,
        "optimization_id": optimization_id,
        "status": "stopping",
    }


@router.post("/{optimization_id}/apply")
async def apply_optimized_params(
    optimization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply optimized parameters to simulation."""
    service = OptimizationService(db)
    
    optimization = service.get_by_id_or_raise(optimization_id)
    
    # Trigger Celery task
    task = apply_optimized_parameters.delay(optimization_id)
    
    return {
        "task_id": task.id,
        "optimization_id": optimization_id,
        "status": "applying",
    }


@router.post("/{optimization_id}/multi-objective")
async def run_multi_objective(
    optimization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run multi-objective optimization."""
    service = OptimizationService(db)
    
    optimization = service.get_by_id_or_raise(optimization_id)
    
    # Update optimization status to running
    service.update(optimization_id, {"status": OptimizationStatus.RUNNING})
    
    # Trigger Celery task
    task = multi_objective_optimization.delay(optimization_id)
    
    return {
        "task_id": task.id,
        "optimization_id": optimization_id,
        "status": "queued",
    }


@router.get("/{optimization_id}/history")
async def get_optimization_history(
    optimization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get optimization history (parameter history)."""
    service = OptimizationService(db)
    
    optimization = service.get_by_id_or_raise(optimization_id)
    
    # Return history from optimization data
    history = optimization.parameter_history or []
    
    return {
        "optimization_id": optimization_id,
        "history": history,
        "iteration_count": len(history),
    }


@router.get("/{optimization_id}/pareto")
async def get_pareto_front(
    optimization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Pareto front for multi-objective optimization."""
    service = OptimizationService(db)
    
    optimization = service.get_by_id_or_raise(optimization_id)
    
    # Return Pareto front from optimization data
    pareto_front = optimization.pareto_front or []
    
    return {
        "optimization_id": optimization_id,
        "pareto_front": pareto_front,
        "num_solutions": len(pareto_front),
    }