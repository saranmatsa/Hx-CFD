"""Geometry adapter selection for the complete FreeCAD import contract.

These tests intentionally use only capability fakes.  They prove routing and
the isolated worker contract without pretending that FreeCAD is installed in
the test runtime.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cfd_backend.services.engineering_orchestrator import (
    FREECAD_GEOMETRY_SOURCE_EXTENSIONS,
    EngineeringExecutionError,
    EngineeringOrchestrator,
)
from cfd_backend.services.workflow_service import LocalWorkflowService


class FreeCADReadyRegistry:
    async def capability(self, engine_id: str, refresh: bool = False) -> SimpleNamespace:
        del refresh
        return SimpleNamespace(
            status="ready" if engine_id == "freecad" else "unavailable",
            display_name=engine_id,
            executable="FreeCADCmd.exe" if engine_id == "freecad" else None,
        )


class FreeCADUnavailableRegistry:
    async def capability(self, engine_id: str, refresh: bool = False) -> SimpleNamespace:
        del refresh
        return SimpleNamespace(status="unavailable", display_name=engine_id, executable=None)


class RecordingGeometryOrchestrator(EngineeringOrchestrator):
    def __init__(self, settings: object, engines: object):
        super().__init__(settings, engines)  # type: ignore[arg-type]
        self.selected_adapter: str | None = None

    async def _prepare_geometry_with_freecad(self, run_path: Path, source: Path) -> dict:
        del run_path, source
        self.selected_adapter = "freecad"
        return {"engines": ["FreeCAD"]}

    async def _prepare_geometry_with_gmsh(self, run_path: Path, source: Path) -> dict:
        del run_path, source
        self.selected_adapter = "gmsh"
        return {"engines": ["Gmsh"]}


class TestFreeCADGeometryFormats(unittest.IsolatedAsyncioTestCase):
    async def test_every_required_format_routes_to_freecad_when_ready(self) -> None:
        registry = FreeCADReadyRegistry()
        orchestrator = RecordingGeometryOrchestrator(SimpleNamespace(), registry)
        workflow = LocalWorkflowService(SimpleNamespace(), registry)  # type: ignore[arg-type]

        with tempfile.TemporaryDirectory(prefix="hx-cfd-freecad-formats-") as temporary:
            root = Path(temporary)
            for extension in sorted(FREECAD_GEOMETRY_SOURCE_EXTENSIONS):
                with self.subTest(extension=extension):
                    source = root / f"source{extension}"
                    source.write_bytes(b"geometry fixture")
                    run_path = root / f"run-{extension.lstrip('.')}"
                    run_path.mkdir()

                    required = await workflow._required_engines(
                        "geometry", {"fields": {"Source": str(source)}}
                    )
                    output = await orchestrator._prepare_geometry(
                        root, run_path, {"fields": {"Source": str(source)}}
                    )

                    self.assertEqual(required, ("freecad",))
                    self.assertEqual(orchestrator.selected_adapter, "freecad")
                    self.assertEqual(output["engines"], ["FreeCAD"])

    async def test_surface_mesh_requires_freecad_when_it_is_unavailable(self) -> None:
        registry = FreeCADUnavailableRegistry()
        orchestrator = RecordingGeometryOrchestrator(SimpleNamespace(), registry)
        workflow = LocalWorkflowService(SimpleNamespace(), registry)  # type: ignore[arg-type]

        with tempfile.TemporaryDirectory(prefix="hx-cfd-no-freecad-") as temporary:
            root = Path(temporary)
            for extension in (".stl", ".obj"):
                with self.subTest(extension=extension):
                    source = root / f"surface{extension}"
                    source.write_bytes(b"surface fixture")
                    run_path = root / f"run-{extension.lstrip('.')}"
                    run_path.mkdir()

                    required = await workflow._required_engines(
                        "geometry", {"fields": {"Source": str(source)}}
                    )
                    with self.assertRaisesRegex(EngineeringExecutionError, "requires local FreeCAD"):
                        await orchestrator._prepare_geometry(
                            root, run_path, {"fields": {"Source": str(source)}}
                        )

                    self.assertEqual(required, ("freecad",))
                    self.assertIsNone(orchestrator.selected_adapter)

    def test_freecad_worker_has_native_mesh_to_solid_validation(self) -> None:
        script = EngineeringOrchestrator._freecad_preparation_script()
        compile(script, "prepare_geometry.py", "exec")
        self.assertIn("makeShapeFromMesh", script)
        self.assertIn("Part.makeSolid", script)
        self.assertIn("accepted_for_volume_meshing", script)

    def test_generic_validation_accepts_all_freecad_import_formats(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-freecad-validation-") as temporary:
            root = Path(temporary)
            for extension in FREECAD_GEOMETRY_SOURCE_EXTENSIONS:
                with self.subTest(extension=extension):
                    source = root / f"source{extension}"
                    source.write_bytes(b"geometry fixture")
                    EngineeringOrchestrator._validate_geometry_source(source)


if __name__ == "__main__":
    unittest.main()
