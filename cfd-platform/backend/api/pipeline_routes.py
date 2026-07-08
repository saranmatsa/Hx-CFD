"""
Pipeline API Routes
REST API endpoints for CFD pipeline operations.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..integrations.pipeline.orchestrator import (
    CFDOrchestrator,
    PipelineConfig,
    PipelineStage,
    PipelineResult
)
from ..services.simulation_service import SimulationService

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# Global orchestrator instance
orchestrator: Optional[CFDOrchestrator] = None
executor = ThreadPoolExecutor(max_workers=4)

# Job tracking
jobs: Dict[str, Dict[str, Any]] = {}


def get_orchestrator() -> CFDOrchestrator:
    """Get or create orchestrator instance."""
    global orchestrator
    if orchestrator is None:
        orchestrator = CFDOrchestrator(
            work_dir="/tmp/cfd_pipeline",
            progress_callback=update_job_progress
        )
    return orchestrator


def update_job_progress(progress_list: List) -> None:
    """Callback to update job progress."""
    # This would update job status in a real implementation
    pass


# Request/Response Models
class PipelineParameters(BaseModel):
    """Parameters for pipeline execution."""
    mesh_size: float = Field(default=0.1, ge=0.001, le=1.0, description="Global mesh element size")
    repair_geometry: bool = Field(default=True, description="Enable geometry repair")
    boundary_layers: bool = Field(default=False, description="Add boundary layer meshing")
    first_layer_height: float = Field(default=0.001, ge=0.0001, le=0.1)
    num_boundary_layers: int = Field(default=5, ge=1, le=20)
    solver: str = Field(default="simpleFoam", description="OpenFOAM solver")
    end_time: float = Field(default=1000.0, ge=1.0)
    delta_t: float = Field(default=0.5, ge=0.0001)
    write_interval: float = Field(default=100.0, ge=1.0)
    color_field: str = Field(default="pressure", description="Field to visualize")
    cleanup_temp_files: bool = Field(default=True)


class PipelineStartRequest(BaseModel):
    """Request to start a pipeline job."""
    parameters: Optional[PipelineParameters] = None
    callback_url: Optional[str] = None


class PipelineStartResponse(BaseModel):
    """Response after starting a pipeline job."""
    job_id: str
    status: str
    message: str
    status_url: str


class JobStatusResponse(BaseModel):
    """Status of a pipeline job."""
    job_id: str
    status: str
    stages_completed: List[str]
    current_stage: Optional[str] = None
    progress: float
    errors: List[str]
    output_paths: Dict[str, str]
    execution_time: float
    created_at: datetime
    updated_at: datetime


class PipelineResultResponse(BaseModel):
    """Final result of a pipeline job."""
    job_id: str
    success: bool
    stages_completed: List[str]
    output_paths: Dict[str, str]
    errors: List[str]
    execution_time: float
    final_image: Optional[str]  # Base64 encoded


# Endpoints
@router.post("/start", response_model=PipelineStartResponse)
async def start_pipeline(
    request: PipelineStartRequest,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Start a new CFD pipeline job.
    
    Upload a STEP or IGES file to begin the automated pipeline:
    STEP → FreeCAD → Gmsh → OpenFOAM → VTK → Browser
    """
    job_id = str(uuid.uuid4())
    
    # Create upload directory
    upload_dir = "/tmp/cfd_pipeline/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save uploaded file
    input_path = os.path.join(upload_dir, f"{job_id}_{file.filename}")
    with open(input_path, "wb") as f:
        content = await file.read()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: f.write(content)
        )
    
    # Create job entry
    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "input_file": input_path,
        "parameters": request.parameters,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "stages_completed": [],
        "errors": [],
        "output_paths": {}
    }
    
    # Start pipeline in background
    background_tasks.add_task(run_pipeline_job, job_id, request.parameters)
    
    return PipelineStartResponse(
        job_id=job_id,
        status="queued",
        message=f"Pipeline job {job_id} created. Processing will begin shortly.",
        status_url=f"/api/pipeline/status/{job_id}"
    )


async def run_pipeline_job(job_id: str, parameters: Optional[PipelineParameters]):
    """Background task to run the pipeline."""
    job = jobs.get(job_id)
    if not job:
        return
    
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["updated_at"] = datetime.now()
        
        # Convert parameters to dict
        param_dict = parameters.dict() if parameters else {}
        
        # Create config
        config = PipelineConfig(
            mesh_size=param_dict.get("mesh_size", 0.1),
            repair_geometry=param_dict.get("repair_geometry", True),
            boundary_layers=param_dict.get("boundary_layers", False),
            first_layer_height=param_dict.get("first_layer_height", 0.001),
            num_boundary_layers=param_dict.get("num_boundary_layers", 5),
            solver=param_dict.get("solver", "simpleFoam"),
            end_time=param_dict.get("end_time", 1000.0),
            delta_t=param_dict.get("delta_t", 0.5),
            write_interval=param_dict.get("write_interval", 100.0),
            color_field=param_dict.get("color_field", "pressure"),
            cleanup_temp_files=param_dict.get("cleanup_temp_files", True)
        )
        
        # Run pipeline
        orch = CFDOrchestrator(
            config=config,
            work_dir="/tmp/cfd_pipeline"
        )
        
        result = await orch.run_pipeline(
            job_id=job_id,
            input_file=job["input_file"],
            output_dir="/tmp/cfd_pipeline/output",
            parameters=param_dict
        )
        
        # Update job with results
        jobs[job_id]["status"] = "completed" if result.success else "failed"
        jobs[job_id]["updated_at"] = datetime.now()
        jobs[job_id]["stages_completed"] = [s.value for s in result.stages_completed]
        jobs[job_id]["output_paths"] = result.output_paths
        jobs[job_id]["errors"] = result.errors
        jobs[job_id]["execution_time"] = result.execution_time
        jobs[job_id]["final_image"] = result.final_image
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["updated_at"] = datetime.now()
        jobs[job_id]["errors"].append(str(e))


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the current status of a pipeline job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Calculate progress
    total_stages = len(PipelineStage)
    completed_stages = len(job.get("stages_completed", []))
    progress = completed_stages / total_stages if total_stages > 0 else 0
    
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        stages_completed=job.get("stages_completed", []),
        current_stage=job.get("stages_completed", [None])[-1] if job.get("stages_completed") else None,
        progress=progress,
        errors=job.get("errors", []),
        output_paths=job.get("output_paths", {}),
        execution_time=job.get("execution_time", 0),
        created_at=job["created_at"],
        updated_at=job["updated_at"]
    )


