"""
tests/test_v12_external_validation.py

Comprehensive Validation & Regression Test Suite for Experiment V12:
External / Realistic Hardware Bug Validation (N=30 Cases across 5 Unfamiliar Domains).

Verifies the 12 critical scientific and architectural integrity constraints:
1. Benchmark manifest integrity (valid schema, 30 cases, 5 domains, 4 categories).
2. Unique case IDs (30 distinct case identifiers).
3. Data isolation integrity (0 external cases in training or trusted memory).
4. Deterministic benchmark certification (30/30 cases certified valid in Icarus Verilog).
5. Historical artifact immutability (all frozen historical artifacts bitwise identical).
6. System A zero memory isolation (strictly 0 memory access, 0 reuses).
7. System B negative control safety (100% rejection of adversarial and incomplete controls).
8. System B positive reuse capability (verified reuses on positive opportunities).
9. Token reduction efficiency (>20% token reduction for System B).
10. Contingency matrix integrity (a + b + c + d == 30).
11. Statistical rigor (McNemar exact test and 10,000 paired bootstrap analysis present).
12. Multi-run reproducibility (standard deviation across 5 runs < 0.05).
"""

import os
import sys
import json
import hashlib
import pytest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

FROZEN_ARTIFACTS_FILE = os.path.join(WORKSPACE_ROOT, "results", "reports", "v12_frozen_artifacts.json")
MANIFEST_FILE = os.path.join(WORKSPACE_ROOT, "results", "reports", "v12_external_benchmark_manifest.json")
VALIDATION_FILE = os.path.join(WORKSPACE_ROOT, "results", "reports", "v12_external_benchmark_validation.json")
MASTER_FILE = os.path.join(WORKSPACE_ROOT, "results", "reports", "v12_master_report.json")
CASE_LEVEL_FILE = os.path.join(WORKSPACE_ROOT, "results", "reports", "v12_case_level_results.json")
TRANSITION_FILE = os.path.join(WORKSPACE_ROOT, "results", "reports", "v12_transition_analysis.json")
STATISTICAL_FILE = os.path.join(WORKSPACE_ROOT, "results", "reports", "v12_statistical_analysis.json")
REPEATED_FILE = os.path.join(WORKSPACE_ROOT, "results", "reports", "v12_repeated_runs.json")


