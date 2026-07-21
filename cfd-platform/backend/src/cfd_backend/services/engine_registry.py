"""Local capability registry for the fourteen HX CFD implementation engines.

The registry is intentionally an application-facing contract.  It describes
what HX CFD can do without leaking repository-specific launch details into the
React UI.  External executables are only probed through explicit argument
lists; no shell command is constructed.
"""

from __future__ import annotations

import asyncio
import importlib.metadata
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

from cfd_backend.core.config import Settings
from cfd_backend.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class EngineDefinition:
    """A stable internal identity for one of the fourteen integration engines."""

    id: str
    display_name: str
    workflow: tuple[str, ...]
    runtime: str
    optional: bool
    adapter: str
    distribution: Optional[str] = None
    executable_names: tuple[str, ...] = ()


@dataclass
class EngineCapability:
    """Runtime availability returned to the desktop application."""

    id: str
    display_name: str
    workflow: list[str]
    runtime: str
    optional: bool
    adapter: str
    status: str
    version: Optional[str] = None
    executable: Optional[str] = None
    detail: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


ENGINE_DEFINITIONS: tuple[EngineDefinition, ...] = (
    EngineDefinition(
        id="freecad",
        display_name="FreeCAD",
        workflow=("geometry", "meshing"),
        runtime="isolated_native_worker",
        optional=True,
        adapter="freecad_headless",
        executable_names=("FreeCADCmd.exe", "FreeCADCmd", "freecadcmd"),
    ),
    EngineDefinition(
        id="gmsh",
        display_name="Gmsh",
        workflow=("geometry", "meshing"),
        runtime="isolated_mesh_worker",
        optional=False,
        adapter="gmsh_python_or_cli",
        distribution="gmsh",
        executable_names=("gmsh.exe", "gmsh"),
    ),
    EngineDefinition(
        id="meshio",
        display_name="meshio",
        workflow=("meshing", "results", "reports"),
        runtime="mesh_or_post_worker",
        optional=False,
        adapter="mesh_interchange",
        distribution="meshio",
    ),
    EngineDefinition(
        id="openfoam",
        display_name="OpenFOAM",
        workflow=("meshing", "solver", "results"),
        runtime="isolated_native_process_tree",
        optional=False,
        adapter="openfoam_cli",
        executable_names=("foamVersion", "foamVersion.exe", "simpleFoam", "simpleFoam.exe"),
    ),
    EngineDefinition(
        id="openmdao",
        display_name="OpenMDAO",
        workflow=("optimization",),
        runtime="isolated_optimization_worker",
        optional=True,
        adapter="optimization_study",
        distribution="openmdao",
    ),
    EngineDefinition(
        id="nevergrad",
        display_name="Nevergrad",
        workflow=("optimization",),
        runtime="isolated_optimization_worker",
        optional=True,
        adapter="optimizer_strategy",
        distribution="nevergrad",
    ),
    EngineDefinition(
        id="physicsnemo",
        display_name="PhysicsNeMo",
        workflow=("surrogate", "optimization"),
        runtime="isolated_gpu_worker",
        optional=True,
        adapter="surrogate_training",
        distribution="physicsnemo",
    ),
    EngineDefinition(
        id="physicsnemo_cfd",
        display_name="PhysicsNeMo-CFD",
        workflow=("surrogate", "optimization"),
        runtime="isolated_gpu_worker",
        optional=True,
        adapter="cfd_surrogate",
        distribution="physicsnemo-cfd",
    ),
    EngineDefinition(
        id="vtk",
        display_name="VTK",
        workflow=("results", "reports"),
        runtime="disposable_post_worker",
        optional=False,
        adapter="scientific_data_pipeline",
        distribution="vtk",
    ),
    EngineDefinition(
        id="pyvista",
        display_name="PyVista",
        workflow=("results", "reports"),
        runtime="disposable_post_worker",
        optional=False,
        adapter="post_processing",
        distribution="pyvista",
    ),
    EngineDefinition(
        id="paraview",
        display_name="ParaView",
        workflow=("results", "reports"),
        runtime="isolated_batch_worker",
        optional=True,
        adapter="pvpython_or_pvbatch",
        executable_names=("pvpython.exe", "pvpython", "pvbatch.exe", "pvbatch"),
    ),
    EngineDefinition(
        id="three",
        display_name="three.js",
        workflow=("geometry", "meshing", "results"),
        runtime="tauri_webview",
        optional=False,
        adapter="viewport_renderer",
    ),
    EngineDefinition(
        id="react_three_fiber",
        display_name="react-three-fiber",
        workflow=("geometry", "meshing", "results"),
        runtime="tauri_webview",
        optional=False,
        adapter="react_viewport_composition",
    ),
    EngineDefinition(
        id="drei",
        display_name="drei",
        workflow=("geometry", "meshing", "results"),
        runtime="tauri_webview",
        optional=False,
        adapter="viewport_interaction_helpers",
    ),
)


