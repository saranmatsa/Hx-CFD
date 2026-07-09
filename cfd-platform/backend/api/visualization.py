from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from core.database import get_db
from core.security import get_current_user
from db.models import User, Simulation
from schemas.visualization import (
    VisualizationData, VisualizationResponse, MeshDataPoint,
    ScalarFieldData, VectorFieldData
)
from backend.services.visualization_service import VisualizationService

router = APIRouter(prefix="/visualization", tags=["visualization"])


@router.get("/mesh/{simulation_id}")
async def get_mesh_visualization(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    simulation = db.query(Simulation).join(User).filter(
        Simulation.id == simulation_id
    ).first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    viz_service = VisualizationService()
    mesh_data = viz_service.get_mesh_geometry(simulation.case_path)
    
    return mesh_data


@router.get("/scalar/{simulation_id}")
async def get_scalar_field(
    simulation_id: str,
    field_name: str = "p",
    time_step: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    simulation = db.query(Simulation).join(User).filter(
        Simulation.id == simulation_id
    ).first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    viz_service = VisualizationService()
    scalar_data = viz_service.get_scalar_field(
        simulation.results_path,
        field_name,
        time_step
    )
    
    return scalar_data


@router.get("/vector/{simulation_id}")
async def get_vector_field(
    simulation_id: str,
    field_name: str = "U",
    time_step: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    simulation = db.query(Simulation).join(User).filter(
        Simulation.id == simulation_id
    ).first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    viz_service = VisualizationService()
    vector_data = viz_service.get_vector_field(
        simulation.results_path,
        field_name,
        time_step
    )
    
    return vector_data


@router.get("/residuals/{simulation_id}")
async def get_residuals(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    simulation = db.query(Simulation).join(User).filter(
        Simulation.id == simulation_id
    ).first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return {"residuals": simulation.residuals or []}


@router.get("/forces/{simulation_id}")
async def get_forces(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    simulation = db.query(Simulation).join(User).filter(
        Simulation.id == simulation_id
    ).first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return {"forces": simulation.forces or []}