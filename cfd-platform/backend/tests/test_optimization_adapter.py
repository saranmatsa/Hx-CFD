"""Contract coverage for real OpenMDAO/Nevergrad optimization evaluations."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cfd_backend.services.engineering_orchestrator import (
    EngineeringExecutionError,
    EngineeringOrchestrator,
)


class TestOptimizationAdapter(unittest.TestCase):
    def test_rejects_non_finite_evaluator_result(self) -> None:
        """A failed CFD evaluator cannot become a misleading optimization run."""
        with tempfile.TemporaryDirectory(prefix="hx-cfd-optimization-nonfinite-") as temporary:
            root = Path(temporary)
            evaluator = root / "evaluator.py"
            evaluator.write_text(
                "def evaluate(design):\n    return float('nan')\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(EngineeringExecutionError, "non-finite objective"):
                EngineeringOrchestrator._run_openmdao_nevergrad(
                    evaluator,
                    "chord",
                    0.8,
                    1.2,
                    1,
                    root,
                )