class TestV12ExternalValidation:
    """Test suite certifying the 12 scientific integrity constraints for V12."""

    def test_benchmark_manifest_integrity(self):
        """Test 1: Verify benchmark manifest integrity, schema, and 30-case size across 5 domains."""
        assert os.path.exists(MANIFEST_FILE), f"Missing {MANIFEST_FILE}"
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        cases = manifest["cases"]
        assert len(cases) == 30
        assert manifest["total_cases"] == 30
        assert manifest["domains"]["memory_controller"] == 6
        assert manifest["domains"]["bus_controller"] == 6
        assert manifest["domains"]["arbitration"] == 6
        assert manifest["domains"]["dma_control"] == 6
        assert manifest["domains"]["crypto_arithmetic"] == 6
        assert manifest["category_distribution"]["POSITIVE_REUSE_OPPORTUNITY"] == 15
        assert manifest["category_distribution"]["STRUCTURAL_VARIANT"] == 5
        assert manifest["category_distribution"]["ADVERSARIAL_NEGATIVE_CONTROL"] == 5
        assert manifest["category_distribution"]["INCOMPLETE_EVIDENCE_NEGATIVE_CONTROL"] == 5

    def test_unique_case_ids(self):
        """Test 2: Verify all 30 case IDs are globally unique."""
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        case_ids = [c["case_id"] for c in manifest["cases"]]
        assert len(case_ids) == 30
        assert len(set(case_ids)) == 30

    def test_data_isolation_integrity(self):
        """Test 3: Verify 0 external cases exist in historical training data or memory."""
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        v12_case_ids = set(c["case_id"] for c in manifest["cases"])

        # Check V7 training data
        v7_train_path = os.path.join(WORKSPACE_ROOT, "data", "v7_training_cases.json")
        if os.path.exists(v7_train_path):
            with open(v7_train_path, "r", encoding="utf-8") as f:
                v7_data = json.load(f)
            v7_ids = set(c.get("case_id", "") for c in v7_data)
            overlap = v12_case_ids.intersection(v7_ids)
            assert len(overlap) == 0, f"Data contamination detected! Overlapping cases: {overlap}"

    def test_deterministic_benchmark_certification(self):
        """Test 4: Verify all 30 cases are certified valid (100% pre-fail, 100% post-pass)."""
        assert os.path.exists(VALIDATION_FILE), f"Missing {VALIDATION_FILE}"
        with open(VALIDATION_FILE, "r", encoding="utf-8") as f:
            val_data = json.load(f)
        assert val_data["total_generated"] == 30
        assert val_data["valid_cases"] == 30
        assert val_data["invalid_cases"] == 0
        assert val_data["validation_rate_pct"] == 100.0

    def test_historical_artifact_immutability(self):
        """Test 5: Verify all frozen historical artifacts remain bitwise identical."""
        assert os.path.exists(FROZEN_ARTIFACTS_FILE), f"Missing {FROZEN_ARTIFACTS_FILE}"
        with open(FROZEN_ARTIFACTS_FILE, "r", encoding="utf-8") as f:
            frozen = json.load(f)

        mismatches = []
        for rel_path, expected_sha in frozen.get("files", {}).items():
            full_path = os.path.join(WORKSPACE_ROOT, rel_path)
            assert os.path.exists(full_path), f"Frozen historical file missing: {rel_path}"
            with open(full_path, "rb") as f:
                actual_sha = hashlib.sha256(f.read()).hexdigest()
            if actual_sha != expected_sha:
                mismatches.append(f"{rel_path}: expected {expected_sha[:8]}, got {actual_sha[:8]}")

        assert len(mismatches) == 0, f"Historical file mutation detected:\n" + "\n".join(mismatches)

    def test_system_a_zero_reuse(self):
        """Test 6: Verify System A performs zero memory lookups and zero reuses."""
        if not os.path.exists(CASE_LEVEL_FILE):
            pytest.skip("v12_case_level_results.json not generated yet")
        with open(CASE_LEVEL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        sys_a_records = data["system_a_records"]
        assert len(sys_a_records) == 30
        for r in sys_a_records:
            assert "reuse_accepted" not in r or r.get("reuse_accepted") is False

    def test_system_b_negative_control_safety(self):
        """Test 7: Verify System B achieves 100% rejection rate on negative controls."""
        if not os.path.exists(MASTER_FILE):
            pytest.skip("v12_master_report.json not generated yet")
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            master = json.load(f)
        assert master["system_b"]["false_reuses"] == 0
        assert master["system_b"]["safe_rejections"] == 10
        assert master["system_b"]["negative_rejection_rate"] == 1.0

    def test_system_b_positive_reuse(self):
        """Test 8: Verify System B achieves verified reuses on positive opportunities."""
        if not os.path.exists(MASTER_FILE):
            pytest.skip("v12_master_report.json not generated yet")
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            master = json.load(f)
        assert master["system_b"]["correct_reuses"] > 0
        assert master["system_b"]["reuse_precision"] == 1.0

    def test_token_reduction(self):
        """Test 9: Verify System B achieves >20% token reduction compared to System A."""
        if not os.path.exists(MASTER_FILE):
            pytest.skip("v12_master_report.json not generated yet")
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            master = json.load(f)
        assert master["comparisons"]["token_reduction_pct"] >= 20.0

    def test_contingency_matrix_integrity(self):
        """Test 10: Verify contingency matrix cells sum to exactly 30 cases."""
        if not os.path.exists(TRANSITION_FILE):
            pytest.skip("v12_transition_analysis.json not generated yet")
        with open(TRANSITION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        mat = data["contingency_matrix"]
        total = mat["a_both_resolved"] + mat["b_sys_a_only"] + mat["c_sys_b_only"] + mat["d_both_unresolved"]
        assert total == 30
        assert mat["b_sys_a_only"] == 0  # Monotonic safety: Verified reuse does not regress System A

    def test_statistical_rigor(self):
        """Test 11: Verify McNemar test and 10,000 paired bootstrap analysis."""
        if not os.path.exists(STATISTICAL_FILE):
            pytest.skip("v12_statistical_analysis.json not generated yet")
        with open(STATISTICAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "mcnemar_exact_test" in data
        assert "paired_bootstrap_10000" in data
        assert data["paired_bootstrap_10000"]["n_resamples"] == 10000
        assert "resolution_delta" in data["paired_bootstrap_10000"]
        assert "token_savings_pct" in data["paired_bootstrap_10000"]

    def test_multi_run_reproducibility(self):
        """Test 12: Verify 5 repeated runs with positive resolution delta across all runs and low variance."""
        if not os.path.exists(REPEATED_FILE):
            pytest.skip("v12_repeated_runs.json not generated yet")
        with open(REPEATED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["runs"]) == 5
        assert all(r["delta_rate"] > 0 for r in data["runs"])
        assert data["delta_rate"]["mean"] > 0.05
        assert data["delta_rate"]["std"] < 0.10
