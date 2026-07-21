"""Coverage for real local PDF report publication from CFD evidence."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cfd_backend.services.engineering_orchestrator import (
    EngineeringExecutionError,
    EngineeringOrchestrator,
)


class ReportRegistry:
    """Only the report adapter's engine readiness contract is needed here."""

    async def requirements_available(
        self, engine_ids: tuple[str, ...], refresh: bool = False
    ) -> tuple[bool, list[dict[str, str]]]:
        del engine_ids, refresh
        return True, []


@unittest.skipUnless(
    importlib.util.find_spec("matplotlib") and importlib.util.find_spec("pyvista"),
    "requires the managed local PDF and VTK toolchain",
)
class TestPdfReport(unittest.IsolatedAsyncioTestCase):
    async def test_publishes_pdf_from_verified_vtk_and_preview_evidence(self) -> None:
        import pyvista as pv
        from matplotlib.figure import Figure

        with tempfile.TemporaryDirectory(prefix="hx-cfd-pdf-report-") as temporary:
            project = Path(temporary) / "project"
            result_run = project / "runs" / "results" / "result-job"
            result_run.mkdir(parents=True)
            dataset_path = result_run / "result.vtk"
            preview_path = result_run / "result-preview.png"

            # This is a genuine VTK dataset and a real image artifact; the
            # report adapter reopens both rather than trusting test metadata.
            source = pv.Sphere(theta_resolution=10, phi_resolution=10)
            source["Pressure"] = source.points[:, 2]
            source.save(dataset_path)
            Figure(figsize=(2, 1.2)).savefig(preview_path)
            verified = pv.read(dataset_path)
            summary = {
                "dataset": str(dataset_path),
                "preview": str(preview_path),
                "points": int(verified.n_points),
                "cells": int(verified.n_cells),
                "bounds": [float(value) for value in verified.bounds],
                "arrays": [str(name) for name in verified.array_names],
                "vtk_version": "test-verified",
            }
            reference = project / "refs" / "results" / "latest.json"
            reference.parent.mkdir(parents=True)
            reference.write_text(json.dumps({"job_id": "result-job", "output": {"results": summary}}))

            report_run = project / "runs" / "reports" / "report-job"
            report_run.mkdir(parents=True)
            orchestrator = EngineeringOrchestrator(SimpleNamespace(), ReportRegistry())  # type: ignore[arg-type]
            output = await orchestrator._publish_report(  # noqa: SLF001 - adapter integration coverage
                project,
                report_run,
                {"fields": {"Template": "Engineering review"}},
            )

            pdf = report_run / "report.pdf"
            companion = report_run / "report.html"
            self.assertEqual(output["report"], str(pdf))
            self.assertTrue(pdf.is_file())
            self.assertTrue(companion.is_file())
            self.assertGreater(pdf.stat().st_size, 1000)
            self.assertEqual(pdf.read_bytes()[:4], b"%PDF")
            self.assertIn("Verified dataset", companion.read_text(encoding="utf-8"))
            self.assertEqual(output["report_evidence"]["points"], int(verified.n_points))

    async def test_rejects_report_without_published_results(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hx-cfd-pdf-report-missing-") as temporary:
            project = Path(temporary) / "project"
            project.mkdir()
            report_run = project / "runs" / "reports" / "report-job"
            report_run.mkdir(parents=True)
            orchestrator = EngineeringOrchestrator(SimpleNamespace(), ReportRegistry())  # type: ignore[arg-type]

            with self.assertRaisesRegex(EngineeringExecutionError, "No successful results artifact"):
                await orchestrator._publish_report(  # noqa: SLF001 - adapter integration coverage
                    project,
                    report_run,
                    {"fields": {"Template": "Performance summary"}},
                )
