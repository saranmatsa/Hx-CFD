"""
Simulation Service for CFD Backend.

Provides business logic for running, monitoring, and managing CFD simulations.
"""

import asyncio
import logging
import os
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cfd_backend.models.project import (
    Project,
    Simulation,
    SimulationStatus,
    SimulationType,
    TurbulenceModel,
)
from cfd_backend.models.mesh import Mesh, MeshStatus

logger = logging.getLogger(__name__)


class SimulationService:
    """Service for simulation operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._running_simulations: Dict[uuid.UUID, asyncio.Task] = {}
        self._simulation_processes: Dict[uuid.UUID, subprocess.Popen] = {}
    
    async def run_simulation(
        self,
        simulation_id: uuid.UUID,
        solver: str = "openfoam",
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Run CFD simulation.
        
        Args:
            simulation_id: ID of the simulation to run
            solver: Solver to use (openfoam, su2, fluent, etc.)
            config: Additional solver configuration
        """
        # Get simulation with relationships
        result = await self.db.execute(
            select(Simulation)
            .options(
                selectinload(Simulation.project),
                selectinload(Simulation.mesh),
            )
            .where(Simulation.id == simulation_id)
        )
        simulation = result.scalar_one_or_none()
        
        if not simulation:
            logger.error(f"Simulation {simulation_id} not found")
            return
        
        if simulation.status in [SimulationStatus.RUNNING, SimulationStatus.QUEUED]:
            logger.warning(f"Simulation {simulation_id} already running")
            return
        
        try:
            # Update status
            simulation.status = SimulationStatus.QUEUED
            await self.db.commit()
            
            # Prepare simulation directory
            sim_dir = await self._prepare_simulation_directory(simulation, config)
            
            # Update status to running
            simulation.status = SimulationStatus.RUNNING
            simulation.started_at = datetime.utcnow()
            await self.db.commit()
            
            # Run simulation based on solver
            if solver.lower() == "openfoam":
                await self._run_openfoam_simulation(simulation, sim_dir, config)
            elif solver.lower() == "su2":
                await self._run_su2_simulation(simulation, sim_dir, config)
            else:
                raise ValueError(f"Unsupported solver: {solver}")
            
            # Update completion status
            simulation.status = SimulationStatus.COMPLETED
            simulation.completed_at = datetime.utcnow()
            if simulation.started_at:
                simulation.duration_seconds = (
                    simulation.completed_at - simulation.started_at
                ).total_seconds()
            
            # Collect results
            await self._collect_results(simulation, sim_dir)
            
        except asyncio.CancelledError:
            simulation.status = SimulationStatus.CANCELLED
            simulation.completed_at = datetime.utcnow()
            if simulation.started_at:
                simulation.duration_seconds = (
                    simulation.completed_at - simulation.started_at
                ).total_seconds()
            await self.db.commit()
            raise
        except Exception as e:
            logger.exception(f"Simulation {simulation_id} failed: {e}")
            simulation.status = SimulationStatus.FAILED
            simulation.error_message = str(e)
            simulation.completed_at = datetime.utcnow()
            if simulation.started_at:
                simulation.duration_seconds = (
                    simulation.completed_at - simulation.started_at
                ).total_seconds()
            await self.db.commit()
        finally:
            self._running_simulations.pop(simulation_id, None)
            self._simulation_processes.pop(simulation_id, None)
    
    async def _prepare_simulation_directory(
        self,
        simulation: Simulation,
        config: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Prepare simulation working directory with all necessary files."""
        # Create simulation directory
        base_dir = Path(config.get("base_dir", "/tmp/cfd_simulations")) if config else Path("/tmp/cfd_simulations")
        sim_dir = base_dir / str(simulation.project_id) / str(simulation.id)
        sim_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy mesh file if available
        if simulation.mesh and simulation.mesh.file_path:
            mesh_src = Path(simulation.mesh.file_path)
            if mesh_src.exists():
                mesh_dst = sim_dir / f"mesh{mesh_src.suffix}"
                shutil.copy2(mesh_src, mesh_dst)
        
        # Generate OpenFOAM case files
        await self._generate_openfoam_case(simulation, sim_dir, config)
        
        return sim_dir
    
    async def _generate_openfoam_case(
        self,
        simulation: Simulation,
        sim_dir: Path,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Generate OpenFOAM case directory structure."""
        # Create directory structure
        (sim_dir / "system").mkdir(exist_ok=True)
        (sim_dir / "constant").mkdir(exist_ok=True)
        (sim_dir / "constant" / "polyMesh").mkdir(exist_ok=True)
        (sim_dir / "0").mkdir(exist_ok=True)
        
        # Generate controlDict
        control_dict = self._generate_control_dict(simulation, config)
        (sim_dir / "system" / "controlDict").write_text(control_dict)
        
        # Generate fvSchemes
        fv_schemes = self._generate_fv_schemes(simulation, config)
        (sim_dir / "system" / "fvSchemes").write_text(fv_schemes)
        
        # Generate fvSolution
        fv_solution = self._generate_fv_solution(simulation, config)
        (sim_dir / "system" / "fvSolution").write_text(fv_solution)
        
        # Generate transportProperties
        transport_props = self._generate_transport_properties(simulation, config)
        (sim_dir / "constant" / "transportProperties").write_text(transport_props)
        
        # Generate turbulenceProperties
        turb_props = self._generate_turbulence_properties(simulation, config)
        (sim_dir / "constant" / "turbulenceProperties").write_text(turb_props)
        
        # Generate boundary conditions (0/ directory)
        await self._generate_boundary_conditions(simulation, sim_dir, config)
        
        # Copy mesh to constant/polyMesh if available
        if simulation.mesh and simulation.mesh.file_path:
            mesh_src = Path(simulation.mesh.file_path)
            if mesh_src.exists() and mesh_src.suffix == ".msh":
                # Convert GMSH to OpenFOAM format
                await self._convert_gmsh_to_openfoam(mesh_src, sim_dir / "constant" / "polyMesh")
    
    def _generate_control_dict(
        self,
        simulation: Simulation,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate OpenFOAM controlDict."""
        project = simulation.project
        time_settings = project.time_settings if project else {}
        solver_settings = project.solver_settings if project else {}
        
        start_time = time_settings.get("start_time", 0)
        end_time = time_settings.get("end_time", 1000)
        delta_t = time_settings.get("delta_t", 1)
        write_interval = time_settings.get("write_interval", 100)
        
        return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}}

application     {solver_settings.get("solver", "simpleFoam")};
startFrom       startTime;
startTime       {start_time};
stopAt          endTime;
endTime         {end_time};
deltaT          {delta_t};
writeControl    timeStep;
writeInterval   {write_interval};
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

functions
{{
    forces
    {{
        type            forces;
        libs            ("libforces.so");
        writeControl    timeStep;
        writeInterval   {write_interval};
        patches         (wall);
        rhoName         rhoInf;
        rhoInf          1;
        CofR            (0 0 0);
    }}
    
    yPlus
    {{
        type            yPlus;
        libs            ("libfieldFunctionObjects.so");
        writeControl    timeStep;
        writeInterval   {write_interval};
    }}
}}
"""
    
    def _generate_fv_schemes(
        self,
        simulation: Simulation,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate OpenFOAM fvSchemes."""
        return """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}

ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
    grad(p)         Gauss linear;
    grad(U)         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      Gauss upwind;
    div(phi,k)      Gauss upwind;
    div(phi,omega)  Gauss upwind;
    div(phi,epsilon) Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

wallDist
{
    method          meshWave;
}
"""
    
    def _generate_fv_solution(
        self,
        simulation: Simulation,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate OpenFOAM fvSolution."""
        solver_settings = simulation.project.solver_settings if simulation.project else {}
        n_correctors = solver_settings.get("n_correctors", 2)
        n_non_orthogonal = solver_settings.get("n_non_orthogonal_correctors", 0)
        
        return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}}

