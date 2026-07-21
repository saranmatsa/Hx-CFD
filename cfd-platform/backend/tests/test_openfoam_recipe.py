"""Unit coverage for the deterministic OpenFOAM case recipe adapter."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cfd_backend.services.engineering_orchestrator import (
    EngineeringExecutionError,
    EngineeringOrchestrator,
)


class TestOpenFoamCaseRecipe(unittest.TestCase):
    @staticmethod
    def _write_mesh_boundary(case_path: Path, patches: tuple[tuple[str, str], ...] = (
        ("inlet", "patch"),
        ("outlet", "patch"),
        ("walls", "patch"),
    )) -> None:
        boundary = case_path / "constant" / "polyMesh" / "boundary"
        boundary.parent.mkdir(parents=True, exist_ok=True)
        entries = []
        start_face = 0
        for name, patch_type in patches:
            entries.extend(
                (
                    name,
                    "{",
                    f"    type {patch_type};",
                    "    nFaces 10;",
                    f"    startFace {start_face};",
                    "}",
                )
            )
            start_face += 10
        boundary.write_text(
            "\n".join(("FoamFile", "{", "    version 2.0;", "}", "", str(len(patches)), "(", *entries, ")", "")),
            encoding="utf-8",
        )

    @staticmethod
    def _boundary_fields() -> dict[str, str]:
        return {
            "Inlet patch": "inlet",
            "Outlet patch": "outlet",
            "Wall patches": "walls",
            "Inlet velocity": "12, 0, 0",
            "Turbulence intensity": "5",
            "Turbulence length scale": "0.01",
        }

    def test_applies_visible_physics_and_transient_solver_choices(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-openfoam-recipe-") as temporary:
            case_path = Path(temporary)
            self._write_mesh_boundary(case_path)
            recipe = EngineeringOrchestrator._write_openfoam_case_files(
                case_path,
                {
                    "fields": {
                        "Fluid": "Water (liquid)",
                        "Energy equation": "Disabled",
                        "Turbulence model": "k-ε Realizable",
                        "Reference pressure": "101325",
                        **self._boundary_fields(),
                    }
                },
                {
                    "fields": {
                        "Run type": "Transient flow",
                        "Maximum iterations": "240",
                        "Residual target": "0.0001",
                    }
                },
            )

            self.assertEqual(recipe["solver"], "pimpleFoam")
            self.assertTrue(recipe["transient"])
            self.assertEqual(recipe["turbulence_model"], "realizableKE")
            self.assertAlmostEqual(recipe["kinematic_viscosity"], 1.0e-6)
            self.assertAlmostEqual(recipe["kinematic_reference_pressure"], 101325 / 998.2)

            self.assertIn("application pimpleFoam;", (case_path / "system" / "controlDict").read_text())
            self.assertIn("endTime 240;", (case_path / "system" / "controlDict").read_text())
            self.assertIn("ddtSchemes { default Euler; }", (case_path / "system" / "fvSchemes").read_text())
            solution = (case_path / "system" / "fvSolution").read_text()
            self.assertIn("PIMPLE", solution)
            self.assertIn("tolerance 0.0001;", solution)
            self.assertIn("RASModel realizableKE;", (case_path / "constant" / "turbulenceProperties").read_text())
            self.assertTrue((case_path / "0" / "epsilon").is_file())
            self.assertTrue((case_path / "0" / "nut").is_file())
            self.assertEqual(recipe["mesh_patches"]["types"]["walls"], "wall")
            self.assertIn("type wall;", (case_path / "constant" / "polyMesh" / "boundary").read_text())

            velocity = (case_path / "0" / "U").read_text()
            self.assertIn("inlet\n    {\n        type          fixedValue;\n        value         uniform (12 0 0);", velocity)
            self.assertIn("outlet\n    {\n        type          zeroGradient;", velocity)
            self.assertIn("walls\n    {\n        type          noSlip;", velocity)
            pressure = (case_path / "0" / "p").read_text()
            self.assertIn("outlet\n    {\n        type          fixedValue;", pressure)
            self.assertIn("walls\n    {\n        type          zeroGradient;", pressure)
            epsilon = (case_path / "0" / "epsilon").read_text()
            self.assertIn("inlet\n    {\n        type          fixedValue;", epsilon)
            self.assertIn("walls\n    {\n        type          epsilonWallFunction;", epsilon)
            self.assertIn("walls\n    {\n        type          nutkWallFunction;", (case_path / "0" / "nut").read_text())

    def test_rejects_energy_when_only_incompressible_recipe_exists(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-openfoam-energy-") as temporary:
            case_path = Path(temporary)
            self._write_mesh_boundary(case_path)
            with self.assertRaisesRegex(EngineeringExecutionError, "Energy equation is enabled"):
                EngineeringOrchestrator._write_openfoam_case_files(
                    case_path,
                    {"fields": {"Energy equation": "Enabled", **self._boundary_fields()}},
                    {"fields": {"Run type": "Steady flow"}},
                )

    def test_rejects_missing_or_unassigned_mesh_patches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-openfoam-boundary-") as temporary:
            case_path = Path(temporary)
            self._write_mesh_boundary(case_path, (("inlet", "patch"), ("walls", "patch"), ("farfield", "patch")))
            fields = self._boundary_fields()
            fields["Outlet patch"] = "outlet"
            with self.assertRaisesRegex(EngineeringExecutionError, "configured patch\(es\) not found: outlet"):
                EngineeringOrchestrator._write_openfoam_case_files(
                    case_path,
                    {"fields": fields},
                    {"fields": {"Run type": "Steady flow"}},
                )

    def test_rejects_zero_velocity_and_duplicate_roles_before_case_generation(self) -> None:
        fields = self._boundary_fields()
        fields["Inlet velocity"] = "0, 0, 0"
        with self.assertRaisesRegex(EngineeringExecutionError, "must not be the zero vector"):
            EngineeringOrchestrator.normalize_boundary_recipe({"fields": fields})

        fields = self._boundary_fields()
        fields["Outlet patch"] = "inlet"
        with self.assertRaisesRegex(EngineeringExecutionError, "assigned more than one boundary role"):
            EngineeringOrchestrator.normalize_boundary_recipe({"fields": fields})


if __name__ == "__main__":
    unittest.main()
