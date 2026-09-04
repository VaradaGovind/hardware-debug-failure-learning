import os
import json
import pytest
from typing import Dict, Any, List


CACHE_DIR = os.environ.get("RCA_REUSE_CACHE_DIR", os.path.expanduser("~/.cache/rca-reuse"))
FROZEN_TEST_IDS = {
    "heldout_fifo_src", "fifo_vl_a1", "fifo_vl_b1", "fifo_vl_f1", "fifo_vl_i2",
    "heldout_axi_src", "axi_vl_a1", "axi_vl_b1", "axi_vl_f1", "axi_vl_i2",
    "heldout_fsm_src", "fsm_vl_a1", "fsm_vl_b1", "fsm_vl_f1", "fsm_vl_i2",
    "heldout_uart_src", "uart_vl_a1", "uart_vl_b1", "uart_vl_f1", "uart_vl_i2",
    "heldout_pipe_src", "pipeline_vl_a1", "pipeline_vl_b1", "pipeline_vl_f1", "pipeline_vl_i2"
}


@pytest.fixture
def train_data() -> List[Dict[str, Any]]:
    path = os.path.join(CACHE_DIR, "datasets", "processed", "rca_train_v6.json")
    if not os.path.exists(path):
        pytest.skip(f"Train dataset not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def val_data() -> List[Dict[str, Any]]:
    path = os.path.join(CACHE_DIR, "datasets", "processed", "rca_val_v6.json")
    if not os.path.exists(path):
        pytest.skip(f"Val dataset not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def quality_report() -> Dict[str, Any]:
    path = os.path.join(CACHE_DIR, "datasets", "reports", "V6_DATASET_QUALITY_REPORT.json")
    if not os.path.exists(path):
        pytest.skip(f"Quality report not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestV6DatasetAndPipeline:
    """Test suite for V6 Dataset Verification and Zero-Leakage Guarantees."""

    def test_dataset_size_and_split(self, train_data, val_data, quality_report):
        """Verify train/val split and totals."""
        total = len(train_data) + len(val_data)
        assert total >= 300, f"Expected at least 300 total examples, got {total}"
        assert len(train_data) == quality_report["train_count"]
        assert len(val_data) == quality_report["val_count"]
        assert total == quality_report["total_examples_generated"]

    def test_zero_leakage_with_frozen_test_set(self, train_data, val_data):
        """CRITICAL: Programmatic assertion that NO frozen test case exists in train or val."""
        all_samples = train_data + val_data
        for s in all_samples:
            src_case = s.get("source_case", "")
            ex_id = s.get("example_id", "")
            assert src_case not in FROZEN_TEST_IDS, f"LEAKAGE ERROR: {src_case} found in dataset"
            assert ex_id not in FROZEN_TEST_IDS, f"LEAKAGE ERROR: {ex_id} matches frozen test ID"
            assert "heldout" not in ex_id, f"LEAKAGE ERROR: 'heldout' found in {ex_id}"

    def test_no_ground_truth_in_human_prompts(self, train_data, val_data):
        """Verify that human prompts do not contain ground-truth leakage."""
        forbidden_keywords = ["ground_truth_signal", "ground_truth_signals", "defect_mechanism"]
        for s in train_data + val_data:
            convs = s.get("conversations", [])
            assert len(convs) == 3, f"Invalid conversation structure in {s.get('example_id')}"
            human_text = convs[1]["value"].lower()
            for kw in forbidden_keywords:
                assert kw not in human_text, f"LEAKAGE: '{kw}' in human prompt for {s.get('example_id')}"

    def test_target_diagnosis_schema_and_validity(self, train_data, val_data):
        """Verify structured JSON target validity and field ranges."""
        for s in train_data + val_data:
            target_str = s["conversations"][2]["value"]
            target = json.loads(target_str)
            assert "candidate_signal" in target
            assert "suspected_root_cause" in target
            assert "causal_chain" in target
            assert isinstance(target["causal_chain"], list)
            assert len(target["causal_chain"]) >= 2
            assert 0.0 <= target["confidence"] <= 1.0

    def test_dataset_diversity_and_balance(self, quality_report):
        """Verify that multiple hardware families and hard negatives are well-represented."""
        families = quality_report["distribution_by_family"]
        types = quality_report["distribution_by_example_type"]
        
        # Verify 5 families represented
        for f in ["fifo", "axi", "fsm", "uart", "pipeline"]:
            assert f in families, f"Missing family '{f}'"
            assert families[f] >= 30, f"Family '{f}' count too low ({families[f]})"

        # Verify hard negatives and UNKNOWN cases exist
        assert types.get("HARD_NEGATIVE", 0) >= 30, "Insufficient hard negatives"
        assert types.get("UNKNOWN_INSUFFICIENT", 0) >= 10, "Insufficient UNKNOWN cases"