solvers
{{
    p
    {{
        solver          GAMG;
        tolerance       1e-07;
        relTol          0.01;
        smoother        GaussSeidel;
        nPreSweeps      0;
        nPostSweeps     2;
        cacheAgglomeration true;
        nCellsInCoarsestLevel 10;
        agglomerator    faceAreaPair;
        mergeLevels     1;
    }}
    
    "(U|k|omega|epsilon)"
    {{
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-07;
        relTol          0.1;
        nSweeps         1;
    }}
}}

SIMPLE
{{
    nNonOrthogonalCorrectors {n_non_orthogonal};
    consistent      yes;
    residualControl
    {{
        p               1e-4;
        U               1e-4;
        "(k|omega|epsilon)" 1e-4;
    }}
}}

relaxationFactors
{{
    equations
    {{
        p               0.3;
        U               0.7;
        k               0.7;
        omega           0.7;
        epsilon         0.7;
    }}
}}
"""
    
    def _generate_transport_properties(
        self,
        simulation: Simulation,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate OpenFOAM transportProperties."""
        physics = simulation.project.physics_settings if simulation.project else {}
        nu = physics.get("kinematic_viscosity", 1.5e-5)
        
        return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      transportProperties;
}}

transportModel  Newtonian;
nu              nu [0 2 -1 0 0 0 0] {nu};
"""
    
    def _generate_turbulence_properties(
        self,
        simulation: Simulation,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate OpenFOAM turbulenceProperties."""
        project = simulation.project
        turb_model = project.turbulence_model if project else TurbulenceModel.K_OMEGA_SST
        
        model_map = {
            TurbulenceModel.K_EPSILON: "kEpsilon",
            TurbulenceModel.K_OMEGA: "kOmega",
            TurbulenceModel.K_OMEGA_SST: "kOmegaSST",
            TurbulenceModel.SPALART_ALLMARAS: "SpalartAllmaras",
            TurbulenceModel.REALIZABLE_K_EPSILON: "realizableKEpsilon",
            TurbulenceModel.RNG_K_EPSILON: "RNGkEpsilon",
            TurbulenceModel.LES: "LES",
            TurbulenceModel.DES: "DES",
        }
        
        model_name = model_map.get(turb_model, "kOmegaSST")
        
        return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}}

