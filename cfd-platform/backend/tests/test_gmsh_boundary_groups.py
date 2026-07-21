"""Regression coverage for explicit Gmsh CFD boundary physical groups."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from cfd_backend.services.engineering_orchestrator import (
    EngineeringExecutionError,
    EngineeringOrchestrator,
)


@unittest.skipUnless(importlib.util.find_spec("gmsh"), "requires the managed local Gmsh runtime")
class TestGmshBoundaryGroups(unittest.TestCase):
    @staticmethod
    def _write_solid_fixture(path: Path) -> None:
        import gmsh

        gmsh.initialize()
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.model.add("hx-cfd-boundary-groups-fixture")
            gmsh.model.occ.addBox(0, 0, 0, 10, 20, 30)
            gmsh.model.occ.synchronize()
            gmsh.write(str(path))
        finally:
            gmsh.finalize()

    @staticmethod
    def _physical_groups(mesh_path: Path) -> dict[tuple[int, str], list[int]]:
        import gmsh

        gmsh.initialize()
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.open(str(mesh_path))
            return {
                (int(dimension), gmsh.model.getPhysicalName(dimension, tag)): [
                    int(entity)
                    for entity in gmsh.model.getEntitiesForPhysicalGroup(dimension, tag)
                ]
                for dimension, tag in gmsh.model.getPhysicalGroups()
            }
        finally:
            gmsh.finalize()

    def _prepared_box(self, root: Path) -> tuple[Path, list[int]]:
        source = root / "box.brep"
        prepared = root / "prepared.brep"
        self._write_solid_fixture(source)
        report = EngineeringOrchestrator._gmsh_prepare_geometry(source, prepared)
        return prepared, [int(surface["surface_id"]) for surface in report["surfaces"]]

    def test_explicit_surface_ids_become_named_physical_groups(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-gmsh-groups-") as temporary:
            root = Path(temporary)
            prepared, surface_ids = self._prepared_box(root)
            inlet, outlet, symmetry = surface_ids[:3]
            recipe = EngineeringOrchestrator.normalize_mesh_boundary_groups(
                {
                    "fields": {
                        "Inlet surface IDs": str(inlet),
                        "Outlet surface IDs": str(outlet),
                        "Wall surface IDs": "",
                        "Symmetry surface IDs": str(symmetry),
                        "Unassigned surfaces": "Group remaining as walls",
                    }
                }
            )
            mesh_path = root / "named-boundaries.msh"

            metadata = EngineeringOrchestrator._gmsh_volume_mesh(
                prepared,
                mesh_path,
                8.0,
                0,
                1.18,
                recipe,
            )

            expected_walls = sorted(set(surface_ids) - {inlet, outlet, symmetry})
            groups = {item["name"]: item["surface_ids"] for item in metadata["physical_groups"]}
            self.assertEqual(groups["inlet"], [inlet])
            self.assertEqual(groups["outlet"], [outlet])
            self.assertEqual(groups["symmetry"], [symmetry])
            self.assertEqual(groups["walls"], expected_walls)
            self.assertEqual(metadata["unassigned_surface_ids"], [])
            self.assertTrue(metadata["ready_for_solver"])

            physical_groups = self._physical_groups(mesh_path)
            self.assertEqual(physical_groups[(2, "inlet")], [inlet])
            self.assertEqual(physical_groups[(2, "outlet")], [outlet])
            self.assertEqual(physical_groups[(2, "symmetry")], [symmetry])
            self.assertEqual(physical_groups[(2, "walls")], expected_walls)
            self.assertEqual(physical_groups[(3, "fluid")], [1])

    def test_missing_flow_selections_stay_unassigned_instead_of_becoming_inlet_or_outlet(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-gmsh-unassigned-") as temporary:
            root = Path(temporary)
            prepared, surface_ids = self._prepared_box(root)
            mesh_path = root / "unassigned-boundaries.msh"
            recipe = EngineeringOrchestrator.normalize_mesh_boundary_groups(
                {"fields": {"Unassigned surfaces": "Keep as unassigned patch"}}
            )

            metadata = EngineeringOrchestrator._gmsh_volume_mesh(
                prepared,
                mesh_path,
                8.0,
                0,
                1.18,
                recipe,
            )

            self.assertEqual(metadata["unassigned_surface_ids"], surface_ids)
            self.assertFalse(metadata["ready_for_solver"])
            physical_groups = self._physical_groups(mesh_path)
            self.assertEqual(physical_groups[(2, "unassigned")], surface_ids)
            self.assertNotIn((2, "inlet"), physical_groups)
            self.assertNotIn((2, "outlet"), physical_groups)

    def test_rejects_unavailable_or_conflicting_surface_ids(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-gmsh-invalid-group-") as temporary:
            root = Path(temporary)
            prepared, surface_ids = self._prepared_box(root)
            mesh_path = root / "invalid-boundaries.msh"
            recipe = EngineeringOrchestrator.normalize_mesh_boundary_groups(
                {
                    "fields": {
                        "Inlet surface IDs": "999",
                        "Unassigned surfaces": "Keep as unassigned patch",
                    }
                }
            )

            with self.assertRaisesRegex(EngineeringExecutionError, "unavailable surface ID"):
                EngineeringOrchestrator._gmsh_volume_mesh(
                    prepared,
                    mesh_path,
                    8.0,
                    0,
                    1.18,
                    recipe,
                )

        with self.assertRaisesRegex(EngineeringExecutionError, "both inlet and outlet"):
            EngineeringOrchestrator.normalize_mesh_boundary_groups(
                {
                    "fields": {
                        "Inlet surface IDs": "1",
                        "Outlet surface IDs": "1",
                    }
                }
            )


if __name__ == "__main__":
    unittest.main()
