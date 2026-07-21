"""Execution adapters for the local HX CFD engineering toolchain.

This module deliberately has no synthetic solver, mesh, or result fallbacks.
Each stage either invokes its declared local engine and publishes its resulting
artifacts, or raises an actionable error.  That keeps the desktop workflow an
orchestrator rather than a visual simulation of one.
"""

from __future__ import annotations

import asyncio
import html
import importlib.util
import json
import math
import os
import re
import shutil
import sys
import threading
from pathlib import Path
from typing import Any

from cfd_backend.core.config import Settings
from cfd_backend.services.engine_registry import EngineRegistry


# Gmsh/OpenCASCADE can only be used as the no-FreeCAD fallback for solid CAD
# exchange files.  FreeCAD is the canonical geometry importer and also owns
# mesh-source import (STL/OBJ), because turning an arbitrary triangle surface
# into a CFD solid is a CAD operation, not a Gmsh import guarantee.
GMSH_SOLID_CAD_EXTENSIONS = frozenset({".brep", ".iges", ".igs", ".step", ".stp"})
FREECAD_MESH_SOURCE_EXTENSIONS = frozenset({".stl", ".obj"})
FREECAD_GEOMETRY_SOURCE_EXTENSIONS = (
    GMSH_SOLID_CAD_EXTENSIONS | FREECAD_MESH_SOURCE_EXTENSIONS
)
_GMSH_API_LOCK = threading.Lock()
_OPENFOAM_PATCH_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_OPENFOAM_BOUNDARY_ENTRY = re.compile(
    r"(?ms)^\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\{(?P<body>.*?)^\s*\}"
)
_OPENFOAM_BOUNDARY_TYPE = re.compile(r"\btype\s+(?P<type>[A-Za-z_][A-Za-z0-9_]*)\s*;")

# The names below are part of the file contract with ``gmshToFoam`` and the
# OpenFOAM case adapter.  Keep the mapping deliberately small: an engineer
# selects geometric surface entity IDs, HX CFD turns those into named physical
# groups, and the solver later checks the same names in ``polyMesh/boundary``.
# No heuristic is allowed to turn an arbitrary face into an inlet or outlet.
_GMSH_BOUNDARY_ROLE_NAMES = {
    "inlet": "inlet",
    "outlet": "outlet",
    "wall": "walls",
    "symmetry": "symmetry",
}
_GMSH_BOUNDARY_FIELD_NAMES = {
    "inlet": "Inlet surface IDs",
    "outlet": "Outlet surface IDs",
    "wall": "Wall surface IDs",
    "symmetry": "Symmetry surface IDs",
}
_GMSH_UNASSIGNED_SURFACE_POLICIES = {
    "keep as unassigned patch": "unassigned",
    "leave ungrouped": "unassigned",
    "unassigned": "unassigned",
    "group remaining as walls": "walls",
    "treat remaining surfaces as walls": "walls",
    "walls": "walls",
}


class EngineeringExecutionError(RuntimeError):
    """A requested engineering operation could not be completed locally."""


