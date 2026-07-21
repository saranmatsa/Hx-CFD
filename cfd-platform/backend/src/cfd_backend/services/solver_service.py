"""
Solver Service for CFD Backend.

Provides business logic for running, monitoring, and managing CFD solver configurations.
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
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cfd_backend.models.solver import SolverConfig, SolverStatus, SolverType
from cfd_backend.models.project import Project
from cfd_backend.models.simulation import Simulation, SimulationStatus

logger = logging.getLogger(__name__)


class SolverService:
    """Service for solver operations including running, monitoring, and managing solver configurations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._running_solvers: Dict[UUID, asyncio.Task] = {}
        self._solver_processes: Dict[UUID, subprocess.Popen] = {}

    async def run_solver(
        self,
        config_id: UUID,
        simulation_id: Optional[UUID] = None,
        overwrite: bool = False,
    ) -> UUID:
        """
        Run solver with configuration.

        Args:
            config_id: ID of the solver configuration
            simulation_id: Optional simulation ID to associate with this run
            overwrite: Whether to overwrite existing results

        Returns:
            Run ID (UUID) for tracking
        """
        # Get solver config with relationships
        result = await self.db.execute(
            select(SolverConfig)
            .options(
                selectinload(SolverConfig.project),
                selectinload(SolverConfig.simulation),
            )
            .where(SolverConfig.id == config_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise ValueError(f"SolverConfig {config_id} not found")

        if config.status == SolverStatus.RUNNING:
            raise ValueError("Solver already running")

        run_id = uuid.uuid4()

        try:
            # Update status
            config.status = SolverStatus.PREPARING
            config.updated_at = datetime.utcnow()
            await self.db.commit()

            # Prepare case directory
            case_dir = await self._prepare_case_directory(config, simulation_id, overwrite)

            # Update status to running
            config.status = SolverStatus.RUNNING
            config.last_run_at = datetime.utcnow()
            await self.db.commit()

            # Run solver based on type
            if config.solver_type == SolverType.OPENFOAM:
                task = asyncio.create_task(
                    self._run_openfoam_solver(config, case_dir, run_id, simulation_id)
                )
            elif config.solver_type == SolverType.SU2:
                task = asyncio.create_task(
                    self._run_su2_solver(config, case_dir, run_id, simulation_id)
                )
            else:
                raise ValueError(f"Unsupported solver type: {config.solver_type}")

            self._running_solvers[run_id] = task

            return run_id

        except Exception as e:
            config.status = SolverStatus.FAILED
            config.last_run_log = str(e)
            config.updated_at = datetime.utcnow()
            await self.db.commit()
            logger.exception(f"Solver run failed for {config_id}: {e}")
            raise

    async def _prepare_case_directory(
        self,
        config: SolverConfig,
        simulation_id: Optional[UUID] = None,
        overwrite: bool = False,
    ) -> Path:
        """Prepare solver case directory with all necessary files."""
        # Determine base directory
        base_dir = Path(config.case_directory) if config.case_directory else Path("/tmp/cfd_cases")
        case_dir = base_dir / str(config.project_id) / str(config.id)

        if overwrite and case_dir.exists():
            shutil.rmtree(case_dir)

        case_dir.mkdir(parents=True, exist_ok=True)

        # Write OpenFOAM case files
        if config.solver_type == SolverType.OPENFOAM:
            await self._write_openfoam_case(config, case_dir)
        elif config.solver_type == SolverType.SU2:
            await self._write_su2_case(config, case_dir)

        return case_dir

    async def _write_openfoam_case(self, config: SolverConfig, case_dir: Path) -> None:
        """Write OpenFOAM case files from configuration."""
        # controlDict
        control_dict = config.control_dict or {}
        control_dict.setdefault("application", config.solver_version)
        control_dict.setdefault("startFrom", "startTime")
        control_dict.setdefault("startTime", 0)
        control_dict.setdefault("stopAt", "endTime")
        control_dict.setdefault("endTime", 1000)
        control_dict.setdefault("deltaT", 1)
        control_dict.setdefault("writeControl", "timeStep")
        control_dict.setdefault("writeInterval", 100)
        control_dict.setdefault("purgeWrite", 0)
        control_dict.setdefault("writeFormat", "ascii")
        control_dict.setdefault("writePrecision", 6)
        control_dict.setdefault("writeCompression", "off")
        control_dict.setdefault("timeFormat", "general")
        control_dict.setdefault("timePrecision", 6)
        control_dict.setdefault("runTimeModifiable", True)

        self._write_foam_file(case_dir / "system" / "controlDict", control_dict)

        # fvSchemes
        fv_schemes = config.fv_schemes or {}
        fv_schemes.setdefault("ddtSchemes", {"default": "Euler"})
        fv_schemes.setdefault("gradSchemes", {"default": "Gauss linear"})
        fv_schemes.setdefault("divSchemes", {"default": "none", "div(phi,U)": "Gauss linearUpwind grad(U)"})
        fv_schemes.setdefault("laplacianSchemes", {"default": "Gauss linear corrected"})
        fv_schemes.setdefault("interpolationSchemes", {"default": "linear"})
        fv_schemes.setdefault("snGradSchemes", {"default": "corrected"})

        self._write_foam_file(case_dir / "system" / "fvSchemes", fv_schemes)

        # fvSolution
        fv_solution = config.fv_solution or {}
        fv_solution.setdefault("solvers", {
            "p": {"solver": "GAMG", "tolerance": 1e-06, "relTol": 0.1, "smoother": "GaussSeidel"},
            "U": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
        })
        fv_solution.setdefault("SIMPLE", {
            "nNonOrthogonalCorrectors": 1,
            "consistent": True,
        })
        fv_solution.setdefault("relaxationFactors", {
            "fields": {"p": 0.3, "U": 0.7},
            "equations": {"U": 0.7},
        })

        self._write_foam_file(case_dir / "system" / "fvSolution", fv_solution)

        # transportProperties
        transport_props = config.transport_properties or {}
        transport_props.setdefault("transportModel", "Newtonian")
        transport_props.setdefault("nu", [0, 1e-05, 0, 0, 0, 0, 0])

        self._write_foam_file(case_dir / "constant" / "transportProperties", transport_props)

        # turbulenceProperties
        turbulence_props = config.turbulence_properties or {}
        turbulence_props.setdefault("simulationType", "RAS")
        turbulence_props.setdefault("RAS", {
            "RASModel": "kEpsilon",
            "turbulence": True,
            "printCoeffs": True,
        })

        self._write_foam_file(case_dir / "constant" / "turbulenceProperties", turbulence_props)

        # boundary conditions
        if config.boundary_conditions:
            self._write_boundary_conditions(config, case_dir)

        # initial conditions
        if config.initial_conditions:
            self._write_initial_conditions(config, case_dir)

    def _write_foam_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Write OpenFOAM dictionary file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)

        def format_value(key: str, value: Any, indent: int = 0) -> str:
            spaces = " " * indent
            if isinstance(value, dict):
                lines = [f"{spaces}{key}"]
                lines.append(f"{spaces}{{")
                for k, v in value.items():
                    lines.append(format_value(k, v, indent + 4))
                lines.append(f"{spaces}}}")
                return "\n".join(lines)
            elif isinstance(value, list):
                if all(isinstance(v, (int, float)) for v in value):
                    return f"{spaces}{key} {' '.join(str(v) for v in value)};"
                else:
                    return f"{spaces}{key} ({' '.join(str(v) for v in value)});"
            elif isinstance(value, bool):
                return f"{spaces}{key} {'on' if value else 'off'};"
            elif isinstance(value, str):
                return f'{spaces}{key} "{value}";'
            else:
                return f"{spaces}{key} {value};"

        lines = ["FoamFile", "{", '    version     2.0;', '    format      ascii;', '    class       dictionary;', '    location    "system";', '    object      controlDict;', "}", ""]

        for key, value in data.items():
            lines.append(format_value(key, value))

        file_path.write_text("\n".join(lines))

    def _write_boundary_conditions(self, config: SolverConfig, case_dir: Path) -> None:
        """
        Write OpenFOAM boundary condition files (0/U, 0/p) from config.

        boundary_conditions is a list of dicts, each describing a patch:
            [{"name": "inlet", "type": "patch", "U": {...}, "p": {...}}, ...]
        """
        zero_dir = case_dir / "0"
        zero_dir.mkdir(parents=True, exist_ok=True)

        bc_list = config.boundary_conditions or []

        # Build boundaryField entries for U and p
        u_patches: Dict[str, Any] = {}
        p_patches: Dict[str, Any] = {}

        for bc in bc_list:
            patch_name = bc.get("name", "patch")
            patch_type = bc.get("type", "patch")
            u_entry = bc.get("U")
            p_entry = bc.get("p")

            if u_entry is not None:
                u_patches[patch_name] = {
                    "type": u_entry.get("type", "fixedValue"),
                    "value": u_entry.get("value", "uniform (0 0 0)"),
                }
            else:
                u_patches[patch_name] = {"type": "calculated", "value": "uniform (0 0 0)"}

            if p_entry is not None:
                p_patches[patch_name] = {
                    "type": p_entry.get("type", "fixedValue"),
                    "value": p_entry.get("value", "uniform 0"),
                }
            else:
                p_patches[patch_name] = {"type": "calculated", "value": "uniform 0"}

        # Write 0/U
        self._write_foam_field_file(
            zero_dir / "U",
            class_name="volVectorField",
            object_name="U",
            internal_field="uniform (0 0 0)",
            boundary_patches=u_patches,
        )

        # Write 0/p
        self._write_foam_field_file(
            zero_dir / "p",
            class_name="volScalarField",
            object_name="p",
            internal_field="uniform 0",
            boundary_patches=p_patches,
        )

    def _write_initial_conditions(self, config: SolverConfig, case_dir: Path) -> None:
        """
        Write OpenFOAM initial condition files from config.

        initial_conditions is a dict like:
            {"U": "uniform (0 0 0)", "p": "uniform 0", "k": ..., "omega": ...}
        If a field file already exists (from boundary conditions), update internalField.
        Otherwise create a new field file with calculated boundaries.
        """
        zero_dir = case_dir / "0"
        zero_dir.mkdir(parents=True, exist_ok=True)

        ic = config.initial_conditions or {}

        for field_name, value in ic.items():
            field_path = zero_dir / field_name

            if field_path.exists():
                # Update internalField in existing file
                content = field_path.read_text()
                import re
                content = re.sub(
                    r'internalField\s+[^;]+;',
                    f'internalField   {value};',
                    content,
                )
                field_path.write_text(content)
            else:
                # Create new field file
                is_vector = isinstance(value, str) and "(" in value
                class_name = "volVectorField" if is_vector else "volScalarField"
                self._write_foam_field_file(
                    field_path,
                    class_name=class_name,
                    object_name=field_name,
                    internal_field=value if isinstance(value, str) else f"uniform {value}",
                    boundary_patches={},
                )

    def _write_foam_field_file(
        self,
        file_path: Path,
        class_name: str,
        object_name: str,
        internal_field: str,
        boundary_patches: Dict[str, Any],
    ) -> None:
        """Write an OpenFOAM field file (0/U, 0/p, etc.)."""
        file_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "FoamFile",
            "{",
            "    version     2.0;",
            "    format      ascii;",
            f"    class       {class_name};",
            '    location    "0";',
            f'    object      {object_name};',
            "}",
            "",
            f"dimensions      [0 0 0 0 0 0 0];",
            "",
            f"internalField   {internal_field};",
            "",
            "boundaryField",
            "{",
        ]

        for patch_name, patch_data in boundary_patches.items():
            lines.append(f"    {patch_name}")
            lines.append("    {")
            for k, v in patch_data.items():
                lines.append(f"        {k}   {v};")
            lines.append("    }")

        if not boundary_patches:
            lines.append("    // No boundary conditions specified")

        lines.append("}")
        lines.append("")

        file_path.write_text("\n".join(lines))

    async def _write_su2_case(self, config: SolverConfig, case_dir: Path) -> None:
        """Write SU2 case files from configuration."""
        # SU2 config file
        su2_config = config.solver_parameters or {}
        su2_config.setdefault("SOLVER", "INC_NAVIER_STOKES")
        su2_config.setdefault("TIME_DOMAIN", "YES")
        su2_config.setdefault("TIME_STEP", 1.0)
        su2_config.setdefault("TIME_ITER", 1000)

        config_file = case_dir / "config.cfg"
        lines = []
        for key, value in su2_config.items():
            if isinstance(value, bool):
                lines.append(f"{key} = {'YES' if value else 'NO'}")
            elif isinstance(value, str):
                lines.append(f'{key} = "{value}"')
            else:
                lines.append(f"{key} = {value}")

        config_file.write_text("\n".join(lines))

    async def _run_openfoam_solver(
        self,
        config: SolverConfig,
        case_dir: Path,
        run_id: UUID,
        simulation_id: Optional[UUID] = None,
    ) -> None:
        """Run OpenFOAM solver."""
        try:
            # Decompose if parallel
            if config.parallel and config.num_processors > 1:
                await self._decompose_case(case_dir, config.num_processors, config.decomposition_method)

            # Determine solver command
            solver_name = config.solver_version
            if config.parallel and config.num_processors > 1:
                cmd = ["mpirun", "-np", str(config.num_processors), solver_name, "-parallel"]
            else:
                cmd = [solver_name]

            # Run solver
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=case_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            self._solver_processes[run_id] = process

            # Monitor output
            log_lines = []
            async for line in process.stdout:
                line_str = line.decode().rstrip()
                log_lines.append(line_str)
                # Keep last 1000 lines
                if len(log_lines) > 1000:
                    log_lines = log_lines[-1000:]

                # Update progress from log
                await self._update_progress_from_log(config, run_id, line_str)

            await process.wait()

            # Update config with results
            config.last_run_duration = (datetime.utcnow() - config.last_run_at).total_seconds() if config.last_run_at else 0
            config.last_run_log = "\n".join(log_lines[-100:])  # Last 100 lines

            if process.returncode == 0:
                config.status = SolverStatus.COMPLETED
            else:
                config.status = SolverStatus.FAILED
                config.last_run_log += f"\nSolver exited with code {process.returncode}"

            config.updated_at = datetime.utcnow()
            await self.db.commit()

            # Reconstruct if parallel
            if config.parallel and config.num_processors > 1:
                await self._reconstruct_case(case_dir)

        except asyncio.CancelledError:
            config.status = SolverStatus.CANCELLED
            config.updated_at = datetime.utcnow()
            await self.db.commit()
            raise
        except Exception as e:
            config.status = SolverStatus.FAILED
            config.last_run_log = str(e)
            config.updated_at = datetime.utcnow()
            await self.db.commit()
            logger.exception(f"OpenFOAM solver failed for {config.id}: {e}")
            raise
        finally:
            self._running_solvers.pop(run_id, None)
            self._solver_processes.pop(run_id, None)

    async def _run_su2_solver(
        self,
        config: SolverConfig,
        case_dir: Path,
        run_id: UUID,
        simulation_id: Optional[UUID] = None,
    ) -> None:
        """Run SU2 solver."""
        try:
            config_file = case_dir / "config.cfg"
            cmd = ["SU2_CFD", str(config_file)]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=case_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            self._solver_processes[run_id] = process

            log_lines = []
            async for line in process.stdout:
                line_str = line.decode().rstrip()
                log_lines.append(line_str)
                if len(log_lines) > 1000:
                    log_lines = log_lines[-1000:]
                await self._update_progress_from_log(config, run_id, line_str)

            await process.wait()

            config.last_run_duration = (datetime.utcnow() - config.last_run_at).total_seconds() if config.last_run_at else 0
            config.last_run_log = "\n".join(log_lines[-100:])

            if process.returncode == 0:
                config.status = SolverStatus.COMPLETED
            else:
                config.status = SolverStatus.FAILED
                config.last_run_log += f"\nSolver exited with code {process.returncode}"

            config.updated_at = datetime.utcnow()
            await self.db.commit()

        except asyncio.CancelledError:
            config.status = SolverStatus.CANCELLED
            config.updated_at = datetime.utcnow()
            await self.db.commit()
            raise
        except Exception as e:
            config.status = SolverStatus.FAILED
            config.last_run_log = str(e)
            config.updated_at = datetime.utcnow()
            await self.db.commit()
            logger.exception(f"SU2 solver failed for {config.id}: {e}")
            raise
        finally:
            self._running_solvers.pop(run_id, None)
            self._solver_processes.pop(run_id, None)

    async def _decompose_case(self, case_dir: Path, num_processors: int, method: str = "scotch") -> None:
        """Decompose OpenFOAM case for parallel run."""
        # Write decomposeParDict
        decompose_dict = {
            "numberOfSubdomains": num_processors,
            "method": method,
        }
        self._write_foam_file(case_dir / "system" / "decomposeParDict", decompose_dict)

        # Run decomposePar
        process = await asyncio.create_subprocess_exec(
            "decomposePar",
            cwd=case_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await process.wait()

        if process.returncode != 0:
            stdout = await process.stdout.read()
            raise RuntimeError(f"decomposePar failed: {stdout.decode()}")

    async def _reconstruct_case(self, case_dir: Path) -> None:
        """Reconstruct OpenFOAM case after parallel run."""
        process = await asyncio.create_subprocess_exec(
            "reconstructPar",
            cwd=case_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await process.wait()

        if process.returncode != 0:
            stdout = await process.stdout.read()
            logger.warning(f"reconstructPar failed: {stdout.decode()}")

    async def _update_progress_from_log(
        self,
        config: SolverConfig,
        run_id: UUID,
        log_line: str,
    ) -> None:
        """Update solver progress from log output."""
        # Parse iteration and residuals from log
        import re

        # OpenFOAM iteration pattern
        iter_match = re.search(r"Time = ([\d.]+)", log_line)
        if iter_match:
            config.current_iteration = int(float(iter_match.group(1)))

        # Residual patterns
        residual_match = re.search(r"Solving for (\w+).*Initial residual = ([\deE.-]+)", log_line)
        if residual_match:
            var = residual_match.group(1)
            residual = float(residual_match.group(2))
            if not hasattr(config, '_residuals'):
                config._residuals = {}
            config._residuals[var] = residual

        await self.db.commit()

    async def stop_solver(self, config_id: UUID) -> None:
        """Stop running solver."""
        result = await self.db.execute(
            select(SolverConfig).where(SolverConfig.id == config_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise ValueError(f"SolverConfig {config_id} not found")

        # Find running task
        for run_id, task in self._running_solvers.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Kill process if running
        for run_id, process in self._solver_processes.items():
            if process.poll() is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()

        config.status = SolverStatus.CANCELLED
        config.updated_at = datetime.utcnow()
        await self.db.commit()

    async def get_solver_status(self, config_id: UUID) -> Dict[str, Any]:
        """Get solver run status."""
        result = await self.db.execute(
            select(SolverConfig).where(SolverConfig.id == config_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise ValueError(f"SolverConfig {config_id} not found")

        # Find active run
        run_id = None
        for rid, task in self._running_solvers.items():
            if not task.done():
                run_id = rid
                break

        status_info = {
            "run_id": str(run_id) if run_id else str(config.id),
            "simulation_id": str(config.simulation_id) if config.simulation_id else None,
            "status": config.status.value if config.status else SolverStatus.READY.value,
            "progress": 0.0,
            "current_iteration": config.current_iteration or 0,
            "max_iterations": config.max_iterations or 1000,
            "residuals": getattr(config, '_residuals', {}),
            "started_at": config.last_run_at.isoformat() if config.last_run_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            "estimated_remaining": None,
            "log_tail": config.last_run_log.split("\n")[-50:] if config.last_run_log else [],
        }

        # Calculate progress
        if config.max_iterations and config.max_iterations > 0:
            status_info["progress"] = min(100.0, (config.current_iteration or 0) / config.max_iterations * 100)

        return status_info

    async def get_solver_logs(
        self,
        config_id: UUID,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """Get solver logs with pagination."""
        result = await self.db.execute(
            select(SolverConfig).where(SolverConfig.id == config_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise ValueError(f"SolverConfig {config_id} not found")

        logs = config.last_run_log.split("\n") if config.last_run_log else []
        total_lines = len(logs)

        start = (page - 1) * page_size
        end = start + page_size
        page_logs = logs[start:end]

        return {
            "run_id": str(config.id),
            "logs": page_logs,
            "total_lines": total_lines,
        }

    async def decompose_case(self, config_id: UUID) -> None:
        """Decompose case for parallel run."""
        result = await self.db.execute(
            select(SolverConfig).where(SolverConfig.id == config_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise ValueError(f"SolverConfig {config_id} not found")

        if not config.parallel:
            raise ValueError("Parallel not enabled for this configuration")

        if not config.case_directory:
            raise ValueError("Case directory not set")

        case_dir = Path(config.case_directory)
        await self._decompose_case(case_dir, config.num_processors, config.decomposition_method)

    async def reconstruct_case(self, config_id: UUID) -> None:
        """Reconstruct case after parallel run."""
        result = await self.db.execute(
            select(SolverConfig).where(SolverConfig.id == config_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise ValueError(f"SolverConfig {config_id} not found")

        if not config.case_directory:
            raise ValueError("Case directory not set")

        case_dir = Path(config.case_directory)
        await self._reconstruct_case(case_dir)
