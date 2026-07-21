"""cfMesh workflow contract tests.

These tests do not require a built cfMesh binary. They pin the backend contract
that lets HX CFD expose cfMesh only as a real local engine route and lets the
solver pipeline consume its OpenFOAM-native mesh output.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cfd_backend.services.engine_registry import EngineCapability, EngineRegistry
from cfd_backend.services.engineering_orchestrator import EngineeringOrchestrator
from cfd_backend.services.workflow_service import LocalWorkflowService


class ReadyRegistry(EngineRegistry):
    def __init__(self) -> None:
        super().__init__(SimpleNamespace())  # type: ignore[arg-type]

    async def capability(self, engine_id: str, refresh: bool = False) -> EngineCapability:
        return EngineCapability(
            id=engine_id,
            display_name={"cfmesh": "cfMesh", "gmsh": "Gmsh"}.get(engine_id, engine_id),
            workflow=["meshing"],
            runtime="test",
            optional=engine_id == "cfmesh",
            adapter="test",
            status="ready",
            executable=f"{engine_id}.exe",
        )

    async def inventory(self, refresh: bool = False) -> list[dict]:
        return [
            (await self.capability("gmsh")).as_dict(),
            (await self.capability("cfmesh")).as_dict(),
        ]

    async def requirements_available(
        self, engine_ids, refresh: bool = False  # type: ignore[no-untyped-def,override]
    ) -> tuple[bool, list[dict]]:
        return True, []


class TestCfMeshWorkflow(unittest.IsolatedAsyncioTestCase):
    async def test_cfmesh_route_requires_cfmesh_and_gmsh(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-cfmesh-route-") as temporary:
            settings = SimpleNamespace(projects_dir=Path(temporary) / "projects")
            workflow = LocalWorkflowService(settings, ReadyRegistry())  # type: ignore[arg-type]

            source = Path(temporary) / "prepared.brep"
            source.write_text("fixture", encoding="utf-8")
            await workflow.configure_stage(
                "cfmesh-route",
                "geometry",
                {"fields": {"Source": str(source)}},
            )
            await workflow.configure_stage(
                "cfmesh-route",
                "meshing",
                {
                    "route": "cfmesh_cartesian",
                    "fields": {
                        "Base size": "1.0",
                        "Boundary layers": "0",
                    },
                },
            )

            required = await workflow._required_engines(  # noqa: SLF001
                "meshing",
                {"route": "cfmesh_cartesian"},
            )
            self.assertEqual(required, ("cfmesh", "gmsh"))

    async def test_physics_accepts_cfmesh_openfoam_case_without_gmsh_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-cfmesh-physics-") as temporary:
            root = Path(temporary)
            project = root / "project"
            case = root / "case"
            boundary = case / "constant" / "polyMesh" / "boundary"
            boundary.parent.mkdir(parents=True)
            boundary.write_text("0\n(\n);\n", encoding="utf-8")
            latest = project / "refs" / "meshing"
            latest.mkdir(parents=True)
            EngineeringOrchestrator._write_json(
                latest / "latest.json",
                {
                    "job_id": "mesh",
                    "output": {
                        "mesh": {
                            "openfoam_case": str(case),
                            "route": "cfmesh_cartesian",
                        }
                    },
                },
            )
            settings = SimpleNamespace(default_turbulence_model="kOmegaSST")
            orchestrator = EngineeringOrchestrator(settings, ReadyRegistry())  # type: ignore[arg-type]
            run_path = root / "run"
            run_path.mkdir()

            output = await orchestrator._write_physics_case(  # noqa: SLF001
                project,
                run_path,
                {
                    "fields": {
                        "Inlet patch": "inlet",
                        "Outlet patch": "outlet",
                        "Wall patches": "walls",
                        "Inlet velocity": "1, 0, 0",
                        "Turbulence intensity": "5",
                        "Turbulence length scale": "0.1",
                    }
                },
            )

            self.assertIsNone(output["physics"]["mesh_file"])
            self.assertEqual(output["physics"]["openfoam_case"], str(case))


if __name__ == "__main__":
    unittest.main()
