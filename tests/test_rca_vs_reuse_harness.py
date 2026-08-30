import unittest
import os
import tempfile
from pathlib import Path

from src.evaluation.rca_vs_reuse_harness import (
    RCABackend,
    RCADiagnosisResult,
    DeterministicProxyRCABackend,
    RCAReuseEvaluator
)


class MockConstantRCABackend(RCABackend):
    """Simple mock backend for testing evaluation harness mechanics."""
    def __init__(self, fixed_signal: str = "count", is_correct: bool = True):
        self.fixed_signal = fixed_signal
        self.is_correct = is_correct
        self.call_count = 0

    def diagnose_failure(self, task_id: str, design_family: str, metadata: dict) -> RCADiagnosisResult:
        self.call_count += 1
        return RCADiagnosisResult(
            task_id=task_id,
            design_family=design_family,
            root_cause_signal=self.fixed_signal,
            is_correct=self.is_correct,
            steps_taken=4,
            tool_calls=4,
            simulations=1,
            waveform_queries=2,
            llm_calls=0,
            llm_tokens=-1,
            backend_type="MOCK_TEST_BACKEND",
            wall_clock_ms=10.0,
            trajectory_summary={"outcome": "SUCCESS"}
        )


class TestRCAReuseHarness(unittest.TestCase):
    """Unit tests for the RCAReuseEvaluator and controlled comparison accounting."""

    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.rtl_dir = str(self.root / "rtl")

    def test_mock_backend_evaluation(self):
        backend = MockConstantRCABackend(fixed_signal="count", is_correct=True)
        evaluator = RCAReuseEvaluator(backend=backend, rtl_dir=self.rtl_dir)

        stream = [
            {
                "target_id": "heldout_fifo_src",
                "design_family": "fifo",
                "defect_mechanism": "FIFO_SIMULTANEOUS_RW",
                "is_source": True,
                "ground_truth_match": "MATCH",
                "ground_truth_signals": ["count"],
                "symptom": "Data Mismatch",
                "target_signals": ["count", "write_en", "read_en"]
            },
            {
                "target_id": "fifo_vl_b1",
                "design_family": "fifo",
                "defect_mechanism": "FIFO_SIMULTANEOUS_RW",
                "is_source": False,
                "ground_truth_match": "MATCH",
                "ground_truth_signals": ["count"],
                "symptom": "Data Mismatch",
                "target_signals": ["count", "write_en", "read_en"]
            }
        ]

        summary = evaluator.evaluate_stream(stream)
        op = summary["operational_metrics"]
        sa = summary["safety_and_accuracy_metrics"]

        # 1 source + 1 target
        self.assertEqual(op["baseline_full_rca_invocations"], 2)
        self.assertEqual(op["reuse_attempts"], 1)
        # Sum of reuses and fallbacks must equal total target attempts
        self.assertEqual(op["successful_reuses"] + op["fallback_rca_executions"], op["reuse_attempts"])

    def test_deterministic_proxy_backend_instantiation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = DeterministicProxyRCABackend(rtl_dir=self.rtl_dir, log_dir=tmpdir, seed=42)
            meta = {
                "bug_id": "fifo_f1",
                "family": "fifo",
                "ground_truth_module": "fifo",
                "ground_truth_signals": ["count"],
                "symptom": "Data Mismatch"
            }
            res = backend.diagnose_failure("fifo_f1", "fifo", meta)
            self.assertEqual(res.task_id, "fifo_f1")
            self.assertEqual(res.backend_type, "DETERMINISTIC_LOCAL_PROXY")
            self.assertEqual(res.llm_tokens, -1)
            self.assertGreater(res.wall_clock_ms, 0.0)


if __name__ == "__main__":
    unittest.main()