simulationType  RAS;

RAS
{{
    RASModel        {model_name};
    turbulence      on;
    printCoeffs     on;
}}
"""
    
    async def _generate_boundary_conditions(
        self,
        simulation: Simulation,
        sim_dir: Path,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Generate boundary condition files in 0/ directory."""
        bc = simulation.project.boundary_conditions if simulation.project else {}
        ic = simulation.project.initial_conditions if simulation.project else {}
        
        # Default values
        default_p = ic.get("pressure", 0)
        default_u = ic.get("velocity", [0, 0, 0])
        default_k = ic.get("k", 0.01)
        default_omega = ic.get("omega", 10)
        default_nut = ic.get("nut", 0)
        
        # Create boundary condition files
        patches = bc.get("patches", {})
        
        # p file
        p_content = self._generate_field_file("p", "scalar", default_p, patches.get("p", {}))
        (sim_dir / "0" / "p").write_text(p_content)
        
        # U file
        u_content = self._generate_field_file("U", "vector", default_u, patches.get("U", {}))
        (sim_dir / "0" / "U").write_text(u_content)
        
        # k file (for turbulence)
        k_content = self._generate_field_file("k", "scalar", default_k, patches.get("k", {}))
        (sim_dir / "0" / "k").write_text(k_content)
        
        # omega file
        omega_content = self._generate_field_file("omega", "scalar", default_omega, patches.get("omega", {}))
        (sim_dir / "0" / "omega").write_text(omega_content)
        
        # nut file
        nut_content = self._generate_field_file("nut", "scalar", default_nut, patches.get("nut", {}))
        (sim_dir / "0" / "nut").write_text(nut_content)
        
        # epsilon file (for k-epsilon models)
        epsilon_content = self._generate_field_file("epsilon", "scalar", ic.get("epsilon", 0.1), patches.get("epsilon", {}))
        (sim_dir / "0" / "epsilon").write_text(epsilon_content)
    
    def _generate_field_file(
        self,
        field_name: str,
        field_type: str,
        default_value: Any,
        patch_bcs: Dict[str, Any],
    ) -> str:
        """Generate OpenFOAM field file with boundary conditions."""
        if field_type == "vector":
            default_str = f"uniform ({default_value[0]} {default_value[1]} {default_value[2]})"
        else:
            default_str = f"uniform {default_value}"
        
        bc_entries = []
        for patch_name, bc_info in patch_bcs.items():
            bc_type = bc_info.get("type", "zeroGradient")
            bc_value = bc_info.get("value", default_value)
            
            if field_type == "vector":
                value_str = f"uniform ({bc_value[0]} {bc_value[1]} {bc_value[2]})"
            else:
                value_str = f"uniform {bc_value}"
            
            bc_entries.append(f"""    {patch_name}
    {{
        type            {bc_type};
        value           {value_str};
    }}""")
        
        return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       vol{field_type.capitalize()}Field;
    location    "0";
    object      {field_name};
}}

