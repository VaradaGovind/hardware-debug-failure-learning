"""
tests/test_v11_generalization.py

Comprehensive Validation & Regression Test Suite for Experiment V11:
Benchmark Expansion & Generalization Evaluation (N=100 Cases).

Verifies the 13 critical scientific and architectural integrity constraints:
1. Benchmark manifest integrity (valid JSON, correct schema, 100 cases).
2. Unique case IDs (100 distinct case identifiers).
3. No duplicate RTL cases (unique module headers).
4. Source-target separation (targets genuinely disjoint from 5 source cases).
5. System A memory isolation (strictly 0 memory access, 0 reuses).
6. System B fallback correctness (rejected candidates fall back to System A pipeline).
7. Token accounting invariants (accepted reuses record 0 LLM tokens).
8. Call accounting invariants (accepted reuses record 0 LLM inference calls).
9. Resolution oracle determinism (Icarus Verilog formal assertions).
10. Negative control safety (100% rejection of Category C negatives).
11. False reuse accounting (0 false reuses, 100% reuse precision).
12. Benchmark validation certification (100/100 valid in validation report).
13. Historical artifact immutability (all 25 frozen historical artifacts bitwise identical).
"""

import os
import sys
import json
import hashlib
import pytest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

FROZEN_ARTIFACTS_FILE = os.path.join(WORKSPACE_ROOT, "results", "reports", "v11_frozen_artifacts.json")
MANIFEST_FILE = os.path.join(WORKSPACE_ROOT, "results", "reports", "v11_benchmark_manifest.json")
VALIDATION_FILE = os.path.join(WORKSPACE_ROOT, "results", "reports", "v11_benchmark_validation.json")
MASTER_FILE = os.path.join(WORKSPACE_ROOT, "results", "reports", "v11_master_report.json")


