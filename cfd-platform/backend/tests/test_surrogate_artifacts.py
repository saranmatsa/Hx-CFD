"""Truthfulness coverage for the project-owned PhysicsNeMo surrogate adapter."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cfd_backend.core.config import Settings
from cfd_backend.services.engineering_orchestrator import (
    EngineeringExecutionError,
    EngineeringOrchestrator,
)


class _ReadySurrogateRegistry:
    async def requirements_available(self, engine_ids, refresh: bool = False):
        return True, []

    def worker_environment(self, engine_id: str) -> dict[str, str]:
        return {}


class _ControlledSurrogateOrchestrator(EngineeringOrchestrator):
    """Exercise the adapter's output contract without a GPU training run."""

    def __init__(self, settings: Settings, *, publish_model: bool):
        super().__init__(settings, _ReadySurrogateRegistry())  # type: ignore[arg-type]
        self.publish_model = publish_model

    async def _require(self, engine_ids):  # type: ignore[override]
        return None

    async def _engine_executable(self, engine_id: str) -> str:  # type: ignore[override]
        return "physicsnemo-python"

    async def _run(self, arguments, cwd, timeout=1800, environment=None):  # type: ignore[override]
        model_root = Path(arguments[4])
        result_file = Path(arguments[5])
        if self.publish_model:
            model_root.mkdir(parents=True, exist_ok=True)
            (model_root / "checkpoint.bin").write_bytes(b"trained-model")
        result_file.write_text(json.dumps({"result": {"loss": 0.01}}), encoding="utf-8")
        return "trainer completed"


class TestSurrogateArtifacts(unittest.IsolatedAsyncioTestCase):
    async def _run_training(self, root: Path, *, publish_model: bool) -> dict:
        project = root / "project"
        run_path = project / "runs" / "surrogate" / "job"
        run_path.mkdir(parents=True)
        trainer = root / "trainer.py"
        trainer.write_text("def train(dataset_path, output_path): pass\n", encoding="utf-8")
        dataset = root / "dataset.csv"
        dataset.write_text("x,y\n0,0\n", encoding="utf-8")
        settings = Settings(
            data_dir=root / "data",
            logs_dir=root / "logs",
            projects_dir=root / "projects",
            temp_dir=root / "tmp",
            cache_dir=root / "cache",
        )
        adapter = _ControlledSurrogateOrchestrator(settings, publish_model=publish_model)
        return await adapter._train_surrogate(
            project,
            run_path,
            {"fields": {"Training module": str(trainer), "Dataset path": str(dataset)}},
        )

    async def test_publishes_real_model_files_as_exportable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-surrogate-artifacts-") as temporary:
            output = await self._run_training(Path(temporary), publish_model=True)

            artifact_names = {Path(path).name for path in output["artifacts"]}
            self.assertEqual(
                artifact_names,
                {"surrogate.json", "surrogate-model-manifest.json", "checkpoint.bin"},
            )
            self.assertEqual(output["surrogate"]["model_artifact_count"], 1)
            manifest = Path(output["surrogate"]["model_manifest"])
            self.assertEqual(
                json.loads(manifest.read_text(encoding="utf-8"))["files"],
                [{"relative_path": "checkpoint.bin", "size_bytes": len(b"trained-model")}],
            )

    async def test_rejects_a_trainer_that_reports_success_without_a_model(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-surrogate-missing-") as temporary:
            with self.assertRaisesRegex(EngineeringExecutionError, "without publishing a model artifact"):
                await self._run_training(Path(temporary), publish_model=False)
