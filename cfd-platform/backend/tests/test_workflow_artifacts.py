"""Regression coverage for the path-free desktop artifact contract."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cfd_backend.services.workflow_service import LocalWorkflowService


class ArtifactRegistry:
    """Only the inventory contract is needed for a durable snapshot."""

    async def inventory(self, refresh: bool = False) -> list[dict[str, str]]:
        del refresh
        return []


class TestWorkflowArtifacts(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_reads_and_exports_project_evidence_without_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-artifacts-") as temporary:
            root = Path(temporary)
            workflow = LocalWorkflowService(
                SimpleNamespace(projects_dir=root / "projects"), ArtifactRegistry()  # type: ignore[arg-type]
            )
            project_id = "artifact-contract"
            project = await workflow.create_project(project_id)
            project_path = root / "projects" / project_id
            job_id = "a" * 32
            run_path = project_path / "runs" / "reports" / job_id
            run_path.mkdir(parents=True)
            report = run_path / "report.html"
            report.write_text("<h1>HX CFD report</h1>", encoding="utf-8")
            log = project_path / "logs" / f"{job_id}.log"
            log.write_text("report generated", encoding="utf-8")
            reference = project_path / "refs" / "reports" / "latest.json"
            reference.parent.mkdir(parents=True, exist_ok=True)
            reference.write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "output": {
                            "engines": ["VTK", "PyVista"],
                            "artifacts": [str(report)],
                            "report": str(report),
                            "log_artifact_id": str(log),
                            "run_path": str(run_path),
                        },
                    }
                ),
                encoding="utf-8",
            )
            workflow._write_job(  # noqa: SLF001 - creates a real durable ledger fixture
                project_path,
                {
                    "id": job_id,
                    "stage": "reports",
                    "state": "SUCCEEDED",
                    "recipe": {},
                    "created_at": workflow._now(),  # noqa: SLF001
                    "updated_at": workflow._now(),  # noqa: SLF001
                    "error": None,
                    "log_artifact_id": str(log),
                },
            )

            self.assertNotIn("project_path", project)
            artifacts = await workflow.list_artifacts(project_id)
            self.assertEqual({artifact["name"] for artifact in artifacts}, {"report.html", f"{job_id}.log"})
            self.assertNotIn(str(project_path), json.dumps(artifacts))
            report_descriptor = next(artifact for artifact in artifacts if artifact["name"] == "report.html")

            content = await workflow.read_artifact(project_id, report_descriptor["artifact_id"])
            self.assertEqual(content["encoding"], "utf-8")
            self.assertEqual(content["content"], "<h1>HX CFD report</h1>")
            self.assertNotIn(str(project_path), json.dumps(content))

            destination = root / "exports" / "decision.html"
            destination.parent.mkdir()
            exported = await workflow.export_artifact(
                project_id, report_descriptor["artifact_id"], str(destination)
            )
            self.assertTrue(exported["exported"])
            self.assertEqual(exported["name"], "decision.html")
            self.assertEqual(destination.read_text(encoding="utf-8"), "<h1>HX CFD report</h1>")
            self.assertNotIn(str(destination), json.dumps(exported))

            with self.assertRaisesRegex(ValueError, "outside the active HX CFD project"):
                await workflow.export_artifact(
                    project_id,
                    report_descriptor["artifact_id"],
                    str(project_path / "overwritten.html"),
                )

            snapshot = await workflow.snapshot(project_id)
            self.assertNotIn(str(project_path), json.dumps(snapshot))
            self.assertEqual(
                snapshot["latest_outputs"]["reports"]["report_artifact"]["artifact_id"],
                report_descriptor["artifact_id"],
            )


if __name__ == "__main__":
    unittest.main()
