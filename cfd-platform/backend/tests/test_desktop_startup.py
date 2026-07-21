"""Regression coverage for the managed HX CFD backend startup path."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from cfd_backend.core.config import Settings
from cfd_backend.core.dependencies import ServiceContainer


class TestManagedDesktopStartup(unittest.IsolatedAsyncioTestCase):
    async def test_tauri_workflow_skips_optional_legacy_probes(self) -> None:
        """Desktop readiness must not wait for unused Redis or tool probes."""
        with tempfile.TemporaryDirectory(prefix="hx-cfd-desktop-startup-") as temporary:
            root = Path(temporary)
            settings = Settings(
                data_dir=root / "data",
                logs_dir=root / "logs",
                projects_dir=root / "projects",
                temp_dir=root / "tmp",
                cache_dir=root / "cache",
                database_url=f"sqlite+aiosqlite:///{(root / 'data' / 'cfd.db').as_posix()}",
            )
            container = ServiceContainer(settings)
            container.db.create_tables = AsyncMock()
            container.redis.ping = AsyncMock(return_value=False)
            container.tools.detect_all = AsyncMock(return_value={})
            container.engines.inventory = AsyncMock(return_value=[])

            with patch.dict(os.environ, {"CFD_PLATFORM_TAURI": "1"}, clear=False):
                await container.initialize()

            container.db.create_tables.assert_awaited_once()
            container.redis.ping.assert_not_awaited()
            container.tools.detect_all.assert_not_awaited()
            container.engines.inventory.assert_awaited_once_with(refresh=True)
            self.assertTrue(await container.is_ready())
