"""
Pipeline Orchestrator
Coordinates the full CFD pipeline: STEP → FreeCAD → Gmsh → OpenFOAM → VTK → Browser
"""

import os
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline execution stages."""
    CAD_IMPORT = "cad_import"
    GEOMETRY_REPAIR = "geometry_repair"
    MESH_GENERATION = "mesh_generation"
    CASE_SETUP = "case_setup"
    SIMULATION = "simulation"
    POST_PROCESSING = "post_processing"
    VISUALIZATION = "visualization"


@dataclass
class PipelineConfig:
    """Configuration for the CFD pipeline."""
    # FreeCAD settings
    repair_geometry: bool = True
    
    # Gmsh settings
    mesh_size: float = 0.1
    element_order: int = 1
    boundary_layers: bool = False
    first_layer_height: float = 0.001
    num_boundary_layers: int = 5
    
    # OpenFOAM settings
    solver: str = "simpleFoam"
    end_time: float = 1000.0
    delta_t: float = 0.5
    write_interval: float = 100.0
    
    # Visualization settings
    image_resolution: tuple = (800, 600)
    color_field: str = "pressure"
    
    # General
    cleanup_temp_files: bool = True


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    job_id: str
    stages_completed: List[PipelineStage] = field(default_factory=list)
    stage_results: Dict[str, Any] = field(default_factory=dict)
    output_paths: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    final_image: Optional[str] = None  # Base64 encoded


@dataclass
class StageProgress:
    """Progress information for a pipeline stage."""
    stage: PipelineStage
    status: str  # "pending", "running", "completed", "failed"
    progress: float  # 0.0 to 1.0
    message: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class PipelineCallbacks:
    """Callbacks for pipeline progress updates."""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
        self.stage_progress: Dict[PipelineStage, StageProgress] = {}
    
    def start_stage(self, stage: PipelineStage) -> None:
        """Mark a stage as started."""
        self.stage_progress[stage] = StageProgress(
            stage=stage,
            status="running",
            progress=0.0,
            message=f"Starting {stage.value}",
            start_time=datetime.now()
        )
        self._notify()
    
    def update_progress(self, stage: PipelineStage, progress: float, message: str) -> None:
        """Update stage progress."""
        if stage in self.stage_progress:
            self.stage_progress[stage].progress = progress
            self.stage_progress[stage].message = message
        self._notify()
    
    def complete_stage(self, stage: PipelineStage, result: Any) -> None:
        """Mark a stage as completed."""
        self.stage_progress[stage].status = "completed"
        self.stage_progress[stage].progress = 1.0
        self.stage_progress[stage].message = f"Completed {stage.value}"
        self.stage_progress[stage].end_time = datetime.now()
        self._notify()
    
    def fail_stage(self, stage: PipelineStage, error: str) -> None:
        """Mark a stage as failed."""
        self.stage_progress[stage].status = "failed"
        self.stage_progress[stage].message = error
        self.stage_progress[stage].end_time = datetime.now()
        self._notify()
    
    def _notify(self) -> None:
        """Send progress update via callback."""
        if self.progress_callback:
            self.progress_callback(list(self.stage_progress.values()))


class CFDOrchestrator:
    """
    Orchestrates the complete CFD pipeline.
    
    Pipeline flow:
    1. CAD Import (FreeCAD) - STEP/IGES → FCStd
    2. Geometry Repair (FreeCAD) - Fix CAD issues
    3. Mesh Generation (Gmsh) - CAD → Mesh
    4. Case Setup (OpenFOAM) - Mesh → Case
    5. Simulation (OpenFOAM) - Run solver
    6. Post-Processing (VTK) - Extract results
    7. Visualization (VTK) - Generate images
    """
    
    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        progress_callback: Optional[Callable] = None,
        work_dir: str = "/tmp/cfd_pipeline"
    ):
        self.config = config or PipelineConfig()
        self.callbacks = PipelineCallbacks(progress_callback)
        self.work_dir = work_dir
        
        # Initialize clients
        from ..freecad.client import FreeCADClient
        from ..gmsh.client import GmshClient
        from ..openfoam.client import OpenFOAMClient, SolverType
        from ..vtk.client import VTKClient
        
        self.freecad = FreeCADClient()
        self.gmsh = GmshClient()
        self.openfoam = OpenFOAMClient()
        self.vtk = VTKClient()
    
    async def run_pipeline(
        self,
        job_id: str,
        input_file: str,
        output_dir: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> PipelineResult:
        """
        Run the complete CFD pipeline.
        
        Args:
            job_id: Unique job identifier
            input_file: Path to input STEP/IGES file
            output_dir: Directory for all outputs
            parameters: Optional pipeline parameters
            
        Returns:
            PipelineResult with all stage results
        """
        import time
        start_time = time.time()
        
        result = PipelineResult(success=True, job_id=job_id)
        
        # Create job directory
        job_dir = os.path.join(output_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        # Update config with parameters
        if parameters:
            self._update_config(parameters)
        
        try:
            # Stage 1: CAD Import
            self.callbacks.start_stage(PipelineStage.CAD_IMPORT)
            cad_result = await self._run_cad_import(input_file, job_dir)
            if cad_result["success"]:
                self.callbacks.complete_stage(PipelineStage.CAD_IMPORT, cad_result)
                result.stages_completed.append(PipelineStage.CAD_IMPORT)
                result.stage_results["cad_import"] = cad_result
                result.output_paths["geometry"] = cad_result["output_path"]
            else:
                self.callbacks.fail_stage(PipelineStage.CAD_IMPORT, cad_result.get("error", "Unknown error"))
                result.errors.append(f"CAD Import failed: {cad_result.get('error')}")
                result.success = False
            
            if not result.success:
                return result
            
            # Stage 2: Geometry Repair (optional)
            if self.config.repair_geometry:
                self.callbacks.start_stage(PipelineStage.GEOMETRY_REPAIR)
                repair_result = await self._run_geometry_repair(cad_result["output_path"], job_dir)
                if repair_result["success"]:
                    self.callbacks.complete_stage(PipelineStage.GEOMETRY_REPAIR, repair_result)
                    result.stages_completed.append(PipelineStage.GEOMETRY_REPAIR)
                    result.stage_results["geometry_repair"] = repair_result
                    result.output_paths["repaired_geometry"] = repair_result["output_path"]
                else:
                    self.callbacks.fail_stage(PipelineStage.GEOMETRY_REPAIR, repair_result.get("error", "Unknown"))
                    result.errors.append(f"Geometry repair failed: {repair_result.get('error')}")
                    # Continue anyway - repair is optional
            
            # Stage 3: Mesh Generation
            self.callbacks.start_stage(PipelineStage.MESH_GENERATION)
            geometry_path = result.output_paths.get("repaired_geometry", cad_result["output_path"])
            mesh_result = await self._run_mesh_generation(geometry_path, job_dir)
            if mesh_result["success"]:
                self.callbacks.complete_stage(PipelineStage.MESH_GENERATION, mesh_result)
                result.stages_completed.append(PipelineStage.MESH_GENERATION)
                result.stage_results["mesh_generation"] = mesh_result
                result.output_paths["mesh"] = mesh_result["mesh_path"]
            else:
                self.callbacks.fail_stage(PipelineStage.MESH_GENERATION, mesh_result.get("error", "Unknown"))
                result.errors.append(f"Mesh generation failed: {mesh_result.get('error')}")
                result.success = False
            
            if not result.success:
                return result
            
            # Stage 4: Case Setup
            self.callbacks.start_stage(PipelineStage.CASE_SETUP)
            case_result = await self._run_case_setup(mesh_result["mesh_path"], job_dir)
            if case_result["success"]:
                self.callbacks.complete_stage(PipelineStage.CASE_SETUP, case_result)
                result.stages_completed.append(PipelineStage.CASE_SETUP)
                result.stage_results["case_setup"] = case_result
                result.output_paths["case"] = case_result["case_dir"]
            else:
                self.callbacks.fail_stage(PipelineStage.CASE_SETUP, case_result.get("error", "Unknown"))
                result.errors.append(f"Case setup failed: {case_result.get('error')}")
                result.success = False
            
            if not result.success:
                return result
            
            # Stage 5: Simulation
            self.callbacks.start_stage(PipelineStage.SIMULATION)
            sim_result = await self._run_simulation(case_result["case_dir"], job_dir)
            if sim_result["success"]:
                self.callbacks.complete_stage(PipelineStage.SIMULATION, sim_result)
                result.stages_completed.append(PipelineStage.SIMULATION)
                result.stage_results["simulation"] = sim_result
            else:
                self.callbacks.fail_stage(PipelineStage.SIMULATION, sim_result.get("error", "Unknown"))
                result.errors.append(f"Simulation failed: {sim_result.get('error')}")
                result.success = False
            
            if not result.success:
                return result
            
            # Stage 6: Post-Processing
            self.callbacks.start_stage(PipelineStage.POST_PROCESSING)
            post_result = await self._run_post_processing(case_result["case_dir"], job_dir)
            if post_result["success"]:
                self.callbacks.complete_stage(PipelineStage.POST_PROCESSING, post_result)
                result.stages_completed.append(PipelineStage.POST_PROCESSING)
                result.stage_results["post_processing"] = post_result
                result.output_paths["vtk"] = post_result["vtk_dir"]
            else:
                self.callbacks.fail_stage(PipelineStage.POST_PROCESSING, post_result.get("error", "Unknown"))
                result.errors.append(f"Post-processing failed: {post_result.get('error')}")
                # Continue anyway - visualization can still work
            
            # Stage 7: Visualization
            self.callbacks.start_stage(PipelineStage.VISUALIZATION)
            viz_result = await self._run_visualization(post_result.get("vtk_dir", ""), job_dir)
            if viz_result["success"]:
                self.callbacks.complete_stage(PipelineStage.VISUALIZATION, viz_result)
                result.stages_completed.append(PipelineStage.VISUALIZATION)
                result.stage_results["visualization"] = viz_result
                result.output_paths["image"] = viz_result["image_path"]
                result.final_image = viz_result.get("image_data")
            else:
                self.callbacks.fail_stage(PipelineStage.VISUALIZATION, viz_result.get("error", "Unknown"))
                result.errors.append(f"Visualization failed: {viz_result.get('error')}")
            
            # Cleanup
            if self.config.cleanup_temp_files:
                self._cleanup_temp_files(job_dir)
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            result.success = False
            result.errors.append(str(e))
        
        result.execution_time = time.time() - start_time
        
        # Save result
        self._save_result(result, job_dir)
        
        return result
    
    def _update_config(self, parameters: Dict[str, Any]) -> None:
        """Update pipeline configuration with parameters."""
        if "mesh_size" in parameters:
            self.config.mesh_size = parameters["mesh_size"]
        if "solver" in parameters:
            self.config.solver = parameters["solver"]
        if "end_time" in parameters:
            self.config.end_time = parameters["end_time"]
        if "repair_geometry" in parameters:
            self.config.repair_geometry = parameters["repair_geometry"]
        if "boundary_layers" in parameters:
            self.config.boundary_layers = parameters["boundary_layers"]
    
    async def _run_cad_import(self, input_file: str, job_dir: str) -> Dict[str, Any]:
        """Run CAD import stage."""
        self.callbacks.update_progress(PipelineStage.CAD_IMPORT, 0.5, "Importing CAD geometry...")
        
        output_dir = os.path.join(job_dir, "cad")
        os.makedirs(output_dir, exist_ok=True)
        
        result = self.freecad.import_step(input_file, output_dir)
        
        return {
            "success": result.success,
            "output_path": result.output_path,
            "error": result.error_message,
            "bounding_box": result.bounding_box,
            "volume": result.volume
        }
    
    async def _run_geometry_repair(self, geometry_path: str, job_dir: str) -> Dict[str, Any]:
        """Run geometry repair stage."""
        self.callbacks.update_progress(PipelineStage.GEOMETRY_REPAIR, 0.5, "Repairing geometry...")
        
        output_dir = os.path.join(job_dir, "cad")
        os.makedirs(output_dir, exist_ok=True)
        
        result = self.freecad.repair_geometry(geometry_path, output_dir)
        
        return {
            "success": result.success,
            "output_path": result.output_path,
            "error": result.error_message
        }
    
    async def _run_mesh_generation(self, geometry_path: str, job_dir: str) -> Dict[str, Any]:
        """Run mesh generation stage."""
        self.callbacks.update_progress(PipelineStage.MESH_GENERATION, 0.3, "Generating mesh...")
        
        output_dir = os.path.join(job_dir, "mesh")
        os.makedirs(output_dir, exist_ok=True)
        
        mesh_config = {
            "mesh_size": self.config.mesh_size,
            "element_order": self.config.element_order
        }
        
        result = self.gmsh.generate_mesh(geometry_path, output_dir, mesh_config)
        
        if result.success and self.config.boundary_layers:
            self.callbacks.update_progress(PipelineStage.MESH_GENERATION, 0.6, "Adding boundary layers...")
            bl_result = self.gmsh.create_boundary_layer_mesh(
                geometry_path, output_dir,
                first_layer_height=self.config.first_layer_height,
                layers=self.config.num_boundary_layers
            )
            if bl_result.success:
                result = bl_result
        
        return {
            "success": result.success,
            "mesh_path": result.mesh_path,
            "error": result.error_message,
            "element_count": result.element_count,
            "node_count": result.node_count,
            "mesh_stats": result.mesh_stats
        }
    
    async def _run_case_setup(self, mesh_path: str, job_dir: str) -> Dict[str, Any]:
        """Run OpenFOAM case setup stage."""
        self.callbacks.update_progress(PipelineStage.CASE_SETUP, 0.5, "Setting up OpenFOAM case...")
        
        from ..openfoam.client import SolverType
        
        solver_map = {
            "simpleFoam": SolverType.INCOMPRESSIBLE_SIMPLE,
            "pisoFoam": SolverType.INCOMPRESSIBLE_PISO,
            "pimpleFoam": SolverType.INCOMPRESSIBLE_PIMPLE,
            "rhoCentralFoam": SolverType.COMPRESSIBLE,
            "interFoam": SolverType.MULTIPHASE
        }
        
        solver_type = solver_map.get(self.config.solver, SolverType.INCOMPRESSIBLE_SIMPLE)
        
        from ..openfoam.client import SolverConfig
        solver_config = SolverConfig(
            solver=solver_type,
            end_time=self.config.end_time,
            delta_t=self.config.delta_t,
            write_interval=self.config.write_interval
        )
        
        case_dir = self.openfoam.create_case(
            "cfd_case",
            mesh_path,
            job_dir,
            solver_config
        )
        
        return {
            "success": True,
            "case_dir": case_dir
        }
    
    async def _run_simulation(self, case_dir: str, job_dir: str) -> Dict[str, Any]:
        """Run OpenFOAM simulation stage."""
        self.callbacks.update_progress(PipelineStage.SIMULATION, 0.1, "Starting simulation...")
        
        from ..openfoam.client import SolverConfig, SolverType
        
        solver_map = {
            "simpleFoam": SolverType.INCOMPRESSIBLE_SIMPLE,
            "pisoFoam": SolverType.INCOMPRESSIBLE_PISO,
            "pimpleFoam": SolverType.INCOMPRESSIBLE_PIMPLE
        }
        
        solver_config = SolverConfig(
            solver=solver_map.get(self.config.solver, SolverType.INCOMPRESSIBLE_SIMPLE),
            end_time=self.config.end_time
        )
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.openfoam.run_simulation(case_dir, solver_config)
        )
        
        return {
            "success": result.success,
            "case_dir": result.case_dir,
            "error": result.error_message,
            "iterations": result.iterations,
            "final_residuals": result.final_residuals,
            "runtime_seconds": result.runtime_seconds
        }
    
    async def _run_post_processing(self, case_dir: str, job_dir: str) -> Dict[str, Any]:
        """Run VTK post-processing stage."""
        self.callbacks.update_progress(PipelineStage.POST_PROCESSING, 0.5, "Converting to VTK format...")
        
        output_dir = os.path.join(job_dir, "post")
        os.makedirs(output_dir, exist_ok=True)
        
        vtk_dir = self.vtk.convert_openfoam_to_vtk(case_dir, output_dir)
        
        return {
            "success": True,
            "vtk_dir": vtk_dir
        }
    
    async def _run_visualization(self, vtk_dir: str, job_dir: str) -> Dict[str, Any]:
        """Run visualization stage."""
        self.callbacks.update_progress(PipelineStage.VISUALIZATION, 0.3, "Generating visualization...")
        
        # Find VTK file
        vtk_files = list(Path(vtk_dir).glob("*.vtk")) if vtk_dir else []
        
        if vtk_files:
            vtk_file = str(vtk_files[0])
        else:
            # Create placeholder
            vtk_file = os.path.join(vtk_dir or job_dir, "results.vtk")
            self.vtk._create_placeholder_vtk(os.path.dirname(vtk_file))
        
        output_path = os.path.join(job_dir, "visualization.png")
        
        result = self.vtk.generate_image(
            vtk_file,
            output_path,
            field_name=self.config.color_field,
            color_range=None
        )
        
        return {
            "success": result.success,
            "image_path": result.output_path,
            "image_data": result.image_data,
            "error": result.error_message
        }
    
    def _cleanup_temp_files(self, job_dir: str) -> None:
        """Remove temporary files after pipeline completion."""
        temp_patterns = ["*.py", "*.geo", "*.log"]
        for pattern in temp_patterns:
            for f in Path(job_dir).rglob(pattern):
                try:
                    os.remove(f)
                except Exception:
                    pass
    
    def _save_result(self, result: PipelineResult, job_dir: str) -> None:
        """Save pipeline result to JSON file."""
        result_file = os.path.join(job_dir, "pipeline_result.json")
        
        result_dict = {
            "success": result.success,
            "job_id": result.job_id,
            "stages_completed": [s.value for s in result.stages_completed],
            "output_paths": result.output_paths,
            "errors": result.errors,
            "execution_time": result.execution_time,
            "stage_results": {}
        }
        
        # Convert stage results to serializable format
        for stage, stage_result in result.stage_results.items():
            if hasattr(stage_result, '__dict__'):
                result_dict["stage_results"][stage] = stage_result.__dict__
            else:
                result_dict["stage_results"][stage] = stage_result
        
        with open(result_file, 'w') as f:
            json.dump(result_dict, f, indent=2, default=str)
    
    def get_pipeline_status(self, job_id: str, output_dir: str) -> Optional[Dict[str, Any]]:
        """Get current status of a pipeline job."""
        result_file = os.path.join(output_dir, job_id, "pipeline_result.json")
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                return json.load(f)
        return None