class EngineRegistry:
    """Detect local engines and expose a stable capability inventory."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._cache: Optional[dict[str, EngineCapability]] = None

    @property
    def definitions(self) -> tuple[EngineDefinition, ...]:
        return ENGINE_DEFINITIONS

    async def inventory(self, refresh: bool = False) -> list[dict]:
        """Return all fourteen engines in canonical order."""
        if refresh or self._cache is None:
            capabilities = await asyncio.gather(
                *(self._probe(definition) for definition in self.definitions)
            )
            self._cache = {capability.id: capability for capability in capabilities}
        return [self._cache[definition.id].as_dict() for definition in self.definitions]

    async def capability(self, engine_id: str, refresh: bool = False) -> EngineCapability:
        """Return a single canonical capability or fail on an unknown identifier."""
        await self.inventory(refresh=refresh)
        assert self._cache is not None
        try:
            return self._cache[engine_id]
        except KeyError as exc:
            raise ValueError(f"Unknown HX CFD engine: {engine_id}") from exc

    async def requirements_available(
        self, engine_ids: Iterable[str], refresh: bool = False
    ) -> tuple[bool, list[dict]]:
        """Report whether a workflow can run with its required local engines."""
        # Refresh the inventory once per workflow request.  Calling
        # ``capability(..., refresh=True)`` for every item would otherwise
        # re-probe the complete fourteen-engine toolchain N times (including
        # isolated PhysicsNeMo imports) before one mesh or results operation.
        # The snapshot below is both faster and internally consistent.
        requested = tuple(engine_ids)
        await self.inventory(refresh=refresh)
        assert self._cache is not None
        capabilities: list[EngineCapability] = []
        for engine_id in requested:
            try:
                capabilities.append(self._cache[engine_id])
            except KeyError as exc:
                raise ValueError(f"Unknown HX CFD engine: {engine_id}") from exc
        unavailable = [
            capability.as_dict()
            for capability in capabilities
            if capability.status not in {"ready", "bundled"}
        ]
        return not unavailable, unavailable

    async def _probe(self, definition: EngineDefinition) -> EngineCapability:
        if definition.id in {"physicsnemo", "physicsnemo_cfd"}:
            return await self._probe_physicsnemo(definition)

        if definition.runtime == "tauri_webview":
            return EngineCapability(
                id=definition.id,
                display_name=definition.display_name,
                workflow=list(definition.workflow),
                runtime=definition.runtime,
                optional=definition.optional,
                adapter=definition.adapter,
                status="bundled",
                detail="Bundled into the HX CFD desktop webview.",
            )

        if definition.distribution:
            version = self._python_distribution_version(definition.distribution)
            if version:
                return EngineCapability(
                    id=definition.id,
                    display_name=definition.display_name,
                    workflow=list(definition.workflow),
                    runtime=definition.runtime,
                    optional=definition.optional,
                    adapter=definition.adapter,
                    status="ready",
                    version=version,
                    detail="Available in the managed local Python runtime.",
                )

        executable = self._resolve_executable(definition)
        if executable:
            version, detail = await self._probe_executable(executable)
            return EngineCapability(
                id=definition.id,
                display_name=definition.display_name,
                workflow=list(definition.workflow),
                runtime=definition.runtime,
                optional=definition.optional,
                adapter=definition.adapter,
                status="ready",
                version=version,
                executable=str(executable),
                detail=detail,
            )

        required = "required" if not definition.optional else "optional"
        return EngineCapability(
            id=definition.id,
            display_name=definition.display_name,
            workflow=list(definition.workflow),
            runtime=definition.runtime,
            optional=definition.optional,
            adapter=definition.adapter,
            status="unavailable",
            detail=f"{definition.display_name} is not available in the local {required} toolchain.",
        )

    async def _probe_physicsnemo(self, definition: EngineDefinition) -> EngineCapability:
        """Verify the checked-out PhysicsNeMo repositories in their own runtime.

        These repositories are intentionally isolated from the general CFD
        runtime because their CUDA/Torch dependency graph is substantially
        different. Both repositories must import in the same worker before the
        surrogate stage is declared ready.
        """
        python = self._physicsnemo_python()
        cfd_source = self._physicsnemo_cfd_source()
        if python and cfd_source:
            environment = os.environ.copy()
            environment["PYTHONPATH"] = self._append_python_path(
                environment.get("PYTHONPATH"), cfd_source
            )
            module = "physicsnemo" if definition.id == "physicsnemo" else "physicsnemo.cfd"
            try:
                process = await asyncio.create_subprocess_exec(
                    str(python),
                    "-c",
                    f"import {module}; print('ready')",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=environment,
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=20)
                if process.returncode == 0 and stdout.decode(errors="replace").strip() == "ready":
                    return EngineCapability(
                        id=definition.id,
                        display_name=definition.display_name,
                        workflow=list(definition.workflow),
                        runtime=definition.runtime,
                        optional=definition.optional,
                        adapter=definition.adapter,
                        status="ready",
                        executable=str(python),
                        detail="Verified in the isolated local PhysicsNeMo repository runtime.",
                    )
                logger.debug(
                    "PhysicsNeMo import probe failed",
                    engine=definition.id,
                    detail=(stderr or stdout).decode(errors="replace")[-500:],
                )
            except (OSError, asyncio.TimeoutError) as error:
                logger.debug("PhysicsNeMo runtime probe failed", engine=definition.id, error=str(error))

        return EngineCapability(
            id=definition.id,
            display_name=definition.display_name,
            workflow=list(definition.workflow),
            runtime=definition.runtime,
            optional=definition.optional,
            adapter=definition.adapter,
            status="unavailable",
            detail=(
                "PhysicsNeMo and PhysicsNeMo-CFD need their checked-out local source "
                "and isolated Python runtime before surrogate training can run."
            ),
        )

    def worker_environment(self, engine_id: str) -> dict[str, str]:
        """Return only the engine-specific environment needed by a worker."""
        if engine_id in {"physicsnemo", "physicsnemo_cfd"}:
            cfd_source = self._physicsnemo_cfd_source()
            if cfd_source:
                return {"PYTHONPATH": self._append_python_path(os.environ.get("PYTHONPATH"), cfd_source)}
        return {}

    def _physicsnemo_python(self) -> Optional[Path]:
        configured = self.settings.physicsnemo_python
        if configured and Path(configured).is_file():
            return Path(configured)
        workspace = self._workspace_root()
        candidate = workspace / "physicsnemo" / ".venv" / "Scripts" / "python.exe"
        if candidate.is_file():
            return candidate
        candidate = workspace / "physicsnemo" / ".venv" / "bin" / "python"
        return candidate if candidate.is_file() else None

    def _physicsnemo_cfd_source(self) -> Optional[Path]:
        configured = self.settings.physicsnemo_cfd_path
        if configured and (Path(configured) / "physicsnemo" / "cfd").is_dir():
            return Path(configured)
        candidate = self._workspace_root() / "physicsnemo-cfd"
        return candidate if (candidate / "physicsnemo" / "cfd").is_dir() else None

    @staticmethod
    def _workspace_root() -> Path:
        # backend/src/cfd_backend/services/engine_registry.py -> workspace
        return Path(__file__).resolve().parents[5]

    @staticmethod
    def _append_python_path(existing: Optional[str], source: Path) -> str:
        return os.pathsep.join(part for part in (str(source), existing) if part)

    def _python_distribution_version(self, distribution: str) -> Optional[str]:
        try:
            return importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            return None

    def _resolve_executable(self, definition: EngineDefinition) -> Optional[Path]:
        configured_paths = {
            "gmsh": self.settings.gmsh_path,
            "openfoam": self.settings.openfoam_path,
            "paraview": self.settings.paraview_path,
            "freecad": self.settings.freecad_path,
        }
        configured = configured_paths.get(definition.id)
        if configured:
            configured_path = Path(configured)
            if configured_path.is_file():
                return configured_path
            for name in definition.executable_names:
                candidate = configured_path / name
                if candidate.exists():
                    return candidate
                candidate = configured_path / "bin" / name
                if candidate.exists():
                    return candidate

        for name in definition.executable_names:
            location = shutil.which(name)
            if location:
                return Path(location)

        for candidate in self._windows_defaults(definition.id, definition.executable_names):
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _windows_defaults(engine_id: str, executable_names: tuple[str, ...]) -> tuple[Path, ...]:
        program_files = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
            Path(os.environ.get("ProgramW6432", r"C:\Program Files")),
        ]
        relative_roots = {
            "freecad": ("FreeCAD", "FreeCAD 1.0"),
            "gmsh": ("Gmsh",),
            "paraview": ("ParaView", "ParaView 5.12.0"),
            "openfoam": ("OpenFOAM",),
        }.get(engine_id, ())
        candidates: list[Path] = []
        for parent in program_files:
            for root in relative_roots:
                for executable in executable_names:
                    candidates.append(parent / root / "bin" / executable)
                    candidates.append(parent / root / executable)
        return tuple(candidates)

    async def _probe_executable(self, executable: Path) -> tuple[Optional[str], str]:
        for args in ((str(executable), "--version"), (str(executable), "-version")):
            try:
                process = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=8)
            except (FileNotFoundError, PermissionError, asyncio.TimeoutError) as exc:
                logger.debug("Engine executable probe failed", executable=str(executable), error=str(exc))
                continue

            output = (stdout or stderr).decode(errors="replace").strip()
            if process.returncode == 0:
                return self._first_output_line(output), "Local executable verified."

        return None, "Local executable found; version probe did not return a version."

    @staticmethod
    def _first_output_line(output: str) -> Optional[str]:
        for line in output.splitlines():
            if line.strip():
                return line.strip()[:160]
        return None