@router.get("/result/{job_id}", response_model=PipelineResultResponse)
async def get_pipeline_result(job_id: str):
    """Get the final result of a completed pipeline job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job["status"] not in ["completed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is still {job['status']}"
        )
    
    return PipelineResultResponse(
        job_id=job_id,
        success=job["status"] == "completed",
        stages_completed=job.get("stages_completed", []),
        output_paths=job.get("output_paths", {}),
        errors=job.get("errors", []),
        execution_time=job.get("execution_time", 0),
        final_image=job.get("final_image")
    )


@router.get("/visualization/{job_id}")
async def get_visualization(job_id: str):
    """Get the visualization image for a completed job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    image_path = job.get("output_paths", {}).get("image")
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Visualization not available")
    
    return FileResponse(
        image_path,
        media_type="image/png",
        filename=f"visualization_{job_id}.png"
    )


@router.get("/mesh/{job_id}")
async def get_mesh_file(job_id: str):
    """Download the mesh file for a completed job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    mesh_path = job.get("output_paths", {}).get("mesh")
    if not mesh_path or not os.path.exists(mesh_path):
        raise HTTPException(status_code=404, detail="Mesh file not available")
    
    return FileResponse(
        mesh_path,
        media_type="application/octet-stream",
        filename=f"mesh_{job_id}.msh"
    )


@router.get("/case/{job_id}")
async def get_case_directory(job_id: str):
    """Get information about the OpenFOAM case directory."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    case_path = job.get("output_paths", {}).get("case")
    if not case_path or not os.path.exists(case_path):
        raise HTTPException(status_code=404, detail="Case directory not available")
    
    # List case contents
    case_contents = []
    for root, dirs, files in os.walk(case_path):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), case_path)
            case_contents.append(rel_path)
    
    return JSONResponse({
        "job_id": job_id,
        "case_path": case_path,
        "files": case_contents
    })


@router.post("/cancel/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running pipeline job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job["status"] not in ["queued", "running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job in {job['status']} state"
        )
    
    # In a real implementation, this would send a termination signal
    jobs[job_id]["status"] = "cancelled"
    jobs[job_id]["updated_at"] = datetime.now()
    jobs[job_id]["errors"].append("Job cancelled by user")
    
    return {"message": f"Job {job_id} cancellation requested"}


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """Delete a pipeline job and its outputs."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Remove output directory
    output_dir = "/tmp/cfd_pipeline/output"
    job_dir = os.path.join(output_dir, job_id)
    if os.path.exists(job_dir):
        import shutil
        shutil.rmtree(job_dir)
    
    # Remove from jobs dict
    del jobs[job_id]
    
    return {"message": f"Job {job_id} deleted"}


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List all pipeline jobs with optional filtering."""
    filtered_jobs = list(jobs.values())
    
    if status:
        filtered_jobs = [j for j in filtered_jobs if j["status"] == status]
    
    # Sort by creation time (newest first)
    filtered_jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Apply pagination
    total = len(filtered_jobs)
    filtered_jobs = filtered_jobs[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "jobs": [
            {
                "job_id": j["job_id"],
                "status": j["status"],
                "created_at": j["created_at"].isoformat(),
                "stages_completed": len(j.get("stages_completed", []))
            }
            for j in filtered_jobs
        ]
    }


@router.get("/stages")
async def get_pipeline_stages():
    """Get list of all pipeline stages."""
    return {
        "stages": [
            {
                "name": stage.value,
                "description": get_stage_description(stage)
            }
            for stage in PipelineStage
        ]
    }


def get_stage_description(stage: PipelineStage) -> str:
    """Get description for a pipeline stage."""
    descriptions = {
        PipelineStage.CAD_IMPORT: "Import STEP/IGES geometry using FreeCAD",
        PipelineStage.GEOMETRY_REPAIR: "Repair CAD geometry issues",
        PipelineStage.MESH_GENERATION: "Generate computational mesh using Gmsh",
        PipelineStage.CASE_SETUP: "Set up OpenFOAM case directory",
        PipelineStage.SIMULATION: "Run CFD solver",
        PipelineStage.POST_PROCESSING: "Convert results to VTK format",
        PipelineStage.VISUALIZATION: "Generate visualization images"
    }
    return descriptions.get(stage, "")


# Include in main app
def register_routes(app):
    """Register pipeline routes with FastAPI app."""
    app.include_router(router)