class EngineeringOrchestrator:
    """Run canonical engines and publish local artifact references."""

    def __init__(self, settings: Settings, engines: EngineRegistry):
        self.settings = settings
        self.engines = engines

    async def execute(
        self,
        project_path: Path,
        stage_id: str,
        configuration: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        run_path = project_path / "runs" / stage_id / job_id
        run_path.mkdir(parents=True, exist_ok=False)
        log_path = project_path / "logs" / f"{job_id}.log"

        try:
            if stage_id == "geometry":
                output = await self._prepare_geometry(project_path, run_path, configuration)
            elif stage_id == "meshing":
                output = await self._generate_mesh(project_path, run_path, configuration)
            elif stage_id == "physics":
                output = await self._write_physics_case(project_path, run_path, configuration)
            elif stage_id == "solver":
                output = await self._run_solver(project_path, run_path, configuration)
            elif stage_id == "results":
                output = await self._process_results(project_path, run_path, configuration)
            elif stage_id == "reports":
                output = await self._publish_report(project_path, run_path, configuration)
            elif stage_id == "optimization":
                output = await self._optimize_design(project_path, run_path, configuration)
            elif stage_id == "surrogate":
                output = await self._train_surrogate(project_path, run_path, configuration)
            else:
                raise EngineeringExecutionError(f"Unsupported engineering workflow stage: {stage_id}")
        except Exception as error:
            log_path.write_text(f"{type(error).__name__}: {error}\n", encoding="utf-8")
            if isinstance(error, EngineeringExecutionError):
                raise
            raise EngineeringExecutionError(str(error)) from error

        output["run_path"] = str(run_path)
        output["log_artifact_id"] = str(log_path)
        self._write_json(log_path, {"stage": stage_id, "job_id": job_id, "output": output})
        self._publish_reference(project_path, stage_id, job_id, output)
        return output

    async def _prepare_geometry(
        self, project_path: Path, run_path: Path, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        source = self._source_path(configuration)
        self._validate_geometry_source(source)

        # FreeCAD remains the preferred native preparation route when it is
        # installed.  Gmsh's OpenCASCADE kernel is a real, local fallback for
        # solid CAD exchange formats; it is not a fabricated geometry result.
        freecad = await self.engines.capability("freecad", refresh=True)
        if freecad.status in {"ready", "bundled"}:
            return await self._prepare_geometry_with_freecad(run_path, source)

        if source.suffix.lower() not in GMSH_SOLID_CAD_EXTENSIONS:
            raise EngineeringExecutionError(
                f"{source.suffix.upper().lstrip('.')} geometry import requires local FreeCAD. "
                "Gmsh is available only as a fallback for solid STEP, IGES, and BREP CAD files; "
                "it does not turn an STL or OBJ surface mesh into a watertight CFD solid. "
                "Install or configure FreeCAD, then repair and close the source surface before meshing."
            )
        return await self._prepare_geometry_with_gmsh(run_path, source)

    async def _prepare_geometry_with_freecad(self, run_path: Path, source: Path) -> dict[str, Any]:
        await self._require(("freecad",))
        output = run_path / "prepared.step"
        report = run_path / "geometry-report.json"
        script = run_path / "prepare_geometry.py"
        script.write_text(self._freecad_preparation_script(), encoding="utf-8")
        executable = await self._engine_executable("freecad")
        stdout = await self._run((executable, str(script), str(source), str(output), str(report)), run_path)
        if not output.exists() or not report.exists():
            raise EngineeringExecutionError("FreeCAD did not produce prepared geometry artifacts.")
        geometry = self._read_json(report)
        if not geometry.get("valid"):
            raise EngineeringExecutionError("FreeCAD reported invalid geometry after repair.")
        return {
            "engines": ["FreeCAD"],
            "artifacts": [str(output), str(report)],
            "geometry": geometry,
            "stdout": stdout[-2000:],
        }

    async def _prepare_geometry_with_gmsh(self, run_path: Path, source: Path) -> dict[str, Any]:
        """Prepare supported solid CAD through Gmsh's OpenCASCADE kernel.

        This route deliberately accepts only BREP/STEP/IGES solid exchange
        files.  It invokes Gmsh's actual ``healShapes`` operation, then proves
        that one or more volume entities remain.  It does not claim that a
        surface mesh (such as STL) was converted into a watertight solid.
        """
        await self._require(("gmsh",))
        output = run_path / "prepared.brep"
        report = run_path / "geometry-report.json"
        geometry = await asyncio.to_thread(self._gmsh_prepare_geometry, source, output)
        self._write_json(report, geometry)
        if not output.exists() or not report.exists():
            raise EngineeringExecutionError("Gmsh did not publish prepared geometry artifacts.")
        return {
            "engines": ["Gmsh"],
            "artifacts": [str(output), str(report)],
            "geometry": geometry,
        }

    async def _generate_mesh(
        self, project_path: Path, run_path: Path, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        route = self._mesh_route(configuration)
        if route == "cfmesh_cartesian":
            return await self._generate_cfmesh_cartesian_mesh(project_path, run_path, configuration)

        # A CFD mesh is valuable engineering evidence in its own right.  Do
        # not make Gmsh meshing contingent on a solver installation: Gmsh,
        # meshio, VTK, and PyVista own generation, interchange, diagnostics,
        # and the in-app preview.  OpenFOAM conversion/checkMesh is an
        # additional validation path when the local solver is available.
        await self._require(("gmsh", "meshio", "vtk", "pyvista"))
        geometry = self._latest_artifact(project_path, "geometry", "prepared_geometry")
        mesh_file = run_path / "mesh.msh"
        vtk_file = run_path / "mesh.vtk"
        preview_file = run_path / "mesh-preview.png"
        fields = self._fields(configuration)
        base_size = self._number(fields.get("Base size"), 1.0)
        boundary_layers = max(0, int(self._number(fields.get("Boundary layers"), 0)))
        growth_rate = self._number(fields.get("Growth rate"), 1.18)
        requested_boundary_groups = self.normalize_mesh_boundary_groups(configuration)
        boundary_groups = await asyncio.to_thread(
            self._gmsh_volume_mesh,
            geometry,
            mesh_file,
            base_size,
            boundary_layers,
            growth_rate,
            requested_boundary_groups,
        )
        if not mesh_file.exists():
            raise EngineeringExecutionError("Gmsh did not create a volume mesh.")
        quality = await asyncio.to_thread(self._mesh_diagnostics, mesh_file, vtk_file, preview_file)

        boundary_file = run_path / "mesh-boundaries.json"
        self._write_json(boundary_file, boundary_groups)

        engines = ["Gmsh", "meshio", "VTK", "PyVista"]
        artifacts = [str(mesh_file), str(vtk_file), str(preview_file), str(boundary_file)]
        mesh_payload: dict[str, Any] = {
            "gmsh": str(mesh_file),
            "vtk": str(vtk_file),
            "preview": str(preview_file),
            "boundary_groups": boundary_groups,
            "boundary_report": str(boundary_file),
        }
        validation: dict[str, Any] = {"gmsh_vtk": quality}

        openfoam = await self.engines.capability("openfoam", refresh=True)
        if openfoam.status in {"ready", "bundled"}:
            # A partial OpenFOAM installation can expose ``simpleFoam`` while
            # omitting converter or validation utilities.  That must not turn
            # a successful Gmsh/VTK mesh into a failed mesh workflow; defer
            # only the unavailable optional validation.  Once both tools are
            # present, actual conversion/checkMesh failures remain fatal.
            try:
                gmsh_to_foam = self._openfoam_executable("gmshToFoam")
                check_mesh = self._openfoam_executable("checkMesh")
            except EngineeringExecutionError as error:
                validation["openfoam_check"] = {
                    "status": "deferred",
                    "reason": str(error),
                }
            else:
                foam_case = run_path / "openfoam"
                foam_case.mkdir()
                await self._run((gmsh_to_foam, "-case", str(foam_case), str(mesh_file)), run_path)
                check_output = await self._run(
                    (check_mesh, "-case", str(foam_case), "-allGeometry", "-allTopology"),
                    run_path,
                )
                if "Mesh OK" not in check_output:
                    raise EngineeringExecutionError("OpenFOAM checkMesh did not accept the generated mesh.")
                engines.append("OpenFOAM")
                artifacts.append(str(foam_case))
                mesh_payload["openfoam_case"] = str(foam_case)
                validation["openfoam_check"] = {
                    "status": "accepted",
                    "output": check_output[-6000:],
                }
        else:
            validation["openfoam_check"] = {
                "status": "deferred",
                "reason": "OpenFOAM is unavailable; the solver will perform conversion and checkMesh after it is installed.",
            }

        quality_file = run_path / "mesh-quality.json"
        self._write_json(
            quality_file,
            {
                "quality": quality,
                "validation": validation,
                "source_geometry": str(geometry),
                "boundary_layers": boundary_layers,
                "growth_rate": growth_rate,
                "boundary_groups": boundary_groups,
            },
        )
        artifacts.append(str(quality_file))
        return {
            "engines": engines,
            "artifacts": artifacts,
            "mesh": mesh_payload,
            "boundary_groups": boundary_groups,
            "quality": quality,
            "validation": validation,
        }

    async def _generate_cfmesh_cartesian_mesh(
        self, project_path: Path, run_path: Path, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate an OpenFOAM polyMesh through cfMesh cartesianMesh.

        cfMesh is an OpenFOAM-native mesher, so this adapter publishes an
        OpenFOAM case as the canonical mesh artifact.  It still uses Gmsh only
        for the preceding CAD-to-STL surface handoff because cfMesh consumes a
        triangulated surface file, not a STEP/BREP volume directly.
        """
        await self._require(("cfmesh", "gmsh"))
        geometry = self._latest_artifact(project_path, "geometry", "prepared_geometry")
        fields = self._fields(configuration)
        base_size = self._number(fields.get("Base size"), 1.0)
        boundary_layers = max(0, int(self._number(fields.get("Boundary layers"), 0)))
        growth_rate = self._number(fields.get("Growth rate"), 1.18)

        case_path = run_path / "openfoam"
        tri_surface = case_path / "constant" / "triSurface" / "geometry.stl"
        mesh_dict = case_path / "system" / "meshDict"
        control_dict = case_path / "system" / "controlDict"
        check_log = run_path / "cfmesh-checkMesh.log"
        case_path.joinpath("constant", "triSurface").mkdir(parents=True)
        case_path.joinpath("system").mkdir(parents=True)

        await asyncio.to_thread(self._gmsh_export_surface_stl, geometry, tri_surface, base_size)
        self._write_cfmesh_control_dict(control_dict)
        self._write_cfmesh_mesh_dict(
            mesh_dict,
            surface_file=tri_surface.name,
            base_size=base_size,
            boundary_layers=boundary_layers,
            growth_rate=growth_rate,
        )

        cartesian_mesh = await self._engine_executable("cfmesh")
        stdout = await self._run((cartesian_mesh, "-case", str(case_path)), run_path)
        boundary_file = case_path / "constant" / "polyMesh" / "boundary"
        if not boundary_file.exists():
            raise EngineeringExecutionError("cfMesh cartesianMesh did not publish constant/polyMesh/boundary.")

        validation: dict[str, Any] = {
            "cfmesh": {
                "status": "completed",
                "output": stdout[-6000:],
            }
        }
        try:
            check_mesh = self._openfoam_executable("checkMesh")
        except EngineeringExecutionError as error:
            validation["openfoam_check"] = {"status": "deferred", "reason": str(error)}
        else:
            check_output = await self._run(
                (check_mesh, "-case", str(case_path), "-allGeometry", "-allTopology"),
                run_path,
            )
            check_log.write_text(check_output, encoding="utf-8")
            if "Mesh OK" not in check_output:
                raise EngineeringExecutionError("OpenFOAM checkMesh did not accept the cfMesh output.")
            validation["openfoam_check"] = {
                "status": "accepted",
                "output": check_output[-6000:],
            }

        patches = self._read_openfoam_boundary_patches(boundary_file)
        boundary_groups = {
            "surface_source": str(tri_surface),
            "patches": patches,
            "ready_for_solver": bool(patches),
            "guidance": (
                "cfMesh generated OpenFOAM patches from the input STL. Verify inlet, outlet, wall, "
                "and symmetry names in the Physics stage before solving."
            ),
        }
        boundary_report = run_path / "mesh-boundaries.json"
        quality_file = run_path / "mesh-quality.json"
        self._write_json(boundary_report, boundary_groups)
        self._write_json(
            quality_file,
            {
                "quality": {
                    "status": "openfoam_native",
                    "diagnostics": "Use checkMesh output for cfMesh OpenFOAM polyMesh quality.",
                    "patch_count": len(patches),
                },
                "validation": validation,
                "source_geometry": str(geometry),
                "surface_file": str(tri_surface),
                "boundary_layers": boundary_layers,
                "growth_rate": growth_rate,
                "route": "cfmesh_cartesian",
            },
        )

        artifacts = [str(case_path), str(tri_surface), str(mesh_dict), str(boundary_report), str(quality_file)]
        if check_log.exists():
            artifacts.append(str(check_log))
        return {
            "engines": ["cfMesh", "Gmsh", "OpenFOAM" if "accepted" == validation.get("openfoam_check", {}).get("status") else "OpenFOAM checkMesh deferred"],
            "artifacts": artifacts,
            "mesh": {
                "openfoam_case": str(case_path),
                "surface": str(tri_surface),
                "boundary_groups": boundary_groups,
                "boundary_report": str(boundary_report),
                "route": "cfmesh_cartesian",
            },
            "boundary_groups": boundary_groups,
            "quality": self._read_json(quality_file)["quality"],
            "validation": validation,
        }

    async def _write_physics_case(
        self, project_path: Path, run_path: Path, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        """Persist the real, versioned physics recipe consumed by the solver adapter.

        Physics setup is meaningful before a solver is installed.  It records
        the accepted Gmsh mesh plus the optional pre-converted OpenFOAM case;
        the solver adapter performs conversion at run time when necessary.
        """
        mesh = self._latest_payload(project_path, "meshing").get("mesh")
        if not isinstance(mesh, dict):
            raise EngineeringExecutionError("The accepted mesh payload is missing for simulation setup.")
        mesh_file: Path | None = None
        if mesh.get("gmsh"):
            mesh_file = Path(str(mesh["gmsh"]))
            if not mesh_file.exists():
                raise EngineeringExecutionError("The accepted Gmsh mesh artifact no longer exists.")
        openfoam_case = mesh.get("openfoam_case")
        if openfoam_case and not Path(str(openfoam_case)).exists():
            raise EngineeringExecutionError("The accepted OpenFOAM mesh case no longer exists.")
        if mesh_file is None and not openfoam_case:
            raise EngineeringExecutionError(
                "The accepted mesh does not contain either a Gmsh artifact or an OpenFOAM case."
            )
        physics_file = run_path / "physics.json"
        # Persist a canonical, engine-independent boundary recipe at setup
        # time.  The solver later validates these names against the actual
        # OpenFOAM mesh produced by gmshToFoam before writing any field files.
        # This keeps the physics stage useful without an OpenFOAM install
        # while preventing a generic defaultFaces condition from being
        # mistaken for a configured aerodynamic case.
        canonical_configuration = dict(configuration)
        canonical_configuration["boundary_recipe"] = self.normalize_boundary_recipe(configuration)
        payload = {
            "mesh_file": str(mesh_file) if mesh_file else None,
            "openfoam_case": str(openfoam_case) if openfoam_case else None,
            "configuration": canonical_configuration,
        }
        self._write_json(physics_file, payload)
        return {"engines": [], "artifacts": [str(physics_file)], "physics": payload, "physics_file": str(physics_file)}

    async def _run_solver(
        self, project_path: Path, run_path: Path, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        await self._require(("openfoam",))
        physics = self._read_json(self._latest_artifact(project_path, "physics", "physics_file"))
        mesh_file_value = physics.get("mesh_file")
        mesh_file = Path(str(mesh_file_value)) if mesh_file_value else None
        if mesh_file and not mesh_file.exists():
            raise EngineeringExecutionError("The configured Gmsh mesh artifact no longer exists.")
        case_path = run_path / "case"
        prepared_case = Path(str(physics["openfoam_case"])) if physics.get("openfoam_case") else None
        if prepared_case and prepared_case.exists():
            shutil.copytree(prepared_case, case_path)
        else:
            if mesh_file is None:
                raise EngineeringExecutionError("Solver setup requires a Gmsh mesh or an existing OpenFOAM case.")
            case_path.mkdir()
            gmsh_to_foam = self._openfoam_executable("gmshToFoam")
            await self._run((gmsh_to_foam, "-case", str(case_path), str(mesh_file)), run_path)
        case_configuration = self._write_openfoam_case_files(
            case_path, physics["configuration"], configuration
        )
        solver = str(case_configuration["solver"])
        solver_output = await self._run((self._openfoam_executable(solver), "-case", str(case_path)), run_path, timeout=7200)
        log_file = run_path / f"{solver}.log"
        log_file.write_text(solver_output, encoding="utf-8")
        return {
            "engines": ["OpenFOAM"],
            "artifacts": [str(case_path), str(log_file)],
            "solver": {
                "case_path": str(case_path),
                "solver": solver,
                "log": str(log_file),
                "case_configuration": case_configuration,
            },
        }

    async def _process_results(
        self, project_path: Path, run_path: Path, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        await self._require(("openfoam", "vtk", "pyvista"))
        solver = self._latest_payload(project_path, "solver")["solver"]
        case_path = Path(str(solver["case_path"]))
        await self._run((self._openfoam_executable("foamToVTK"), "-case", str(case_path)), run_path)
        vtk_directory = case_path / "VTK"
        datasets = sorted((*vtk_directory.rglob("*.vtk"), *vtk_directory.rglob("*.vtu")), key=lambda item: item.stat().st_mtime)
        if not datasets:
            raise EngineeringExecutionError("foamToVTK completed without producing a VTK dataset.")
        summary = await asyncio.to_thread(self._result_summary, datasets[-1], run_path / "result-preview.png")
        paraview_preview = await self._paraview_preview(datasets[-1], run_path)
        summary_file = run_path / "result-summary.json"
        self._write_json(summary_file, summary)
        engines = ["OpenFOAM", "VTK", "PyVista"]
        artifacts = [str(datasets[-1]), str(summary_file), str(run_path / "result-preview.png")]
        if paraview_preview:
            engines.append("ParaView")
            artifacts.append(str(paraview_preview))
        return {
            "engines": engines,
            "artifacts": artifacts,
            "results": summary,
        }

    async def _publish_report(
        self, project_path: Path, run_path: Path, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a local PDF from published, verified CFD result evidence.

        A report is not a second results generator.  It validates the latest
        VTK result artifact one more time, then lays out the real data summary
        and the PyVista-produced result preview.  Missing or stale evidence is
        an execution failure, never an invitation to render a sample report.
        """
        await self._require(("vtk", "pyvista"))
        results_output = self._latest_payload(project_path, "results")
        results = results_output.get("results")
        if not isinstance(results, dict):
            raise EngineeringExecutionError(
                "A verified VTK/PyVista result summary is required before a report can be generated."
            )

        fields = self._fields(configuration)
        template = str(fields.get("Template") or "Engineering review")
        if template not in {"Engineering review", "Performance summary"}:
            raise EngineeringExecutionError(
                "Report template must be Engineering review or Performance summary."
            )

        evidence = await asyncio.to_thread(
            self._verified_report_evidence,
            project_path,
            results,
        )
        pdf_report = run_path / "report.pdf"
        html_report = run_path / "report.html"
        await asyncio.to_thread(self._write_pdf_report, pdf_report, evidence, template)
        self._write_html_report(html_report, evidence, template)
        if not pdf_report.is_file() or pdf_report.stat().st_size < 4:
            raise EngineeringExecutionError("HX CFD could not publish a readable PDF report.")
        return {
            "engines": ["VTK", "PyVista", "matplotlib"],
            "artifacts": [str(pdf_report), str(html_report)],
            "report": str(pdf_report),
            "report_html": str(html_report),
            "report_evidence": evidence,
        }

    async def _optimize_design(
        self, project_path: Path, run_path: Path, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        """Run user-supplied real CFD evaluations through OpenMDAO and Nevergrad.

        The evaluator is deliberately mandatory. HX CFD never substitutes a
        toy objective when an engineering evaluation is not available.
        """
        await self._require(("openmdao", "nevergrad"))
        fields = self._fields(configuration)
        evaluator = Path(str(fields.get("Evaluator module") or "")).expanduser()
        if not evaluator.is_file():
            raise EngineeringExecutionError("Optimization needs an existing evaluator module with evaluate(design).")
        variable = str(fields.get("Design variable") or "scale")
        lower = self._number(fields.get("Lower bound"), 0.8)
        upper = self._number(fields.get("Upper bound"), 1.2)
        budget = max(1, int(self._number(fields.get("Budget"), 20)))
        if lower >= upper:
            raise EngineeringExecutionError("Optimization lower bound must be less than upper bound.")
        payload = await asyncio.to_thread(
            self._run_openmdao_nevergrad,
            evaluator,
            variable,
            lower,
            upper,
            budget,
            project_path,
        )
        output_file = run_path / "optimization.json"
        self._write_json(output_file, payload)
        return {
            "engines": ["OpenMDAO", "Nevergrad"],
            "artifacts": [str(output_file)],
            "optimization": payload,
        }

    async def _train_surrogate(
        self, project_path: Path, run_path: Path, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatch a project-owned PhysicsNeMo training adapter in a clean process."""
        await self._require(("physicsnemo", "physicsnemo_cfd"))
        fields = self._fields(configuration)
        trainer = Path(str(fields.get("Training module") or "")).expanduser()
        dataset = Path(str(fields.get("Dataset path") or "")).expanduser()
        if not trainer.is_file() or not dataset.exists():
            raise EngineeringExecutionError(
                "Surrogate training needs an existing training module and a labelled local dataset."
            )
        runner = run_path / "run_surrogate.py"
        result_file = run_path / "surrogate.json"
        runner.write_text(
            "\n".join(
                (
                    "import importlib.util, json, sys",
                    "import physicsnemo, physicsnemo.cfd",
                    "module_path, dataset_path, output_path, result_path = sys.argv[1:5]",
                    "spec = importlib.util.spec_from_file_location('hx_cfd_project_trainer', module_path)",
                    "module = importlib.util.module_from_spec(spec)",
                    "spec.loader.exec_module(module)",
                    "if not hasattr(module, 'train'): raise RuntimeError('Training module must export train(dataset_path, output_path)')",
                    "result = module.train(dataset_path, output_path)",
                    "json.dump({'result': result, 'physicsnemo': getattr(physicsnemo, '__version__', 'installed'), 'physicsnemo_cfd': getattr(physicsnemo.cfd, '__version__', 'source')}, open(result_path, 'w', encoding='utf-8'), indent=2, default=str)",
                )
            ),
            encoding="utf-8",
        )
        runtime = await self._engine_executable("physicsnemo")
        model_root = run_path / "model"
        await self._run(
            (runtime, str(runner), str(trainer), str(dataset), str(model_root), str(result_file)),
            run_path,
            timeout=7200,
            environment=self.engines.worker_environment("physicsnemo_cfd"),
        )
        if not result_file.exists():
            raise EngineeringExecutionError("PhysicsNeMo trainer did not publish a training result.")
        # A JSON return value alone is not a trained surrogate.  The adapter
        # owns the output directory passed to the project trainer, so require
        # at least one real model file there and publish every project-owned
        # file as evidence that can be listed/exported by the desktop.
        model_files = sorted(
            (
                path
                for path in model_root.rglob("*")
                if path.is_file() and not path.is_symlink()
            ),
            key=lambda path: path.as_posix(),
        ) if model_root.is_dir() else []
        if not model_files:
            raise EngineeringExecutionError(
                "PhysicsNeMo trainer completed without publishing a model artifact under the assigned output directory."
            )
        model_manifest = run_path / "surrogate-model-manifest.json"
        self._write_json(
            model_manifest,
            {
                "model_root": str(model_root),
                "files": [
                    {
                        "relative_path": path.relative_to(model_root).as_posix(),
                        "size_bytes": path.stat().st_size,
                    }
                    for path in model_files
                ],
            },
        )
        return {
            "engines": ["PhysicsNeMo", "PhysicsNeMo-CFD"],
            "artifacts": [str(result_file), str(model_manifest), *(str(path) for path in model_files)],
            "surrogate": {
                **self._read_json(result_file),
                "model_manifest": str(model_manifest),
                "model_artifact_count": len(model_files),
            },
        }

    async def _require(self, engine_ids: tuple[str, ...]) -> None:
        available, unavailable = await self.engines.requirements_available(engine_ids, refresh=True)
        if not available:
            names = ", ".join(item["display_name"] for item in unavailable)
            raise EngineeringExecutionError(f"Required local engineering engine unavailable: {names}.")

    async def _paraview_preview(self, dataset: Path, run_path: Path) -> Path | None:
        """Use ParaView batch rendering when it is installed; PyVista remains the required path."""
        capability = await self.engines.capability("paraview", refresh=True)
        if capability.status != "ready" or not capability.executable:
            return None
        preview = run_path / "paraview-preview.png"
        script = run_path / "render_paraview.py"
        script.write_text(
            "\n".join(
                (
                    "import sys",
                    "from paraview.simple import *",
                    "reader = OpenDataFile(sys.argv[1])",
                    "view = GetActiveViewOrCreate('RenderView')",
                    "Show(reader, view)",
                    "view.ViewSize = [1600, 900]",
                    "Render()",
                    "SaveScreenshot(sys.argv[2], view)",
                )
            ),
            encoding="utf-8",
        )
        await self._run((capability.executable, str(script), str(dataset), str(preview)), run_path)
        return preview if preview.exists() else None

    async def _engine_executable(self, engine_id: str) -> str:
        capability = await self.engines.capability(engine_id, refresh=True)
        if not capability.executable:
            raise EngineeringExecutionError(f"{capability.display_name} does not expose an executable adapter.")
        return capability.executable

    def _openfoam_executable(self, name: str) -> str:
        openfoam_path = getattr(self.settings, "openfoam_path", None)
        if openfoam_path:
            for location in (
                openfoam_path / "bin" / f"{name}.exe",
                openfoam_path / "bin" / name,
                openfoam_path / f"{name}.exe",
                openfoam_path / name,
            ):
                if location.exists():
                    return str(location)
        executable = shutil.which(f"{name}.exe") or shutil.which(name)
        if not executable:
            raise EngineeringExecutionError(f"OpenFOAM executable '{name}' is not available on the local toolchain.")
        return executable

    async def _cfmesh_executable(self, name: str) -> str:
        if name == "cartesianMesh":
            return await self._engine_executable("cfmesh")
        cfmesh_path = getattr(self.settings, "cfmesh_path", None)
        if cfmesh_path:
            for location in (
                cfmesh_path / "bin" / f"{name}.exe",
                cfmesh_path / "bin" / name,
                cfmesh_path / f"{name}.exe",
                cfmesh_path / name,
            ):
                if location.exists():
                    return str(location)
        executable = shutil.which(f"{name}.exe") or shutil.which(name)
        if not executable:
            raise EngineeringExecutionError(f"cfMesh executable '{name}' is not available on the local toolchain.")
        return executable

    async def _run(
        self,
        arguments: tuple[str, ...],
        cwd: Path,
        timeout: int = 1800,
        environment: dict[str, str] | None = None,
    ) -> str:
        process = await asyncio.create_subprocess_exec(
            *arguments,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, **environment} if environment else None,
        )
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError as error:
            process.kill()
            await process.wait()
            raise EngineeringExecutionError(f"Timed out running {Path(arguments[0]).name}.") from error
        output = stdout.decode(errors="replace")
        if process.returncode != 0:
            raise EngineeringExecutionError(f"{Path(arguments[0]).name} failed: {output[-2000:]}")
        return output

    @staticmethod
    def _validate_geometry_source(source: Path) -> None:
        if not source.exists() or not source.is_file():
            raise EngineeringExecutionError(
                "Geometry execution needs a real local geometry file. Set Source to an existing "
                "STEP, IGES, STL, BREP, or OBJ file."
            )
        if source.suffix.lower() not in FREECAD_GEOMETRY_SOURCE_EXTENSIONS:
            raise EngineeringExecutionError(
                "Geometry preparation accepts STEP, IGES, STL, BREP, and OBJ files."
            )

    @staticmethod
    def _freecad_preparation_script() -> str:
        """Return the isolated FreeCAD worker used for every supported import.

        The worker deliberately does not claim that an arbitrary imported
        triangle mesh is solid.  STL/OBJ data is converted through FreeCAD's
        native mesh-to-shape API and then accepted only when a closed solid
        exists.  That makes the result usable by the subsequent Gmsh volume
        mesher, while keeping an open or invalid surface an actionable
        engineering error instead of a fabricated repair.
        """
        return """import json
import sys

import FreeCAD as App
import Import
import Part

source, output, report = sys.argv[1:4]
source_doc = Import.open(source)
doc = source_doc if source_doc is not None else App.activeDocument()
if doc is None:
    raise RuntimeError('FreeCAD did not create a document for the imported geometry')


def solids_from_shape(shape):
    if shape is None or shape.isNull():
        return []
    try:
        shape = shape.removeSplitter()
    except Exception:
        pass
    solids = list(shape.Solids)
    if solids:
        return solids
    # A mesh-to-shape conversion often yields a closed shell rather than a
    # direct solid.  Only promote shells that FreeCAD itself proves closed.
    for shell in shape.Shells:
        if shell.isClosed():
            try:
                solid = Part.makeSolid(shell)
            except Exception:
                continue
            if not solid.isNull():
                solids.append(solid)
    return solids


solids = []
mesh_objects = 0
for obj in doc.Objects:
    shape = getattr(obj, 'Shape', None)
    object_solids = solids_from_shape(shape)
    solids.extend(object_solids)
    if object_solids:
        continue
    mesh = getattr(obj, 'Mesh', None)
    if mesh is None or getattr(mesh, 'CountFacets', 0) <= 0:
        continue
    mesh_objects += 1
    mesh_shape = Part.Shape()
    # This is FreeCAD's native TopoShape conversion.  It creates a shape from
    # the imported triangles; the closed-solid check above remains mandatory.
    mesh_shape.makeShapeFromMesh(mesh.Topology, 1e-6)
    solids.extend(solids_from_shape(mesh_shape))

if not solids:
    kind = 'surface mesh' if mesh_objects else 'geometry'
    raise RuntimeError(
        'FreeCAD imported the %s but no closed valid solid was available. '
        'Seal or repair the source in FreeCAD before creating a CFD volume mesh.' % kind
    )

prepared = App.newDocument('HXCFDPrepared')
prepared_objects = []
for index, solid in enumerate(solids, start=1):
    if solid.isNull() or not solid.isValid():
        raise RuntimeError('FreeCAD produced an invalid solid during geometry preparation')
    obj = prepared.addObject('Part::Feature', 'Solid_%d' % index)
    obj.Shape = solid
    prepared_objects.append(obj)
prepared.recompute()
Import.export(prepared_objects, output)

bounds = [obj.Shape.BoundBox for obj in prepared_objects]
payload = {
    'source': source,
    'prepared_geometry': output,
    'source_format': source.rsplit('.', 1)[-1].lower() if '.' in source else '',
    'solid_count': len(prepared_objects),
    'valid': all(obj.Shape.isValid() and obj.Shape.Volume > 0 for obj in prepared_objects),
    'volume': sum(obj.Shape.Volume for obj in prepared_objects),
    'area': sum(obj.Shape.Area for obj in prepared_objects),
    'bounds': [
        min(box.XMin for box in bounds), min(box.YMin for box in bounds), min(box.ZMin for box in bounds),
        max(box.XMax for box in bounds), max(box.YMax for box in bounds), max(box.ZMax for box in bounds),
    ],
    'validation': {
        'status': 'accepted_for_volume_meshing',
        'checks': ['FreeCAD import completed', 'at least one valid closed solid was exported'],
    },
    'repair': {
        'operation_invoked': 'FreeCAD removeSplitter and native mesh-to-shape conversion when needed',
        'defeaturing': 'not performed',
    },
}
if not payload['valid']:
    raise RuntimeError('FreeCAD did not produce valid positive-volume solids')
with open(report, 'w', encoding='utf-8') as handle:
    json.dump(payload, handle, indent=2)
"""

    @staticmethod
    def _gmsh_prepare_geometry(source: Path, target: Path) -> dict[str, Any]:
        """Import, conservatively heal, and validate a solid CAD model with OCC.

        Gmsh exposes OpenCASCADE's healing operation, but not a general-purpose
        CAD validity boolean.  The report therefore records exactly what was
        checked: successful OCC import and the presence of volume entities
        after healing.  The ``valid`` flag means "accepted for volume meshing",
        not a stronger claim about the original CAD file.
        """
        import gmsh

        # This adapter runs in ``asyncio.to_thread``.  Disabling Gmsh's signal
        # handler is required on Windows, where Python only permits signal
        # registration from the main interpreter thread.
        _GMSH_API_LOCK.acquire()
        initialized = False
        try:
            gmsh.initialize(interruptible=False)
            initialized = True
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.model.add("hx-cfd-geometry-preparation")
            imported = gmsh.model.occ.importShapes(str(source), highestDimOnly=False)
            if not imported:
                raise EngineeringExecutionError(
                    "Gmsh could not import any CAD entities from the source file."
                )

            # This is a real OpenCASCADE healing pass.  It does not defeature
            # geometry or fabricate closure for an unsupported surface mesh.
            gmsh.model.occ.healShapes(
                tolerance=1e-8,
                fixDegenerated=True,
                fixSmallEdges=True,
                fixSmallFaces=True,
                sewFaces=True,
                makeSolids=True,
            )
            gmsh.model.occ.synchronize()

            volumes = gmsh.model.getEntities(3)
            surfaces = gmsh.model.getEntities(2)
            if not volumes:
                raise EngineeringExecutionError(
                    "Gmsh imported the CAD source but no closed volume remained after OpenCASCADE "
                    "healing. Provide a watertight STEP, IGES, or BREP solid."
                )

            bounds = [float(value) for value in gmsh.model.getBoundingBox(-1, -1)]
            volume = sum(float(gmsh.model.occ.getMass(3, tag)) for _, tag in volumes)
            area = sum(float(gmsh.model.occ.getMass(2, tag)) for _, tag in surfaces)
            # Surface entity IDs are the deliberately explicit hand-off from
            # geometry preparation to meshing.  They let an engineer select
            # inlet/outlet/wall/symmetry faces in the next stage without HX
            # CFD guessing flow direction from a bounding box.
            surface_details = [
                {
                    "surface_id": int(tag),
                    "area": float(gmsh.model.occ.getMass(2, tag)),
                    "bounds": [float(value) for value in gmsh.model.getBoundingBox(2, tag)],
                }
                for _, tag in sorted(surfaces, key=lambda entity: entity[1])
            ]
            gmsh.write(str(target))
            return {
                "source": str(source),
                "prepared_geometry": str(target),
                "source_format": source.suffix.lower().lstrip("."),
                "solid_count": len(volumes),
                "surface_count": len(surfaces),
                "surfaces": surface_details,
                "valid": True,
                "volume": volume,
                "area": area,
                "bounds": bounds,
                "validation": {
                    "status": "accepted_for_volume_meshing",
                    "checks": [
                        "OpenCASCADE import completed",
                        "at least one volume entity remained after healing",
                    ],
                },
                "repair": {
                    "operation_invoked": "Gmsh OpenCASCADE healShapes",
                    "options": {
                        "fix_degenerated": True,
                        "fix_small_edges": True,
                        "fix_small_faces": True,
                        "sew_faces": True,
                        "make_solids": True,
                    },
                    "defeaturing": "not performed",
                },
                "gmsh_version": getattr(gmsh, "__version__", "installed"),
            }
        finally:
            try:
                if initialized:
                    gmsh.finalize()
            finally:
                _GMSH_API_LOCK.release()

    @staticmethod
    def _gmsh_volume_mesh(
        source: Path,
        target: Path,
        base_size: float,
        boundary_layers: int,
        growth_rate: float,
        requested_boundary_groups: dict[str, Any],
    ) -> dict[str, Any]:
        import gmsh

        # This helper is called from ``asyncio.to_thread`` as well.
        _GMSH_API_LOCK.acquire()
        initialized = False
        try:
            gmsh.initialize(interruptible=False)
            initialized = True
            gmsh.option.setNumber("General.Terminal", 1)
            gmsh.model.add("hx-cfd")
            gmsh.model.occ.importShapes(str(source))
            gmsh.model.occ.synchronize()
            volumes = sorted(gmsh.model.getEntities(3), key=lambda entity: entity[1])
            surfaces = sorted(gmsh.model.getEntities(2), key=lambda entity: entity[1])
            if not volumes:
                raise EngineeringExecutionError("The prepared CAD file contains no volume entities for meshing.")
            if not surfaces:
                raise EngineeringExecutionError("The prepared CAD file contains no surface entities for meshing.")

            boundary_groups = EngineeringOrchestrator._assign_gmsh_boundary_groups(
                gmsh,
                [tag for _, tag in surfaces],
                [tag for _, tag in volumes],
                requested_boundary_groups,
            )
            gmsh.option.setNumber("Mesh.CharacteristicLengthMin", max(base_size * 0.25, 1e-6))
            gmsh.option.setNumber("Mesh.CharacteristicLengthMax", max(base_size, 1e-6))
            if boundary_layers:
                field = gmsh.model.mesh.field.add("BoundaryLayer")
                faces = [tag for _, tag in surfaces]
                if not faces:
                    raise EngineeringExecutionError("Boundary layers require surface entities in the CAD model.")
                gmsh.model.mesh.field.setNumbers(field, "FacesList", faces)
                gmsh.model.mesh.field.setNumber("hwall_n", max(base_size * 0.05, 1e-7))
                gmsh.model.mesh.field.setNumber("ratio", max(growth_rate, 1.0))
                gmsh.model.mesh.field.setNumber("thickness", base_size * boundary_layers)
                gmsh.model.mesh.field.setNumber("nLayers", boundary_layers)
                gmsh.model.mesh.field.setAsBoundaryLayer(field)
            gmsh.model.mesh.generate(3)
            gmsh.write(str(target))
            return boundary_groups
        finally:
            try:
                if initialized:
                    gmsh.finalize()
            finally:
                _GMSH_API_LOCK.release()

    @staticmethod
    def _gmsh_export_surface_stl(source: Path, target: Path, base_size: float) -> None:
        import gmsh

        _GMSH_API_LOCK.acquire()
        initialized = False
        try:
            gmsh.initialize(interruptible=False)
            initialized = True
            gmsh.option.setNumber("General.Terminal", 1)
            gmsh.model.add("hx-cfd-cfmesh-surface")
            gmsh.model.occ.importShapes(str(source))
            gmsh.model.occ.synchronize()
            surfaces = sorted(gmsh.model.getEntities(2), key=lambda entity: entity[1])
            if not surfaces:
                raise EngineeringExecutionError("The prepared CAD file contains no surfaces for cfMesh export.")
            gmsh.option.setNumber("Mesh.CharacteristicLengthMin", max(base_size * 0.25, 1e-6))
            gmsh.option.setNumber("Mesh.CharacteristicLengthMax", max(base_size, 1e-6))
            gmsh.model.mesh.generate(2)
            gmsh.write(str(target))
            if not target.exists():
                raise EngineeringExecutionError("Gmsh did not export the cfMesh STL surface.")
        finally:
            try:
                if initialized:
                    gmsh.finalize()
            finally:
                _GMSH_API_LOCK.release()

    @staticmethod
    def _write_cfmesh_control_dict(path: Path) -> None:
        path.write_text(
            """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}

application     cartesianMesh;
startFrom       latestTime;
startTime       0;
stopAt          endTime;
endTime         1;
deltaT          1;
writeControl    timeStep;
writeInterval   1;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;
""",
            encoding="utf-8",
        )

    @staticmethod
    def _write_cfmesh_mesh_dict(
        path: Path,
        surface_file: str,
        base_size: float,
        boundary_layers: int,
        growth_rate: float,
    ) -> None:
        boundary_section = ""
        if boundary_layers:
            boundary_section = f"""

boundaryLayers
{{
    nLayers           {boundary_layers};
    thicknessRatio    {max(growth_rate, 1.0):.6g};
    maxFirstLayerThickness {max(base_size * 0.05, 1e-7):.6g};
}}
"""
        path.write_text(
            f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      meshDict;
}}

surfaceFile "{surface_file}";

maxCellSize      {max(base_size, 1e-6):.6g};
boundaryCellSize {max(base_size, 1e-6):.6g};
minCellSize      {max(base_size * 0.25, 1e-7):.6g};
{boundary_section}
""",
            encoding="utf-8",
        )

    @staticmethod
    def normalize_mesh_boundary_groups(meshing_configuration: dict[str, Any]) -> dict[str, Any]:
        """Normalize explicit Gmsh surface selections into a stable recipe.

        Surface entity IDs are intentionally the only selection mechanism in
        this adapter.  They are published by the geometry report and validated
        against the prepared CAD during meshing.  This prevents convenient but
        unsafe guesses such as identifying the lowest-X face as an inlet.

        ``unassigned_surface_policy`` controls faces that the engineer did not
        place in a role.  ``unassigned`` keeps them as an explicitly named
        diagnostic patch; ``walls`` combines them into the named ``walls``
        group.  The latter is available only by an explicit user choice.
        """
        if not isinstance(meshing_configuration, dict):
            raise EngineeringExecutionError("Meshing configuration must be a JSON object.")
        fields = EngineeringOrchestrator._fields(meshing_configuration)
        raw_groups = meshing_configuration.get("boundary_groups")
        if raw_groups is not None and not isinstance(raw_groups, dict):
            raise EngineeringExecutionError("Meshing boundary groups must be a JSON object.")
        groups = raw_groups if isinstance(raw_groups, dict) else {}

        selected: dict[str, list[int]] = {}
        for role, label in _GMSH_BOUNDARY_FIELD_NAMES.items():
            # Desktop fields take precedence so a reconfigured stage cannot
            # accidentally retain selections from an older saved recipe.
            value = fields[label] if label in fields else groups.get(role, groups.get(f"{role}s"))
            selected[role] = EngineeringOrchestrator._surface_entity_ids(value, label)

        policy_value = fields.get(
            "Unassigned surfaces",
            groups.get("unassigned_surface_policy", groups.get("unassigned_surfaces", "unassigned")),
        )
        if policy_value is None:
            policy_value = "unassigned"
        policy_key = str(policy_value).strip().lower()
        policy = _GMSH_UNASSIGNED_SURFACE_POLICIES.get(policy_key)
        if policy is None:
            allowed = "Keep as unassigned patch or Group remaining as walls"
            raise EngineeringExecutionError(
                f"Unassigned surfaces must be one of: {allowed}."
            )

        assigned: dict[int, str] = {}
        for role, tags in selected.items():
            for tag in tags:
                existing = assigned.get(tag)
                if existing is not None:
                    raise EngineeringExecutionError(
                        f"Surface ID {tag} is assigned to both {existing} and {role}. "
                        "Assign every CAD surface to at most one boundary role."
                    )
                assigned[tag] = role

        return {
            "inlet": selected["inlet"],
            "outlet": selected["outlet"],
            "wall": selected["wall"],
            "symmetry": selected["symmetry"],
            "unassigned_surface_policy": policy,
        }

    @staticmethod
    def _surface_entity_ids(value: Any, label: str) -> list[int]:
        """Parse a non-ambiguous list of positive Gmsh surface entity IDs."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return []
        if isinstance(value, str):
            raw_values: list[Any] = [part.strip() for part in re.split(r"[,;\s]+", value.strip())]
        elif isinstance(value, (list, tuple)):
            raw_values = list(value)
        else:
            raise EngineeringExecutionError(f"{label} must be a comma-separated list of positive surface IDs.")

        tags: list[int] = []
        for raw_value in raw_values:
            if isinstance(raw_value, bool):
                raise EngineeringExecutionError(f"{label} must contain positive integer surface IDs.")
            try:
                numeric = float(raw_value)
            except (TypeError, ValueError) as error:
                raise EngineeringExecutionError(
                    f"{label} must contain positive integer surface IDs."
                ) from error
            if not numeric.is_integer() or numeric <= 0:
                raise EngineeringExecutionError(f"{label} must contain positive integer surface IDs.")
            tag = int(numeric)
            if tag in tags:
                raise EngineeringExecutionError(f"{label} contains duplicate surface ID {tag}.")
            tags.append(tag)
        return tags

    @staticmethod
    def _assign_gmsh_boundary_groups(
        gmsh: Any,
        surface_tags: list[int],
        volume_tags: list[int],
        requested: dict[str, Any],
    ) -> dict[str, Any]:
        """Create real named physical groups for every exterior face.

        Gmsh writes only elements in physical groups once any group exists.
        Therefore this method creates a 3-D ``fluid`` group and always puts
        every remaining exterior face in an explicit ``unassigned`` or
        user-approved ``walls`` group.  The unassigned group is deliberately
        not a CFD role: the OpenFOAM recipe validator will stop a solver run
        until the engineer assigns it a role.
        """
        available = sorted({int(tag) for tag in surface_tags})
        if not available:
            raise EngineeringExecutionError("The prepared CAD file contains no surface IDs to group.")
        if not volume_tags:
            raise EngineeringExecutionError("The prepared CAD file contains no volume IDs to mesh.")

        selections = {
            role: [int(tag) for tag in requested.get(role, [])]
            for role in _GMSH_BOUNDARY_ROLE_NAMES
        }
        known = set(available)
        for role, tags in selections.items():
            unavailable = sorted(set(tags) - known)
            if unavailable:
                raise EngineeringExecutionError(
                    f"{_GMSH_BOUNDARY_FIELD_NAMES[role]} include unavailable surface ID(s): "
                    f"{', '.join(str(tag) for tag in unavailable)}. Available surface IDs: "
                    f"{', '.join(str(tag) for tag in available)}."
                )

        assigned: dict[int, str] = {}
        for role, tags in selections.items():
            for tag in tags:
                existing = assigned.get(tag)
                if existing is not None:
                    raise EngineeringExecutionError(
                        f"Surface ID {tag} is assigned to both {existing} and {role}."
                    )
                assigned[tag] = role

        unassigned = sorted(set(available) - set(assigned))
        policy = str(requested.get("unassigned_surface_policy") or "unassigned")
        if policy not in {"unassigned", "walls"}:
            raise EngineeringExecutionError("Meshing boundary-group policy is invalid.")
        if policy == "walls":
            selections["wall"] = sorted(set(selections["wall"]) | set(unassigned))
            unassigned = []

        physical_groups: list[dict[str, Any]] = []
        for role, physical_name in _GMSH_BOUNDARY_ROLE_NAMES.items():
            tags = selections[role]
            if not tags:
                continue
            physical_tag = int(gmsh.model.addPhysicalGroup(2, tags))
            gmsh.model.setPhysicalName(2, physical_tag, physical_name)
            physical_groups.append(
                {
                    "role": role,
                    "name": physical_name,
                    "dimension": 2,
                    "physical_tag": physical_tag,
                    "surface_ids": tags,
                }
            )

        # Even when an engineer has not assigned a CFD role yet, preserve the
        # actual exterior triangles in the MSH artifact and expose the gap.
        # This is a diagnostic group, never a fabricated boundary condition.
        if unassigned:
            physical_tag = int(gmsh.model.addPhysicalGroup(2, unassigned))
            gmsh.model.setPhysicalName(2, physical_tag, "unassigned")
            physical_groups.append(
                {
                    "role": "unassigned",
                    "name": "unassigned",
                    "dimension": 2,
                    "physical_tag": physical_tag,
                    "surface_ids": unassigned,
                }
            )

        fluid_physical_tag = int(gmsh.model.addPhysicalGroup(3, volume_tags))
        gmsh.model.setPhysicalName(3, fluid_physical_tag, "fluid")
        ready_for_solver = (
            bool(selections["inlet"])
            and bool(selections["outlet"])
            and not unassigned
        )
        return {
            "surface_ids": available,
            "physical_groups": physical_groups,
            "volume_group": {
                "name": "fluid",
                "dimension": 3,
                "physical_tag": fluid_physical_tag,
                "volume_ids": [int(tag) for tag in volume_tags],
            },
            "unassigned_surface_ids": unassigned,
            "unassigned_surface_policy": policy,
            "ready_for_solver": ready_for_solver,
            "guidance": (
                "Select at least one inlet and outlet surface ID, then assign every remaining "
                "surface to walls or symmetry before running OpenFOAM."
                if not ready_for_solver
                else "Every surface has a named physical group and inlet/outlet are explicitly selected."
            ),
        }

    @staticmethod
    def _read_openfoam_boundary_patches(boundary_file: Path) -> list[dict[str, Any]]:
        text = boundary_file.read_text(encoding="utf-8", errors="replace")
        patches: list[dict[str, Any]] = []
        for match in _OPENFOAM_BOUNDARY_ENTRY.finditer(text):
            name = match.group("name")
            if name in {"FoamFile", "boundary"}:
                continue
            body = match.group("body")
            type_match = _OPENFOAM_BOUNDARY_TYPE.search(body)
            patches.append(
                {
                    "name": name,
                    "type": type_match.group("type") if type_match else "unknown",
                }
            )
        return patches

    @staticmethod
    def _mesh_diagnostics(mesh_file: Path, vtk_file: Path, preview_file: Path) -> dict[str, Any]:
        import meshio
        import pyvista as pv
        from vtkmodules.vtkCommonCore import vtkVersion

        mesh = meshio.read(mesh_file)
        # Gmsh's physical/entity sets are useful in the source ``.msh`` file,
        # but meshio's legacy VTK writer attempts to materialize every set as
        # cell data.  Mixed-dimensional Gmsh groups can contain negative
        # indices at that conversion boundary on Windows.  The visualisation
        # artifact only needs topology and coordinates; keep the canonical
        # Gmsh file untouched and publish a clean, set-free VTK derivative.
        vtk_mesh = meshio.Mesh(points=mesh.points, cells=mesh.cells)
        meshio.write(vtk_file, vtk_mesh)
        dataset = pv.read(vtk_file)
        # PyVista 0.48 renamed ``compute_cell_quality`` to ``cell_quality``.
        # Support both adapter contracts because the bundled local toolchain
        # can be upgraded independently of the desktop shell.
        if hasattr(dataset, "cell_quality"):
            quality = dataset.cell_quality("scaled_jacobian")
            values = quality.cell_data.get("scaled_jacobian")
        else:
            quality = dataset.compute_cell_quality(quality_measure="scaled_jacobian")
            values = quality.cell_data.get("CellQuality")
        if values is None or len(values) == 0:
            raise EngineeringExecutionError("VTK did not produce mesh quality values.")
        valid_values = values[values >= 0]
        if len(valid_values) == 0:
            raise EngineeringExecutionError("VTK did not produce valid volumetric mesh quality values.")
        plotter = pv.Plotter(off_screen=True)
        try:
            plotter.add_mesh(dataset, style="wireframe", color="#75c7ff", line_width=1)
            plotter.screenshot(str(preview_file))
        finally:
            plotter.close()
        return {
            "points": int(dataset.n_points),
            "cells": int(dataset.n_cells),
            "bounds": [float(value) for value in dataset.bounds],
            "cell_types": {block.type: int(len(block.data)) for block in mesh.cells},
            "scaled_jacobian": {
                "min": float(valid_values.min()),
                "max": float(valid_values.max()),
                "mean": float(valid_values.mean()),
            },
            "vtk_version": vtkVersion.GetVTKVersion(),
        }

    @staticmethod
    def _run_openmdao_nevergrad(
        evaluator_path: Path,
        variable: str,
        lower: float,
        upper: float,
        budget: int,
        project_path: Path,
    ) -> dict[str, Any]:
        import nevergrad as ng
        import openmdao.api as om

        spec = importlib.util.spec_from_file_location("hx_cfd_project_evaluator", evaluator_path)
        if spec is None or spec.loader is None:
            raise EngineeringExecutionError("Could not load the optimization evaluator module.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        evaluator = getattr(module, "evaluate", None)
        if not callable(evaluator):
            raise EngineeringExecutionError("Optimization evaluator module must export evaluate(design).")

        class EngineeringEvaluation(om.ExplicitComponent):
            def setup(self) -> None:
                self.add_input("design_value", val=lower)
                self.add_output("objective", val=0.0)

            def compute(self, inputs: Any, outputs: Any) -> None:
                design = {variable: float(inputs["design_value"][0]), "project_path": str(project_path)}
                outputs["objective"] = float(evaluator(design))

        problem = om.Problem(reports=False)
        problem.model.add_subsystem("design", om.IndepVarComp("design_value", lower), promotes=["*"])
        problem.model.add_subsystem("engineering_evaluation", EngineeringEvaluation(), promotes=["*"])
        problem.setup()
        optimizer = ng.optimizers.OnePlusOne(
            parametrization=ng.p.Scalar(init=lower).set_bounds(lower, upper),
            budget=budget,
        )
        history: list[dict[str, float]] = []
        for _ in range(budget):
            candidate = optimizer.ask()
            problem.set_val("design_value", candidate.value)
            problem.run_model()
            objective = float(problem.get_val("objective")[0])
            if not math.isfinite(objective):
                raise EngineeringExecutionError(
                    "Optimization evaluator returned a non-finite objective; "
                    "publish a finite scalar objective for every CFD evaluation."
                )
            optimizer.tell(candidate, objective)
            history.append({"design_value": float(candidate.value), "objective": objective})
        recommendation = optimizer.provide_recommendation()
        return {"variable": variable, "recommended_value": float(recommendation.value), "history": history}

    @staticmethod
    def _result_summary(dataset_path: Path, preview_path: Path) -> dict[str, Any]:
        import pyvista as pv
        from vtkmodules.vtkCommonCore import vtkVersion

        dataset = pv.read(dataset_path)
        plotter = pv.Plotter(off_screen=True)
        plotter.add_mesh(dataset, scalars=dataset.array_names[0] if dataset.array_names else None)
        plotter.screenshot(str(preview_path))
        return {
            "dataset": str(dataset_path),
            "points": int(dataset.n_points),
            "cells": int(dataset.n_cells),
            "bounds": [float(value) for value in dataset.bounds],
            "arrays": list(dataset.array_names),
            "preview": str(preview_path),
            "vtk_version": vtkVersion.GetVTKVersion(),
        }

    @staticmethod
    def _verified_report_evidence(project_path: Path, reported: dict[str, Any]) -> dict[str, Any]:
        """Re-open published result evidence before it enters a report.

        The results stage is responsible for producing this evidence.  The
        report stage deliberately reads the VTK artifact again instead of
        trusting a mutable JSON summary or assembling a sample document from
        configuration values.  That makes stale references, deleted files,
        and manually modified evidence visible as a report failure.
        """
        dataset_path = EngineeringOrchestrator._project_owned_file(
            project_path, reported.get("dataset"), "The published VTK result dataset"
        )
        preview_path = EngineeringOrchestrator._project_owned_file(
            project_path, reported.get("preview"), "The published result preview"
        )
        try:
            import matplotlib

            matplotlib.use("Agg", force=True)
            from matplotlib import image as mpimg
            import pyvista as pv

            dataset = pv.read(dataset_path)
            # Decode the image now.  A copied or corrupted non-image file
            # must not result in a seemingly valid report with no real visual
            # evidence on its second page.
            preview_image = mpimg.imread(str(preview_path))
        except Exception as error:
            raise EngineeringExecutionError(
                "HX CFD could not re-open the published VTK/PyVista result evidence for reporting."
            ) from error

        actual = {
            "points": int(dataset.n_points),
            "cells": int(dataset.n_cells),
            "bounds": [float(value) for value in dataset.bounds],
            "arrays": [str(name) for name in dataset.array_names],
        }
        EngineeringOrchestrator._validate_report_summary(reported, actual)
        return {
            "dataset": str(dataset_path),
            "dataset_name": dataset_path.name,
            "preview": str(preview_path),
            "preview_name": preview_path.name,
            "points": actual["points"],
            "cells": actual["cells"],
            "bounds": actual["bounds"],
            "arrays": actual["arrays"],
            "preview_shape": [int(value) for value in preview_image.shape],
            "vtk_version": str(reported.get("vtk_version") or "verified locally"),
        }

    @staticmethod
    def _project_owned_file(project_path: Path, raw_path: Any, label: str) -> Path:
        """Resolve one published evidence file without allowing path escape."""
        if not isinstance(raw_path, (str, os.PathLike)):
            raise EngineeringExecutionError(f"{label} is missing.")
        try:
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                raise ValueError("not absolute")
            resolved = candidate.resolve(strict=True)
            root = project_path.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, RuntimeError, ValueError) as error:
            raise EngineeringExecutionError(f"{label} is no longer a project-owned file.") from error
        if not resolved.is_file():
            raise EngineeringExecutionError(f"{label} is no longer available.")
        return resolved

    @staticmethod
    def _validate_report_summary(reported: dict[str, Any], actual: dict[str, Any]) -> None:
        """Reject a summary when it no longer describes the actual VTK file."""
        for key in ("points", "cells"):
            value = reported.get(key)
            if value is None:
                continue
            if isinstance(value, bool):
                raise EngineeringExecutionError(f"The published result summary has an invalid {key} value.")
            try:
                matches = int(value) == actual[key]
            except (TypeError, ValueError) as error:
                raise EngineeringExecutionError(
                    f"The published result summary has an invalid {key} value."
                ) from error
            if not matches:
                raise EngineeringExecutionError(
                    f"The published result summary no longer matches the VTK dataset ({key})."
                )

        bounds = reported.get("bounds")
        if bounds is not None:
            if not isinstance(bounds, (list, tuple)) or len(bounds) != len(actual["bounds"]):
                raise EngineeringExecutionError("The published result summary has invalid bounds.")
            try:
                matches_bounds = all(
                    math.isclose(float(expected), observed, rel_tol=1e-9, abs_tol=1e-12)
                    for expected, observed in zip(bounds, actual["bounds"])
                )
            except (TypeError, ValueError) as error:
                raise EngineeringExecutionError("The published result summary has invalid bounds.") from error
            if not matches_bounds:
                raise EngineeringExecutionError(
                    "The published result summary no longer matches the VTK dataset bounds."
                )

        arrays = reported.get("arrays")
        if arrays is not None:
            if not isinstance(arrays, list) or sorted(str(name) for name in arrays) != sorted(actual["arrays"]):
                raise EngineeringExecutionError(
                    "The published result summary no longer matches the VTK dataset arrays."
                )

    @staticmethod
    def _write_pdf_report(report_path: Path, evidence: dict[str, Any], template: str) -> None:
        """Render a portable PDF with only verified local CFD evidence."""
        import matplotlib

        matplotlib.use("Agg", force=True)
        from matplotlib import image as mpimg
        from matplotlib.backends.backend_pdf import PdfPages
        from matplotlib.figure import Figure

        bounds = evidence["bounds"]
        array_names = evidence["arrays"]
        summary_lines = [
            f"Template: {template}",
            f"Verified dataset: {evidence['dataset_name']}",
            f"Points: {evidence['points']:,}",
            f"Cells: {evidence['cells']:,}",
            "Bounds: " + ", ".join(f"{float(value):.6g}" for value in bounds),
            "Available fields: " + (", ".join(array_names) if array_names else "No field arrays published"),
            f"VTK evidence: {evidence['vtk_version']}",
        ]
        if template == "Engineering review":
            summary_lines.insert(
                1,
                "Evidence scope: verified solver-result dataset and rendered local result view.",
            )

        with PdfPages(report_path) as pdf:
            summary = Figure(figsize=(11.69, 8.27), facecolor="white")
            summary_ax = summary.add_axes((0.07, 0.10, 0.86, 0.80))
            summary_ax.axis("off")
            summary_ax.text(
                0.0,
                0.98,
                "HX CFD Engineering Report",
                fontsize=22,
                fontweight="bold",
                va="top",
            )
            summary_ax.text(
                0.0,
                0.86,
                "\n\n".join(summary_lines),
                fontsize=12,
                va="top",
                family="monospace",
                wrap=True,
            )
            pdf.savefig(summary)

            image = mpimg.imread(str(evidence["preview"]))
            visual = Figure(figsize=(11.69, 8.27), facecolor="white")
            visual_ax = visual.add_axes((0.05, 0.08, 0.90, 0.78))
            visual_ax.imshow(image)
            visual_ax.axis("off")
            visual.suptitle(
                f"Verified result view · {evidence['preview_name']}",
                fontsize=16,
                fontweight="bold",
                y=0.94,
            )
            pdf.savefig(visual)

    @staticmethod
    def _write_html_report(report_path: Path, evidence: dict[str, Any], template: str) -> None:
        """Write a readable local companion without inventing engineering data."""
        rows = "".join(
            f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>"
            for label, value in (
                ("Template", template),
                ("Verified dataset", str(evidence["dataset_name"])),
                ("Points", f"{int(evidence['points']):,}"),
                ("Cells", f"{int(evidence['cells']):,}"),
                ("Bounds", ", ".join(f"{float(value):.6g}" for value in evidence["bounds"])),
                ("Available fields", ", ".join(evidence["arrays"]) or "No field arrays published"),
                ("VTK evidence", str(evidence["vtk_version"])),
            )
        )
        report_path.write_text(
            "<!doctype html><html><head><meta charset=\"utf-8\"><title>HX CFD Engineering Report</title>"
            "<style>body{font-family:Arial,sans-serif;margin:2rem;color:#111}"
            "table{border-collapse:collapse;max-width:64rem}th,td{border:1px solid #bbb;padding:.5rem;text-align:left}"
            "th{background:#eee}</style></head><body><h1>HX CFD Engineering Report</h1>"
            "<p>This companion contains only verified local result evidence. The PDF contains the rendered result view.</p>"
            f"<table>{rows}</table></body></html>",
            encoding="utf-8",
        )

    @staticmethod
    def _write_openfoam_case_files(
        case_path: Path, physics_configuration: dict[str, Any], solver_configuration: dict[str, Any]
    ) -> dict[str, Any]:
        """Write an OpenFOAM recipe that matches the saved desktop selections.

        This is deliberately an incompressible RANS path.  A requested energy
        equation is rejected instead of silently launching ``simpleFoam`` or
        ``pimpleFoam`` without a thermal model.
        """
        fields = EngineeringOrchestrator._fields(physics_configuration)
        run_fields = EngineeringOrchestrator._fields(solver_configuration)
        system = case_path / "system"
        zero = case_path / "0"
        constant = case_path / "constant"
        system.mkdir(exist_ok=True)
        zero.mkdir(exist_ok=True)
        constant.mkdir(exist_ok=True)

        boundary_recipe = EngineeringOrchestrator.normalize_boundary_recipe(physics_configuration)
        mesh_patches = EngineeringOrchestrator._validate_and_apply_boundary_patch_types(
            case_path, boundary_recipe
        )

        energy_equation = str(fields.get("Energy equation") or "Disabled")
        if energy_equation != "Disabled":
            raise EngineeringExecutionError(
                "Energy equation is enabled, but the current local wind-tunnel adapter only "
                "writes incompressible RANS cases. Disable it or provide a validated thermal "
                "OpenFOAM case before running the solver."
            )

        fluid = str(fields.get("Fluid") or "Air (ideal gas)")
        fluid_properties = {
            "Air (ideal gas)": {"nu": 1.5e-5, "density": 1.225},
            "Water (liquid)": {"nu": 1.0e-6, "density": 998.2},
        }
        if fluid not in fluid_properties:
            raise EngineeringExecutionError(f"Unsupported fluid selection: {fluid}.")
        properties = fluid_properties[fluid]

        turbulence_label = str(fields.get("Turbulence model") or "k-ω SST")
        turbulence_models = {
            "k-ω SST": ("kOmegaSST", "omega"),
            "k-ε Realizable": ("realizableKE", "epsilon"),
        }
        if turbulence_label not in turbulence_models:
            raise EngineeringExecutionError(f"Unsupported turbulence model: {turbulence_label}.")
        turbulence, turbulence_field = turbulence_models[turbulence_label]

        iterations = int(EngineeringOrchestrator._number(run_fields.get("Maximum iterations"), 5000))
        if iterations < 1:
            raise EngineeringExecutionError("Maximum iterations must be at least 1.")
        residual_target = EngineeringOrchestrator._number(run_fields.get("Residual target"), 1e-5)
        if not 0 < residual_target < 1:
            raise EngineeringExecutionError("Residual target must be greater than 0 and less than 1.")
        reference_pressure = EngineeringOrchestrator._number(fields.get("Reference pressure"), 101325.0)
        if reference_pressure <= 0:
            raise EngineeringExecutionError("Reference pressure must be greater than 0 Pa.")

        solver = EngineeringOrchestrator._solver_name(solver_configuration)
        transient = solver == "pimpleFoam"
        algorithm = "PIMPLE" if transient else "SIMPLE"
        ddt_scheme = "Euler" if transient else "steadyState"
        # In incompressible OpenFOAM solvers p is kinematic pressure. Keep
        # the supplied Pascal reference traceable by converting it with the
        # selected fluid density instead of writing incompatible units.
        kinematic_reference_pressure = reference_pressure / float(properties["density"])

        (system / "controlDict").write_text(
            "\n".join(
                (
                    f"application {solver};",
                    "startFrom startTime;",
                    "startTime 0;",
                    "stopAt endTime;",
                    f"endTime {iterations};",
                    "deltaT 1;",
                    "writeControl timeStep;",
                    "writeInterval 100;",
                    "",
                )
            ),
            encoding="utf-8",
        )
        (system / "fvSchemes").write_text(
            "\n".join(
                (
                    f"ddtSchemes {{ default {ddt_scheme}; }}",
                    "divSchemes { default none; }",
                    "gradSchemes { default Gauss linear; }",
                    "laplacianSchemes { default Gauss linear corrected; }",
                    "interpolationSchemes { default linear; }",
                    "snGradSchemes { default corrected; }",
                    "",
                )
            ),
            encoding="utf-8",
        )
        (system / "fvSolution").write_text(
            "\n".join(
                (
                    "solvers",
                    "{",
                    f"    p {{ solver GAMG; tolerance {residual_target:.9g}; relTol 0; }}",
                    f"    U {{ solver smoothSolver; tolerance {residual_target:.9g}; relTol 0; }}",
                    f"    k {{ solver smoothSolver; tolerance {residual_target:.9g}; relTol 0; }}",
                    f"    {turbulence_field} {{ solver smoothSolver; tolerance {residual_target:.9g}; relTol 0; }}",
                    "}",
                    algorithm,
                    "{",
                    "    nNonOrthogonalCorrectors 0;",
                    "    pRefCell 0;",
                    f"    pRefValue {kinematic_reference_pressure:.9g};",
                    "}",
                    "",
                )
            ),
            encoding="utf-8",
        )
        (constant / "transportProperties").write_text(
            "\n".join(
                (
                    "transportModel Newtonian;",
                    f"nu [0 2 -1 0 0 0 0] {float(properties['nu']):.9g};",
                    "",
                )
            ),
            encoding="utf-8",
        )
        (constant / "turbulenceProperties").write_text(
            "\n".join(
                (
                    "simulationType RAS;",
                    "RAS",
                    "{",
                    f"    RASModel {turbulence};",
                    "    turbulence on;",
                    "    printCoeffs on;",
                    "}",
                    "",
                )
            ),
            encoding="utf-8",
        )
        inlet_turbulence = {
            entry["name"]: EngineeringOrchestrator._inlet_turbulence_values(entry)
            for entry in boundary_recipe["patches"]
            if entry["role"] == "inlet"
        }
        # An initial turbulent state is needed in the volume before boundary
        # conditions take over.  With more than one inlet, use the largest
        # prescribed turbulent kinetic energy rather than silently selecting
        # an arbitrary inlet based on list order.
        initial_turbulence = max(inlet_turbulence.values(), key=lambda values: values["k"])
        velocity_conditions: dict[str, dict[str, str]] = {}
        pressure_conditions: dict[str, dict[str, str]] = {}
        k_conditions: dict[str, dict[str, str]] = {}
        turbulence_conditions: dict[str, dict[str, str]] = {}
        nut_conditions: dict[str, dict[str, str]] = {}
        for entry in boundary_recipe["patches"]:
            patch_name = str(entry["name"])
            role = str(entry["role"])
            if role == "inlet":
                velocity = " ".join(f"{component:.9g}" for component in entry["velocity"])
                turbulence_values = inlet_turbulence[patch_name]
                velocity_conditions[patch_name] = {
                    "type": "fixedValue",
                    "value": f"uniform ({velocity})",
                }
                pressure_conditions[patch_name] = {"type": "zeroGradient"}
                k_conditions[patch_name] = {
                    "type": "fixedValue",
                    "value": f"uniform {turbulence_values['k']:.9g}",
                }
                turbulence_conditions[patch_name] = {
                    "type": "fixedValue",
                    "value": f"uniform {turbulence_values[turbulence_field]:.9g}",
                }
                nut_conditions[patch_name] = {"type": "calculated", "value": "uniform 0"}
            elif role == "outlet":
                velocity_conditions[patch_name] = {"type": "zeroGradient"}
                pressure_conditions[patch_name] = {
                    "type": "fixedValue",
                    "value": f"uniform {kinematic_reference_pressure:.9g}",
                }
                k_conditions[patch_name] = {"type": "zeroGradient"}
                turbulence_conditions[patch_name] = {"type": "zeroGradient"}
                nut_conditions[patch_name] = {"type": "calculated", "value": "uniform 0"}
            elif role == "wall":
                velocity_conditions[patch_name] = {"type": "noSlip"}
                pressure_conditions[patch_name] = {"type": "zeroGradient"}
                k_conditions[patch_name] = {"type": "kqRWallFunction", "value": "uniform 0"}
                turbulence_conditions[patch_name] = {
                    "type": "omegaWallFunction" if turbulence_field == "omega" else "epsilonWallFunction",
                    "value": "uniform 1",
                }
                nut_conditions[patch_name] = {"type": "nutkWallFunction", "value": "uniform 0"}
            elif role == "symmetry":
                velocity_conditions[patch_name] = {"type": "symmetry"}
                pressure_conditions[patch_name] = {"type": "symmetry"}
                k_conditions[patch_name] = {"type": "symmetry"}
                turbulence_conditions[patch_name] = {"type": "symmetry"}
                nut_conditions[patch_name] = {"type": "symmetry"}
            else:  # normalize_boundary_recipe makes this unreachable.
                raise EngineeringExecutionError(f"Unsupported boundary role: {role}.")

        EngineeringOrchestrator._write_openfoam_field(
            zero / "U",
            "volVectorField",
            "U",
            "[0 1 -1 0 0 0 0]",
            "uniform (0 0 0)",
            velocity_conditions,
        )
        EngineeringOrchestrator._write_openfoam_field(
            zero / "p",
            "volScalarField",
            "p",
            "[0 2 -2 0 0 0 0]",
            f"uniform {kinematic_reference_pressure:.9g}",
            pressure_conditions,
        )
        EngineeringOrchestrator._write_openfoam_field(
            zero / "k",
            "volScalarField",
            "k",
            "[0 2 -2 0 0 0 0]",
            f"uniform {initial_turbulence['k']:.9g}",
            k_conditions,
        )
        turbulence_dimensions = "[0 0 -1 0 0 0 0]" if turbulence_field == "omega" else "[0 2 -3 0 0 0 0]"
        EngineeringOrchestrator._write_openfoam_field(
            zero / turbulence_field,
            "volScalarField",
            turbulence_field,
            turbulence_dimensions,
            f"uniform {initial_turbulence[turbulence_field]:.9g}",
            turbulence_conditions,
        )
        EngineeringOrchestrator._write_openfoam_field(
            zero / "nut",
            "volScalarField",
            "nut",
            "[0 2 -1 0 0 0 0]",
            "uniform 0",
            nut_conditions,
        )
        return {
            "solver": solver,
            "transient": transient,
            "energy_equation": energy_equation,
            "fluid": fluid,
            "kinematic_viscosity": float(properties["nu"]),
            "reference_pressure_pa": reference_pressure,
            "kinematic_reference_pressure": kinematic_reference_pressure,
            "turbulence_model": turbulence,
            "residual_target": residual_target,
            "boundary_recipe": boundary_recipe,
            "mesh_patches": mesh_patches,
        }

    @staticmethod
    def normalize_boundary_recipe(physics_configuration: dict[str, Any]) -> dict[str, Any]:
        """Return the canonical, safe boundary recipe for an OpenFOAM case.

        The desktop's simple Advanced controls create the same recipe as the
        programmatic ``boundary_recipe`` / ``boundary_conditions`` contracts.
        A structured recipe accepts a ``patches`` list with entries such as::

            {"name": "inlet", "role": "inlet", "velocity": [20, 0, 0],
             "turbulence_intensity": 0.05, "turbulence_length_scale": 0.01}

        Turbulence intensity in structured recipes is a fraction; the desktop
        percentage field is converted before persistence.  Boundary names are
        constrained to OpenFOAM ``word`` characters so user input cannot alter
        the generated dictionaries.
        """
        if not isinstance(physics_configuration, dict):
            raise EngineeringExecutionError("Physics configuration must be a JSON object.")
        fields = EngineeringOrchestrator._fields(physics_configuration)
        raw_recipe = physics_configuration.get("boundary_recipe")
        if raw_recipe is None:
            raw_recipe = physics_configuration.get("boundary_conditions")

        if raw_recipe is None:
            entries = EngineeringOrchestrator._boundary_entries_from_setup_fields(fields)
        else:
            if isinstance(raw_recipe, str):
                try:
                    raw_recipe = json.loads(raw_recipe)
                except json.JSONDecodeError as error:
                    raise EngineeringExecutionError(
                        "Boundary recipe must be valid JSON when supplied as text."
                    ) from error
            entries = EngineeringOrchestrator._boundary_entries_from_structured_recipe(raw_recipe)

        canonical: list[dict[str, Any]] = []
        seen_names: set[str] = set()
        roles: set[str] = set()
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                raise EngineeringExecutionError(f"Boundary recipe entry {index} must be an object.")
            name = str(entry.get("name") or entry.get("patch") or "").strip()
            if not _OPENFOAM_PATCH_NAME.fullmatch(name):
                raise EngineeringExecutionError(
                    f"Boundary patch '{name or index}' must use letters, numbers, and underscores only."
                )
            if name in seen_names:
                raise EngineeringExecutionError(
                    f"Boundary patch '{name}' is assigned more than one boundary role."
                )
            role = str(entry.get("role") or "").strip().lower()
            if role not in {"inlet", "outlet", "wall", "symmetry"}:
                raise EngineeringExecutionError(
                    f"Boundary patch '{name}' has unsupported role '{role or 'missing'}'."
                )
            normalized_entry: dict[str, Any] = {"name": name, "role": role}
            if role == "inlet":
                normalized_entry["velocity"] = EngineeringOrchestrator._boundary_vector(
                    entry.get("velocity"), f"Inlet velocity for '{name}'"
                )
                intensity = EngineeringOrchestrator._boundary_number(
                    entry.get("turbulence_intensity"), f"Turbulence intensity for '{name}'"
                )
                if not 0 < intensity <= 1:
                    raise EngineeringExecutionError(
                        f"Turbulence intensity for '{name}' must be greater than 0 and no more than 1."
                    )
                length_scale = EngineeringOrchestrator._boundary_number(
                    entry.get("turbulence_length_scale"), f"Turbulence length scale for '{name}'"
                )
                if length_scale <= 0:
                    raise EngineeringExecutionError(
                        f"Turbulence length scale for '{name}' must be greater than 0 m."
                    )
                normalized_entry["turbulence_intensity"] = intensity
                normalized_entry["turbulence_length_scale"] = length_scale
            canonical.append(normalized_entry)
            seen_names.add(name)
            roles.add(role)

        if "inlet" not in roles or "outlet" not in roles:
            raise EngineeringExecutionError(
                "A wind-tunnel solver recipe needs at least one named inlet and one named outlet patch."
            )
        return {"patches": canonical}

    @staticmethod
    def _boundary_entries_from_setup_fields(fields: dict[str, Any]) -> list[dict[str, Any]]:
        inlet_names = EngineeringOrchestrator._boundary_patch_names(
            fields.get("Inlet patch"), "Inlet patch", required=True
        )
        outlet_names = EngineeringOrchestrator._boundary_patch_names(
            fields.get("Outlet patch"), "Outlet patch", required=True
        )
        wall_names = EngineeringOrchestrator._boundary_patch_names(
            fields.get("Wall patches"), "Wall patches", required=False
        )
        symmetry_names = EngineeringOrchestrator._boundary_patch_names(
            fields.get("Symmetry patches"), "Symmetry patches", required=False
        )
        velocity = EngineeringOrchestrator._boundary_vector(fields.get("Inlet velocity"), "Inlet velocity")
        intensity_percent = EngineeringOrchestrator._boundary_number(
            fields.get("Turbulence intensity"), "Turbulence intensity"
        )
        if not 0 < intensity_percent <= 100:
            raise EngineeringExecutionError("Turbulence intensity must be greater than 0% and no more than 100%.")
        length_scale = EngineeringOrchestrator._boundary_number(
            fields.get("Turbulence length scale"), "Turbulence length scale"
        )
        if length_scale <= 0:
            raise EngineeringExecutionError("Turbulence length scale must be greater than 0 m.")

        entries: list[dict[str, Any]] = [
            {
                "name": name,
                "role": "inlet",
                "velocity": velocity,
                "turbulence_intensity": intensity_percent / 100.0,
                "turbulence_length_scale": length_scale,
            }
            for name in inlet_names
        ]
        entries.extend({"name": name, "role": "outlet"} for name in outlet_names)
        entries.extend({"name": name, "role": "wall"} for name in wall_names)
        entries.extend({"name": name, "role": "symmetry"} for name in symmetry_names)
        return entries

    @staticmethod
    def _boundary_entries_from_structured_recipe(raw_recipe: Any) -> list[dict[str, Any]]:
        if isinstance(raw_recipe, list):
            return raw_recipe
        if not isinstance(raw_recipe, dict):
            raise EngineeringExecutionError("Boundary recipe must be an object with a patches list.")
        patches = raw_recipe.get("patches")
        if isinstance(patches, list):
            return patches

        # The grouped form is convenient for API clients and maps exactly to
        # the canonical patch list.  It remains intentionally explicit: a
        # missing inlet velocity never falls back to a fabricated freestream.
        grouped: list[dict[str, Any]] = []
        for role, key in (("inlet", "inlets"), ("outlet", "outlets"), ("wall", "walls"), ("symmetry", "symmetry")):
            values = raw_recipe.get(key, [])
            if isinstance(values, (str, dict)):
                values = [values]
            if not isinstance(values, list):
                raise EngineeringExecutionError(f"Boundary recipe '{key}' must be a list.")
            for value in values:
                if isinstance(value, str):
                    grouped.append({"name": value, "role": role})
                elif isinstance(value, dict):
                    grouped.append({**value, "role": role})
                else:
                    raise EngineeringExecutionError(f"Boundary recipe '{key}' contains an invalid patch entry.")
        if not grouped:
            raise EngineeringExecutionError("Boundary recipe must contain a non-empty patches list.")
        return grouped

    @staticmethod
    def _boundary_patch_names(value: Any, label: str, *, required: bool) -> list[str]:
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                raise EngineeringExecutionError(f"{label} is required for the wind-tunnel boundary recipe.")
            return []
        if isinstance(value, str):
            names = [part.strip() for part in value.split(",")]
        elif isinstance(value, list):
            names = [str(part).strip() for part in value]
        else:
            raise EngineeringExecutionError(f"{label} must be a comma-separated list of mesh patch names.")
        if any(not name for name in names):
            raise EngineeringExecutionError(f"{label} contains an empty patch name.")
        return names

    @staticmethod
    def _boundary_number(value: Any, label: str) -> float:
        if isinstance(value, bool) or value is None:
            raise EngineeringExecutionError(f"{label} is required.")
        try:
            numeric = float(value)
        except (TypeError, ValueError) as error:
            raise EngineeringExecutionError(f"{label} must be a finite number.") from error
        if not math.isfinite(numeric):
            raise EngineeringExecutionError(f"{label} must be a finite number.")
        return numeric

    @staticmethod
    def _boundary_vector(value: Any, label: str) -> list[float]:
        if isinstance(value, str):
            tokens = [token for token in re.split(r"[\s,;]+", value.strip().strip("()[]")) if token]
            value = tokens
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            raise EngineeringExecutionError(f"{label} must contain exactly three components, for example '20, 0, 0'.")
        vector = [EngineeringOrchestrator._boundary_number(component, label) for component in value]
        if math.sqrt(sum(component * component for component in vector)) <= 0:
            raise EngineeringExecutionError(f"{label} must not be the zero vector.")
        return vector

    @staticmethod
    def _inlet_turbulence_values(entry: dict[str, Any]) -> dict[str, float]:
        velocity = entry["velocity"]
        speed = math.sqrt(sum(float(component) * float(component) for component in velocity))
        intensity = float(entry["turbulence_intensity"])
        length_scale = float(entry["turbulence_length_scale"])
        turbulent_kinetic_energy = 1.5 * (speed * intensity) ** 2
        c_mu = 0.09
        return {
            "k": turbulent_kinetic_energy,
            "omega": math.sqrt(turbulent_kinetic_energy) / (c_mu**0.25 * length_scale),
            "epsilon": (c_mu**0.75 * turbulent_kinetic_energy**1.5) / length_scale,
        }

    @staticmethod
    def _validate_and_apply_boundary_patch_types(
        case_path: Path, boundary_recipe: dict[str, Any]
    ) -> dict[str, Any]:
        """Verify explicit roles against the converted mesh and safely retag walls.

        ``gmshToFoam`` commonly emits every physical surface as a generic
        ``patch``.  A named user wall is therefore retagged to ``wall`` before
        wall functions are written.  Inlet and outlet patches must already be
        open ``patch`` boundaries; the adapter never converts a real wall into
        an inlet or outlet.
        """
        boundary_path = case_path / "constant" / "polyMesh" / "boundary"
        entries = EngineeringOrchestrator._openfoam_boundary_entries(boundary_path)
        by_name = {entry["name"]: entry for entry in entries}
        configured = {str(entry["name"]): entry for entry in boundary_recipe["patches"]}
        mesh_names = list(by_name)
        missing = [name for name in configured if name not in by_name]
        unconfigured = [name for name in mesh_names if name not in configured]
        if missing or unconfigured:
            messages: list[str] = []
            if missing:
                messages.append(f"configured patch(es) not found: {', '.join(missing)}")
            if unconfigured:
                messages.append(f"mesh patch(es) without a boundary role: {', '.join(unconfigured)}")
            raise EngineeringExecutionError(
                "OpenFOAM boundary recipe does not match the converted mesh (" + "; ".join(messages) + ")."
            )

        desired_types = {"inlet": "patch", "outlet": "patch", "wall": "wall", "symmetry": "symmetryPlane"}
        permitted_source_types = {
            "inlet": {"patch"},
            "outlet": {"patch"},
            "wall": {"patch", "wall"},
            "symmetry": {"patch", "symmetry", "symmetryPlane"},
        }
        updates: list[tuple[int, int, str]] = []
        final_types: dict[str, str] = {}
        for name, recipe_entry in configured.items():
            mesh_entry = by_name[name]
            role = str(recipe_entry["role"])
            source_type = str(mesh_entry["type"])
            if source_type not in permitted_source_types[role]:
                raise EngineeringExecutionError(
                    f"Mesh patch '{name}' has type '{source_type}', which cannot be used as a {role}."
                )
            desired_type = desired_types[role]
            if source_type != desired_type:
                updates.append((int(mesh_entry["type_start"]), int(mesh_entry["type_end"]), desired_type))
            final_types[name] = desired_type

        if updates:
            content = boundary_path.read_text(encoding="utf-8")
            for start, end, desired_type in sorted(updates, reverse=True):
                content = content[:start] + desired_type + content[end:]
            boundary_path.write_text(content, encoding="utf-8")
        return {"names": mesh_names, "types": final_types}

    @staticmethod
    def _openfoam_boundary_entries(boundary_path: Path) -> list[dict[str, Any]]:
        if not boundary_path.is_file():
            raise EngineeringExecutionError(
                "OpenFOAM mesh conversion did not produce constant/polyMesh/boundary for boundary validation."
            )
        content = boundary_path.read_text(encoding="utf-8")
        list_start = content.find("(")
        if list_start < 0:
            raise EngineeringExecutionError("OpenFOAM mesh boundary file is malformed: patch list is missing.")
        entries: list[dict[str, Any]] = []
        offset = list_start + 1
        for match in _OPENFOAM_BOUNDARY_ENTRY.finditer(content[offset:]):
            name = match.group("name")
            body = match.group("body")
            type_match = _OPENFOAM_BOUNDARY_TYPE.search(body)
            if not type_match:
                raise EngineeringExecutionError(f"OpenFOAM mesh patch '{name}' has no type declaration.")
            body_start = offset + match.start("body")
            entries.append(
                {
                    "name": name,
                    "type": type_match.group("type"),
                    "type_start": body_start + type_match.start("type"),
                    "type_end": body_start + type_match.end("type"),
                }
            )
        if not entries:
            raise EngineeringExecutionError("OpenFOAM mesh boundary file contains no named patches.")
        if len({entry["name"] for entry in entries}) != len(entries):
            raise EngineeringExecutionError("OpenFOAM mesh boundary file contains duplicate patch names.")
        return entries

    @staticmethod
    def _write_openfoam_field(
        path: Path,
        class_name: str,
        object_name: str,
        dimensions: str,
        internal_field: str,
        boundary_conditions: dict[str, dict[str, str]],
    ) -> None:
        lines = [
            "FoamFile",
            "{",
            "    version     2.0;",
            "    format      ascii;",
            f"    class       {class_name};",
            '    location    "0";',
            f"    object      {object_name};",
            "}",
            "",
            f"dimensions      {dimensions};",
            f"internalField   {internal_field};",
            "",
            "boundaryField",
            "{",
        ]
        for patch_name, condition in boundary_conditions.items():
            lines.extend((f"    {patch_name}", "    {"))
            for key, value in condition.items():
                lines.append(f"        {key:<14}{value};")
            lines.append("    }")
        lines.extend(("}", ""))
        path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _solver_name(configuration: dict[str, Any]) -> str:
        fields = EngineeringOrchestrator._fields(configuration)
        transient = fields.get("Solver type") == "Transient RANS" or fields.get("Run type") == "Transient flow"
        return "pimpleFoam" if transient else "simpleFoam"

    @staticmethod
    def _fields(configuration: dict[str, Any]) -> dict[str, Any]:
        fields = configuration.get("fields", configuration)
        return fields if isinstance(fields, dict) else {}

    @staticmethod
    def _mesh_route(configuration: dict[str, Any]) -> str:
        fields = EngineeringOrchestrator._fields(configuration)
        return str(configuration.get("route") or fields.get("Route") or "tetrahedral").strip()

    @staticmethod
    def _source_path(configuration: dict[str, Any]) -> Path:
        fields = EngineeringOrchestrator._fields(configuration)
        source = configuration.get("source_path") or fields.get("Source")
        return Path(str(source or "")).expanduser()

    @staticmethod
    def _number(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _publish_reference(self, project_path: Path, stage_id: str, job_id: str, output: dict[str, Any]) -> None:
        reference_path = project_path / "refs" / stage_id
        reference_path.mkdir(parents=True, exist_ok=True)
        self._write_json(reference_path / "latest.json", {"job_id": job_id, "output": output})

    def _latest_payload(self, project_path: Path, stage_id: str) -> dict[str, Any]:
        path = project_path / "refs" / stage_id / "latest.json"
        if not path.exists():
            raise EngineeringExecutionError(f"No successful {stage_id} artifact exists for this project.")
        return self._read_json(path)["output"]

    def _latest_artifact(self, project_path: Path, stage_id: str, key: str) -> Path:
        payload = self._latest_payload(project_path, stage_id)
        if key in payload:
            return Path(str(payload[key]))
        for group in (payload.get(stage_id), payload.get("geometry"), payload.get("mesh"), payload.get("physics")):
            if isinstance(group, dict) and key in group:
                return Path(str(group[key]))
        raise EngineeringExecutionError(f"The latest {stage_id} artifact does not contain '{key}'.")