dimensions      [0 2 -2 0 0 0 0];
internalField   {default_str};
boundaryField
{{
{chr(10).join(bc_entries)}
}}
"""
    
    async def _convert_gmsh_to_openfoam(
        self,
        mesh_file: Path,
        output_dir: Path,
    ) -> None:
        """Convert GMSH mesh to OpenFOAM format using gmshToFoam."""
        try:
            # Run gmshToFoam
            result = subprocess.run(
                ["gmshToFoam", str(mesh_file)],
                cwd=str(output_dir.parent),
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            if result.returncode != 0:
                logger.warning(f"gmshToFoam failed: {result.stderr}")
                # Try alternative: copy mesh files directly if they exist
                for f in ["points", "faces", "owner", "neighbour", "boundary"]:
                    src = output_dir.parent / f
                    if src.exists():
                        shutil.copy2(src, output_dir / f)
        except FileNotFoundError:
            logger.warning("gmshToFoam not found, skipping mesh conversion")
        except subprocess.TimeoutExpired:
            logger.error("gmshToFoam timed out")
    
    async def _run_openfoam_simulation(
        self,
        simulation: Simulation,
        sim_dir: Path,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Run OpenFOAM simulation."""
        solver = simulation.project.solver_settings.get("solver", "simpleFoam") if simulation.project else "simpleFoam"
        n_procs = config.get("n_procs", 1) if config else 1
        
        # Prepare command
        if n_procs > 1:
            # Decompose
            await self._run_command(sim_dir, ["decomposePar", "-force"])
            
            # Run parallel
            cmd = ["mpirun", "-np", str(n_procs), solver, "-parallel"]
        else:
            cmd = [solver]
        
        # Run simulation
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(sim_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        self._simulation_processes[simulation.id] = process
        
        # Monitor output
        stdout, stderr = await process.communicate()
        
        # Save logs
        log_path = sim_dir / "simulation.log"
        log_path.write_text(stdout.decode() + "\n" + stderr.decode())
        simulation.log_path = str(log_path)
        
        if process.returncode != 0:
            raise RuntimeError(f"OpenFOAM simulation failed: {stderr.decode()}")
        
        # Reconstruct if parallel
        if n_procs > 1:
            await self._run_command(sim_dir, ["reconstructPar", "-latestTime"])
    
    async def _run_su2_simulation(
        self,
        simulation: Simulation,
        sim_dir: Path,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Run SU2 simulation."""
        # Generate SU2 config
        su2_config = self._generate_su2_config(simulation, config)
        (sim_dir / "config.cfg").write_text(su2_config)
        
        # Run SU2
        cmd = ["SU2_CFD", "config.cfg"]
        if config and config.get("n_procs", 1) > 1:
            cmd = ["mpirun", "-np", str(config["n_procs"])] + cmd
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(sim_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        self._simulation_processes[simulation.id] = process
        stdout, stderr = await process.communicate()
        
        log_path = sim_dir / "simulation.log"
        log_path.write_text(stdout.decode() + "\n" + stderr.decode())
        simulation.log_path = str(log_path)
        
        if process.returncode != 0:
            raise RuntimeError(f"SU2 simulation failed: {stderr.decode()}")
    
    def _generate_su2_config(
        self,
        simulation: Simulation,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate SU2 configuration file."""
        project = simulation.project
        physics = project.physics_settings if project else {}
        
        return f"""% SU2 Configuration File
% Generated by CFD Platform

% Solver settings
SOLVER= INC_NAVIER_STOKES
MATH_PROBLEM= DIRECT
TIME_DOMAIN= STEADY

% Flow conditions
FREESTREAM_PRESSURE= {physics.get('pressure', 101325)}
FREESTREAM_TEMPERATURE= {physics.get('temperature', 300)}
FREESTREAM_VELOCITY= {physics.get('velocity', [10, 0, 0])}
FREESTREAM_DENSITY= {physics.get('density', 1.225)}
FREESTREAM_MACH= {physics.get('mach', 0.1)}

% Reference values
REF_LENGTH= {physics.get('ref_length', 1.0)}
REF_AREA= {physics.get('ref_area', 1.0)}

% Numerical settings
CFL_NUMBER= {physics.get('cfl', 1.0)}
NUM_METHOD_GRAD= GREEN_GAUSS
CONV_NUM_METHOD_FLOW= ROE_SECOND_ORDER
TIME_STEPPING= EULER_IMPLICIT

% Convergence
INNER_ITER= 100
CONV_CRITERIA= CAUCHY
CONV_CAUCHY_ELEMS= 100
CONV_CAUCHY_EPS= 1E-6

% Output
SCREEN_OUTPUT= (INNER_ITER, RMS_DENSITY, RMS_MOMENTUM, RMS_ENERGY, CL, CD)
HISTORY_OUTPUT= ITER, RMS_DENSITY, RMS_MOMENTUM, RMS_ENERGY, CL, CD
VOLUME_OUTPUT= PARAVIEW
SURFACE_OUTPUT= PARAVIEW
OUTPUT_FILES= (RESTART, PARAVIEW_BINARY)
"""
    
    async def _run_command(
        self,
        cwd: Path,
        cmd: List[str],
    ) -> subprocess.CompletedProcess:
        """Run command and return result."""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=300)
        )
    
    async def _collect_results(
        self,
        simulation: Simulation,
        sim_dir: Path,
    ) -> None:
        """Collect simulation results."""
        # Find latest time directory
        time_dirs = sorted([d for d in sim_dir.iterdir() if d.is_dir() and d.name.replace(".", "").isdigit()])
        
        if time_dirs:
            latest_time = time_dirs[-1]
            simulation.results_path = str(latest_time)
            
            # Parse forces if available
            forces_file = sim_dir / "postProcessing" / "forces" / "0" / "forceCoeffs.dat"
            if forces_file.exists():
                await self._parse_forces(simulation, forces_file)
            
            # Parse convergence history
            await self._parse_convergence(simulation, sim_dir)
    
    async def _parse_forces(
        self,
        simulation: Simulation,
        forces_file: Path,
    ) -> None:
        """Parse OpenFOAM forces output."""
        try:
            lines = forces_file.read_text().strip().split("\n")
            data_lines = [l for l in lines if not l.startswith("#") and l.strip()]
            
            if data_lines:
                last_line = data_lines[-1].split()
                if len(last_line) >= 7:
                    simulation.performance_metrics = {
                        "drag_coefficient": float(last_line[3]),
                        "lift_coefficient": float(last_line[4]),
                        "moment_coefficient": float(last_line[5]),
                    }
        except Exception as e:
            logger.warning(f"Failed to parse forces: {e}")
    
    async def _parse_convergence(
        self,
        simulation: Simulation,
        sim_dir: Path,
    ) -> None:
        """Parse convergence history from logs."""
        log_file = sim_dir / "simulation.log"
        if not log_file.exists():
            return
        
        try:
            content = log_file.read_text()
            # Parse residuals from log
            residuals = {}
            for line in content.split("\n"):
                if "Solving for" in line and "Initial residual" in line:
                    parts = line.split()
                    var_name = parts[2].rstrip(",")
                    init_res = float(parts[5].rstrip(","))
                    final_res = float(parts[8].rstrip(","))
                    if var_name not in residuals:
                        residuals[var_name] = []
                    residuals[var_name].append({"initial": init_res, "final": final_res})
            
            simulation.convergence_data = residuals
        except Exception as e:
            logger.warning(f"Failed to parse convergence: {e}")
    
    async def stop_simulation(self, simulation_id: uuid.UUID) -> None:
        """
        Stop running simulation.
        
        Args:
            simulation_id: ID of the simulation to stop
        """
        # Cancel asyncio task
        task = self._running_simulations.get(simulation_id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Kill subprocess if running
        process = self._simulation_processes.get(simulation_id)
        if process:
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=10)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            except Exception as e:
                logger.warning(f"Error stopping simulation process: {e}")
        
        # Update database
        result = await self.db.execute(
            select(Simulation).where(Simulation.id == simulation_id)
        )
        simulation = result.scalar_one_or_none()
        
        if simulation and simulation.status == SimulationStatus.RUNNING:
            simulation.status = SimulationStatus.CANCELLED
            simulation.completed_at = datetime.utcnow()
            if simulation.started_at:
                simulation.duration_seconds = (
                    simulation.completed_at - simulation.started_at
                ).total_seconds()
            await self.db.commit()
    
    async def get_simulation_status(self, simulation_id: uuid.UUID) -> Dict[str, Any]:
        """Get current simulation status with progress."""
        result = await self.db.execute(
            select(Simulation).where(Simulation.id == simulation_id)
        )
        simulation = result.scalar_one_or_none()
        
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")
        
        status = {
            "id": str(simulation.id),
            "status": simulation.status.value,
            "progress": 0.0,
            "current_time": None,
            "end_time": None,
        }
        
        if simulation.status == SimulationStatus.RUNNING and simulation.started_at:
            # Estimate progress based on time
            project = simulation.project
            if project:
                time_settings = project.time_settings
                end_time = time_settings.get("end_time", 1000)
                # This would need actual time reading from simulation
                status["current_time"] = 0
                status["end_time"] = end_time
                status["progress"] = 0.0
        
        return status
    
    async def get_simulation_logs(
        self,
        simulation_id: uuid.UUID,
        tail: int = 100,
    ) -> List[str]:
        """Get simulation log lines."""
        result = await self.db.execute(
            select(Simulation).where(Simulation.id == simulation_id)
        )
        simulation = result.scalar_one_or_none()
        
        if not simulation or not simulation.log_path:
            return []
        
        log_path = Path(simulation.log_path)
        if not log_path.exists():
            return []
        
        lines = log_path.read_text().splitlines()
        return lines[-tail:] if tail > 0 else lines