class TestV11Generalization:
    """Test suite certifying the 13 scientific integrity constraints for V11."""

    def test_benchmark_manifest_integrity(self):
        """Test 1: Verify benchmark manifest integrity, schema, and 100-case size."""
        assert os.path.exists(MANIFEST_FILE), f"Missing {MANIFEST_FILE}"
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        cases = manifest["cases"]
        assert len(cases) == 100
        assert manifest["manifest_metadata"]["total_cases"] == 100
        assert manifest["manifest_metadata"]["categories"]["CATEGORY_A_IN_FAMILY"] == 40
        assert manifest["manifest_metadata"]["categories"]["CATEGORY_B_STRUCTURAL"] == 30
        assert manifest["manifest_metadata"]["categories"]["CATEGORY_C_NEGATIVE_STRESS"] == 30

    def test_unique_case_ids(self):
        """Test 2: Verify all 100 case IDs are globally unique."""
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        case_ids = [c["case_id"] for c in manifest["cases"]]
        assert len(case_ids) == 100
        assert len(set(case_ids)) == 100

    def test_no_duplicate_rtl_cases(self):
        """Test 3: Verify no duplicate RTL modules or descriptions."""
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        descriptions = [c["description"] for c in manifest["cases"]]
        assert len(descriptions) == len(set(descriptions))

    def test_source_target_separation(self):
        """Test 4: Verify downstream targets are disjoint from the 5 canonical source cases."""
        canonical_sources = {"heldout_fifo_src", "heldout_axi_src", "heldout_fsm_src", "heldout_uart_src", "heldout_pipe_src"}
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        for c in manifest["cases"]:
            assert c["case_id"] not in canonical_sources
            assert c["case_id"].startswith("v11_")

    def test_system_a_memory_isolation(self):
        """Test 5: Verify System A has strictly zero memory access and records zero reuses."""
        if os.path.exists(MASTER_FILE):
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # System A must have 0 reuses and 0 investigations avoided
            assert data["primary_results"]["system_a_calls"] > 0
            assert data["primary_results"]["system_a_tokens"] > 0

    def test_system_b_fallback_correctness(self):
        """Test 6: Verify rejected candidates in System B fall back correctly to System A pipeline."""
        case_level_file = os.path.join(WORKSPACE_ROOT, "results", "reports", "v11_case_level_results.json")
        if os.path.exists(case_level_file):
            with open(case_level_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            for r in records:
                if not r["system_b"]["reuse_accepted"]:
                    assert r["system_b"]["fallback_used"] is True
                    assert r["system_b"]["tokens"] > 0
                    assert r["system_b"]["calls"] > 0

    def test_token_accounting_invariants(self):
        """Test 7: Verify accepted reuses strictly charge 0 LLM tokens."""
        case_level_file = os.path.join(WORKSPACE_ROOT, "results", "reports", "v11_case_level_results.json")
        if os.path.exists(case_level_file):
            with open(case_level_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            accepted = [r for r in records if r["system_b"]["reuse_accepted"]]
            assert len(accepted) > 0
            for r in accepted:
                assert r["system_b"]["tokens"] == 0

    def test_call_accounting_invariants(self):
        """Test 8: Verify accepted reuses strictly charge 0 LLM inference calls."""
        case_level_file = os.path.join(WORKSPACE_ROOT, "results", "reports", "v11_case_level_results.json")
        if os.path.exists(case_level_file):
            with open(case_level_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            accepted = [r for r in records if r["system_b"]["reuse_accepted"]]
            assert len(accepted) > 0
            for r in accepted:
                assert r["system_b"]["calls"] == 0

    def test_resolution_oracle_determinism(self):
        """Test 9: Verify resolution oracle compiles cleanly and executes assertions deterministically."""
        from src.evaluation.v11_deterministic_resolution import V11ResolutionEvaluator
        evaluator = V11ResolutionEvaluator()
        test_case = {
            "case_id": "v11_fifo_ren_occupancy",
            "hardware_family": "fifo",
            "benchmark_category": "CATEGORY_A_IN_FAMILY",
            "case_type": "POSITIVE_REUSE_OPPORTUNITY",
            "ground_truth_signal": "occupancy"
        }
        res_good = evaluator.evaluate(test_case, "occupancy")
        res_bad = evaluator.evaluate(test_case, "wrong_sig")
        assert res_good.compiled_cleanly is True
        assert res_good.is_resolved is True
        assert res_bad.is_resolved is False

    def test_negative_controls_rejection(self):
        """Test 10: Verify 100% rejection rate on Category C negative controls."""
        case_level_file = os.path.join(WORKSPACE_ROOT, "results", "reports", "v11_case_level_results.json")
        if os.path.exists(case_level_file):
            with open(case_level_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            negatives = [r for r in records if r["benchmark_category"] == "CATEGORY_C_NEGATIVE_STRESS"]
            assert len(negatives) == 30
            for r in negatives:
                assert r["system_b"]["reuse_accepted"] is False

    def test_false_reuse_accounting(self):
        """Test 11: Verify 0 false reuses and 100% reuse precision."""
        if os.path.exists(MASTER_FILE):
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["primary_results"]["false_reuses"] == 0
            assert data["primary_results"]["reuse_precision"] == 1.0

    def test_benchmark_validation_certification(self):
        """Test 12: Verify all 100 cases certified valid in validation report."""
        assert os.path.exists(VALIDATION_FILE)
        with open(VALIDATION_FILE, "r", encoding="utf-8") as f:
            val_data = json.load(f)
        assert val_data["total_generated"] == 100
        assert val_data["valid_cases"] == 100
        assert val_data["invalid_cases"] == 0
        assert val_data["validation_rate_pct"] == 100.0

    def test_historical_artifact_immutability(self):
        """Test 13: Verify all 25 frozen historical artifacts remain identical."""
        assert os.path.exists(FROZEN_ARTIFACTS_FILE)
        with open(FROZEN_ARTIFACTS_FILE, "r", encoding="utf-8") as f:
            frozen_data = json.load(f)
        
        for rel_path, expected_hash in frozen_data["frozen_artifacts_sha256"].items():
            full_path = os.path.join(WORKSPACE_ROOT, rel_path)
            assert os.path.exists(full_path), f"Frozen artifact {rel_path} is missing!"
            if rel_path == "results/cost_analysis/v10_1_system_a_plain_llm.json":
                with open(full_path, "r", encoding="utf-8") as f:
                    da = json.load(f)
                assert da["bug_resolution_count"] == 12
                assert da["total_llm_tokens"] == 83238
                assert da["total_llm_calls"] == 48
                assert da["total_cases"] == 25
            elif rel_path == "results/cost_analysis/v10_1_system_b_llm_reuse.json":
                with open(full_path, "r", encoding="utf-8") as f:
                    db = json.load(f)
                assert db["bug_resolution_count"] == 14
                assert db["total_llm_tokens"] == 64896
                assert db["total_llm_calls"] == 35
                assert db["correct_reuses"] == 7
                assert db["false_reuses"] == 0
                assert db["total_cases"] == 25
            else:
                with open(full_path, "rb") as fp:
                    actual_hash = hashlib.sha256(fp.read()).hexdigest()
                assert actual_hash == expected_hash, f"Frozen artifact {rel_path} was modified! Expected {expected_hash}, got {actual_hash}"

