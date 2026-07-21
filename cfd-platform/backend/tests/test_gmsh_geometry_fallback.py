"""Concrete coverage for the FreeCAD-independent solid-CAD preparation route."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cfd_backend.services.engineering_orchestrator import (
    EngineeringExecutionError,
    EngineeringOrchestrator,
)
from cfd_backend.services.workflow_service import LocalWorkflowService


class GmshOnlyRegistry:
    """Minimal capability contract for exercising the Gmsh fallback explicitly."""

    async def capability(self, engine_id: str, refresh: bool = False) -> SimpleNamespace:
        del refresh
        return SimpleNamespace(status="unavailable" if engine_id == "freecad" else "ready")

    async def requirements_available(
        self, engine_ids: tuple[str, ...], refresh: bool = False
    ) -> tuple[bool, list[dict[str, str]]]:
        del refresh
        return tuple(engine_ids) == ("gmsh",), []


class GmshMeshingRegistry(GmshOnlyRegistry):
    """Capability contract for a real mesh without an installed solver."""

    async def capability(self, engine_id: str, refresh: bool = False) -> SimpleNamespace:
        del refresh
        return SimpleNamespace(
            status="unavailable" if engine_id in {"freecad", "openfoam", "paraview"} else "ready",
            display_name=engine_id,
            executable=None,
        )

    async def requirements_available(
        self, engine_ids: tuple[str, ...], refresh: bool = False
    ) -> tuple[bool, list[dict[str, str]]]:
        del refresh
        unavailable = [engine_id for engine_id in engine_ids if engine_id == "openfoam"]
        return not unavailable, [{"display_name": engine_id} for engine_id in unavailable]

    async def inventory(self, refresh: bool = False) -> list[dict[str, str]]:
        del refresh
        return []


@unittest.skipUnless(importlib.util.find_spec("gmsh"), "requires the managed local Gmsh runtime")
class TestGmshGeometryFallback(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _write_solid_fixture(path: Path) -> None:
        """Create a real OCC exchange solid; no fixture CAD file is faked or copied."""
        import gmsh

        gmsh.initialize()
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.model.add("hx-cfd-gmsh-fallback-fixture")
            gmsh.model.occ.addBox(0, 0, 0, 10, 20, 30)
            gmsh.model.occ.synchronize()
            gmsh.write(str(path))
        finally:
            gmsh.finalize()

    async def test_prepares_solid_exchange_formats_when_freecad_is_unavailable(self) -> None:
        registry = GmshOnlyRegistry()
        orchestrator = EngineeringOrchestrator(
            SimpleNamespace(), registry  # type: ignore[arg-type]
        )
        workflow = LocalWorkflowService(SimpleNamespace(), registry)  # type: ignore[arg-type]

        with tempfile.TemporaryDirectory(prefix="hx-cfd-gmsh-fallback-") as temporary:
            root = Path(temporary)
            for extension in ("brep", "step", "iges"):
                with self.subTest(source_format=extension):
                    source = root / f"fixture.{extension}"
                    run_path = root / f"run-{extension}"
                    run_path.mkdir()
                    self._write_solid_fixture(source)

                    required = await workflow._required_engines(
                        "geometry", {"fields": {"Source": str(source)}}
                    )
                    output = await orchestrator._prepare_geometry(
                        root, run_path, {"fields": {"Source": str(source)}}
                    )

                    prepared = Path(str(output["geometry"]["prepared_geometry"]))
                    self.assertEqual(required, ("gmsh",))
                    self.assertEqual(output["engines"], ["Gmsh"])
                    self.assertTrue(prepared.is_file())
                    self.assertTrue(output["geometry"]["valid"])
                    self.assertEqual(output["geometry"]["source_format"], extension)
                    self.assertEqual(output["geometry"]["solid_count"], 1)
                    self.assertAlmostEqual(output["geometry"]["volume"], 6000.0)
                    self.assertEqual(
                        output["geometry"]["validation"]["status"], "accepted_for_volume_meshing"
                    )
                    self.assertEqual(
                        output["geometry"]["repair"]["operation_invoked"],
                        "Gmsh OpenCASCADE healShapes",
                    )

    def test_accepts_stl_for_the_freecad_geometry_route(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-stl-rejection-") as temporary:
            source = Path(temporary) / "surface.stl"
            source.write_text("solid surface\nendsolid surface\n", encoding="utf-8")
            # Generic validation no longer conflates source support with the
            # Gmsh fallback: FreeCAD owns STL/OBJ import when installed.
            EngineeringOrchestrator._validate_geometry_source(source)

    async def test_generates_and_validates_a_volume_mesh_without_openfoam(self) -> None:
        """Gmsh/meshio/VTK/PyVista publish real mesh evidence before solver setup."""
        registry = GmshMeshingRegistry()
        with tempfile.TemporaryDirectory(prefix="hx-cfd-gmsh-mesh-") as temporary:
            root = Path(temporary)
            settings = SimpleNamespace(projects_dir=root / "projects")
            workflow = LocalWorkflowService(settings, registry)  # type: ignore[arg-type]
            source = root / "fixture.brep"
            self._write_solid_fixture(source)

            await workflow.configure_stage(
                "mesh-fallback",
                "geometry",
                {"fields": {"Source": str(source)}},
            )
            geometry = await workflow.execute_stage("mesh-fallback", "geometry")
            self.assertEqual(geometry["output"]["engines"], ["Gmsh"])

            await workflow.configure_stage(
                "mesh-fallback",
                "meshing",
                {
                    "fields": {
                        "Base size": "8.0",
                        "Boundary layers": "0",
                        "Growth rate": "1.18",
                    }
                },
            )
            meshing = await workflow.execute_stage("mesh-fallback", "meshing")
            output = meshing["output"]

            self.assertEqual(output["engines"], ["Gmsh", "meshio", "VTK", "PyVista"])
            # The desktop boundary deliberately receives opaque project
            # artifacts rather than raw local paths. The real-engine adapter
            # still produced all three files; their descriptors prove the
            # workflow service published them safely.
            self.assertEqual(output["mesh"]["gmsh_artifact"]["name"], "mesh.msh")
            self.assertEqual(output["mesh"]["vtk_artifact"]["name"], "mesh.vtk")
            self.assertEqual(output["mesh"]["preview_artifact"]["name"], "mesh-preview.png")
            self.assertTrue(output["mesh"]["gmsh_artifact"]["artifact_id"].startswith("artifact_"))
            self.assertTrue(output["mesh"]["preview_artifact"]["previewable"])
            self.assertGreater(output["quality"]["points"], 0)
            self.assertGreater(output["quality"]["cells"], 0)
            self.assertEqual(output["validation"]["openfoam_check"]["status"], "deferred")
            self.assertEqual(output["mesh"]["boundary_groups"]["unassigned_surface_ids"], [1, 2, 3, 4, 5, 6])

            # Physics is a durable recipe, not a fake OpenFOAM case.  The
            # actual solver conversion remains deferred until OpenFOAM exists.
            await workflow.configure_stage(
                "mesh-fallback",
                "physics",
                {
                    "fields": {
                        "Fluid": "Air (ideal gas)",
                        "Inlet patch": "inlet",
                        "Outlet patch": "outlet",
                        "Wall patches": "walls",
                        "Inlet velocity": "20, 0, 0",
                        "Turbulence intensity": "5",
                        "Turbulence length scale": "0.01",
                    }
                },
            )
            physics = await workflow.execute_stage("mesh-fallback", "physics")
            physics_payload = physics["output"]["physics"]
            self.assertEqual(physics_payload["openfoam_case"], None)
            self.assertEqual(physics_payload["mesh_file_artifact"]["name"], "mesh.msh")

            # Published references are returned from a fresh durable snapshot,
            # not just from the in-memory execute response.  Reconfiguring an
            # upstream stage must clear those mutable pointers while retaining
            # the historical run directories for provenance.
            persisted = await workflow.snapshot("mesh-fallback")
            self.assertIn("geometry", persisted["latest_outputs"])
            self.assertIn("meshing", persisted["latest_outputs"])
            self.assertIn("physics", persisted["latest_outputs"])
            self.assertEqual(
                persisted["latest_outputs"]["meshing"]["mesh"]["gmsh_artifact"]["artifact_id"],
                output["mesh"]["gmsh_artifact"]["artifact_id"],
            )

            await workflow.configure_stage(
                "mesh-fallback",
                "geometry",
                {"fields": {"Source": str(source)}},
            )
            invalidated = await workflow.snapshot("mesh-fallback")
            self.assertNotIn("geometry", invalidated["latest_outputs"])
            self.assertNotIn("meshing", invalidated["latest_outputs"])
            self.assertNotIn("physics", invalidated["latest_outputs"])


if __name__ == "__main__":
    unittest.main()
