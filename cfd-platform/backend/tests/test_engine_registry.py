"""Regression coverage for local-engine inventory efficiency."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from cfd_backend.services.engine_registry import EngineCapability, EngineRegistry


class CountingRegistry(EngineRegistry):
    """Avoid real executable/import probes while retaining registry semantics."""

    def __init__(self) -> None:
        super().__init__(SimpleNamespace())  # type: ignore[arg-type]
        self.probe_count = 0

    async def _probe(self, definition):  # type: ignore[no-untyped-def,override]
        self.probe_count += 1
        return EngineCapability(
            id=definition.id,
            display_name=definition.display_name,
            workflow=list(definition.workflow),
            runtime=definition.runtime,
            optional=definition.optional,
            adapter=definition.adapter,
            status="ready",
        )


class TestEngineRegistry(unittest.IsolatedAsyncioTestCase):
    async def test_requirement_refresh_probes_inventory_once(self) -> None:
        registry = CountingRegistry()

        available, unavailable = await registry.requirements_available(
            ("gmsh", "meshio", "vtk", "pyvista"), refresh=True
        )

        self.assertTrue(available)
        self.assertEqual(unavailable, [])
        self.assertEqual(registry.probe_count, len(registry.definitions))
