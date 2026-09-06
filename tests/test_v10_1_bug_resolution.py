"""
tests/test_v10_1_bug_resolution.py

Comprehensive unit and integration tests for Experiment V10.1:
- Deterministic Resolution Evaluator on all 5 hardware families
- False reuse classification on adversarial negative defects
- Token and LLM call accounting invariants
- System A memory isolation (zero certificate access)
- System B fallback behavior on negative and truncated targets
- Experiment manifest integrity and consistency
"""

import os
import json
import unittest
from pathlib import Path

from src.evaluation.deterministic_resolution import (
    DeterministicResolutionEvaluator,
    DeterministicPatchSynthesizer,
    ResolutionResult
)
from src.reuse.v8_certificate_store import V8CertificateStore
from src.reuse.v8_deterministic_ingestion import DeterministicSourceIngestion
from experiments.run_v10_1_plain_llm_rca import run_plain_llm_rca
from experiments.run_v10_1_llm_reuse_rca import run_llm_reuse_rca


class TestV10_1_BugResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace_root = Path(__file__).resolve().parents[1]
        cls.evaluator = DeterministicResolutionEvaluator(workspace_root=str(cls.workspace_root))
        cls.manifest_path = cls.workspace_root / "results" / "reports" / "v10_1_experiment_manifest.json"

    def test_case_manifest_consistency(self):
        """Verifies that the frozen 25-case experiment manifest matches all structural invariants."""
        self.assertTrue(self.manifest_path.exists(), "Manifest file must exist")
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        cases = manifest.get("cases", [])
        self.assertEqual(len(cases), 25, "Manifest must contain exactly 25 cases")

        families = set(c["hardware_family"] for c in cases)
        self.assertEqual(families, {"fifo", "axi", "fsm", "uart", "pipeline"})

        source_count = sum(1 for c in cases if c["role"] == "SOURCE")
        self.assertEqual(source_count, 5, "Must have exactly 1 source per family (5 total)")

        positive_count = sum(1 for c in cases if c["case_type"] == "POSITIVE_REUSE_OPPORTUNITY")
        self.assertEqual(positive_count, 10, "Must have exactly 10 positive reuse targets (2 per family)")

        adv_count = sum(1 for c in cases if c["case_type"] == "ADVERSARIAL_NEGATIVE")
        self.assertEqual(adv_count, 5, "Must have exactly 5 adversarial negative targets (1 per family)")

        trunc_count = sum(1 for c in cases if c["case_type"] == "INCOMPLETE_TRACE_NEGATIVE")
        self.assertEqual(trunc_count, 5, "Must have exactly 5 incomplete trace targets (1 per family)")

    def test_deterministic_resolution_all_families_positive(self):
        """Verifies that diagnosing the true root-cause signal synthesizes valid patches and passes assertions."""
        test_cases = [
            ("heldout_fifo_src", "fifo", "count", "count"),
            ("heldout_axi_src", "axi", "valid_out", "valid_out"),
            ("heldout_fsm_src", "fsm", "state", "state"),
            ("heldout_uart_src", "uart", "cnt", "cnt"),
            ("heldout_pipe_src", "pipeline", "v1", "v1")
        ]

        for case_id, family, pred_sig, gt_sig in test_cases:
            res = self.evaluator.evaluate_resolution(case_id, family, pred_sig, gt_sig)
            self.assertTrue(res.patch_synthesized, f"Patch must synthesize for {case_id}")
            self.assertTrue(res.compiled_cleanly, f"Must compile cleanly for {case_id}: {res.compile_error}")
            self.assertTrue(res.assertions_passed, f"Assertions must pass for {case_id}: {res.sim_output}")
            self.assertTrue(res.is_resolved, f"Bug must be marked RESOLVED for {case_id}")

    def test_deterministic_resolution_negative_and_wrong_diagnoses(self):
        """Verifies that wrong diagnoses, empty signals, or unknown signals fail resolution."""
        wrong_cases = [
            ("heldout_fifo_src", "fifo", "write_ptr", "count"),
            ("heldout_axi_src", "axi", "ready_in", "valid_out"),
            ("heldout_fsm_src", "fsm", "done", "state"),
            ("heldout_uart_src", "uart", "tx", "cnt"),
            ("heldout_pipe_src", "pipeline", "d1", "v1"),
            ("heldout_fifo_src", "fifo", "unknown", "count"),
            ("heldout_axi_src", "axi", "", "valid_out")
        ]

        for case_id, family, pred_sig, gt_sig in wrong_cases:
            res = self.evaluator.evaluate_resolution(case_id, family, pred_sig, gt_sig)
            self.assertFalse(res.is_resolved, f"Wrong diagnosis {pred_sig} on {case_id} must NOT be resolved")

    def test_false_reuse_classification(self):
        """Verifies that mistakenly applying source certificates to adversarial negatives is caught as false reuse."""
        adversarial_tests = [
            ("fifo_vl_f1", "fifo", "count", "write_ptr"),      # Reusing count on ptr defect
            ("axi_vl_f1", "axi", "valid_out", "ready_out"),    # Reusing valid_out on ready defect
            ("fsm_vl_f1", "fsm", "state", "done"),             # Reusing state on timing defect
            ("uart_vl_f1", "uart", "cnt", "tx"),               # Reusing cnt on stop-bit defect
            ("pipeline_vl_f1", "pipeline", "v1", "d1")         # Reusing v1 on data hazard defect
        ]

        for case_id, family, false_diag, gt_sig in adversarial_tests:
            res = self.evaluator.evaluate_resolution(case_id, family, false_diag, gt_sig)
            self.assertFalse(res.is_resolved, f"False reuse on adversarial case {case_id} must fail assertion verification")

    def test_system_a_isolation(self):
        """Verifies that System A (Plain LLM RCA) never accesses certificate memory and has 0 reuses."""
        sys_a_summary = run_plain_llm_rca()
        self.assertEqual(sys_a_summary["rca_investigations_avoided"], 0)
        self.assertEqual(sys_a_summary["full_rca_investigations"], 25)

        for rec in sys_a_summary["records"]:
            self.assertNotIn("reused_prior_rca", rec)
            self.assertGreaterEqual(rec["llm_calls"], 1, "System A must execute LLM call on every case")

    def test_token_and_call_accounting_invariants(self):
        """Verifies that System B achieves strict token and LLM call reductions on accepted reuses."""
        sys_a = run_plain_llm_rca()
        sys_b = run_llm_reuse_rca()

        self.assertGreater(sys_a["total_llm_tokens"], sys_b["total_llm_tokens"])
        self.assertGreater(sys_a["total_llm_calls"], sys_b["total_llm_calls"])
        self.assertGreater(sys_b["rca_investigations_avoided"], 0)

        # On every accepted reuse in System B, LLM calls and tokens must be 0
        for rec in sys_b["records"]:
            if rec["reused_prior_rca"]:
                self.assertEqual(rec["llm_calls"], 0, f"Case {rec['case_id']} reused RCA but recorded non-zero calls")
                self.assertEqual(rec["tokens"], 0, f"Case {rec['case_id']} reused RCA but recorded non-zero tokens")

    def test_system_b_safety_and_fallback(self):
        """Verifies that System B preserves 0 false reuses and 100% negative target rejection."""
        sys_b = run_llm_reuse_rca()
        self.assertEqual(sys_b["false_reuses"], 0, "System B must maintain 0 false reuses")
        self.assertEqual(sys_b["reuse_precision"], 1.0, "Reuse precision must be 100%")
        self.assertEqual(sys_b["negative_rejection_rate"], 1.0, "Negative rejection rate must be 100%")
        self.assertEqual(sys_b["safe_rejections"], 10, "All 10 negative targets must be safely rejected")


if __name__ == "__main__":
    unittest.main()
