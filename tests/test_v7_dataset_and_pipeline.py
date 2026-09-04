import os
import json
import pytest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

FROZEN_TEST_IDS = {
    "heldout_fifo_src", "fifo_vl_a1", "fifo_vl_b1", "fifo_vl_f1", "fifo_vl_i2",
    "heldout_axi_src", "axi_vl_a1", "axi_vl_b1", "axi_vl_f1", "axi_vl_i2",
    "heldout_fsm_src", "fsm_vl_a1", "fsm_vl_b1", "fsm_vl_f1", "fsm_vl_i2",
    "heldout_uart_src", "uart_vl_a1", "uart_vl_b1", "uart_vl_f1", "uart_vl_i2",
    "heldout_pipe_src", "pipeline_vl_a1", "pipeline_vl_b1", "pipeline_vl_f1", "pipeline_vl_i2",
    "fifo_f5_inc", "axi_f5_inc", "fsm_f5_inc", "uart_f5_inc", "pipeline_f5_inc"
}

CACHE_DIR = os.environ.get("RCA_REUSE_CACHE_DIR", os.path.expanduser("~/.cache/rca-reuse"))
TRAIN_PATH = os.path.join(CACHE_DIR, "v7", "datasets", "rca_train_v7.json")
VAL_PATH = os.path.join(CACHE_DIR, "v7", "datasets", "rca_val_v7.json")
REPORT_PATH = os.path.join(CACHE_DIR, "v7", "reports", "V7_DATASET_QUALITY_REPORT.json")


def _check_v7_artifacts():
    if not os.path.exists(TRAIN_PATH):
        pytest.skip(f"V7 train dataset missing at {TRAIN_PATH}")


def test_v7_dataset_files_exist():
    _check_v7_artifacts()
    assert os.path.exists(TRAIN_PATH), f"Train dataset missing at {TRAIN_PATH}"
    assert os.path.exists(VAL_PATH), f"Validation dataset missing at {VAL_PATH}"
    assert os.path.exists(REPORT_PATH), f"Quality report missing at {REPORT_PATH}"


def test_v7_dataset_size_target():
    _check_v7_artifacts()
    with open(TRAIN_PATH, "r", encoding="utf-8") as f:
        train_data = json.load(f)
    with open(VAL_PATH, "r", encoding="utf-8") as f:
        val_data = json.load(f)
    
    total = len(train_data) + len(val_data)
    assert 800 <= total <= 1200, f"Total dataset size {total} not in [800, 1200]"
    assert len(train_data) >= 600
    assert len(val_data) >= 150


def test_zero_frozen_test_leakage():
    _check_v7_artifacts()
    with open(TRAIN_PATH, "r", encoding="utf-8") as f:
        train_data = json.load(f)
    with open(VAL_PATH, "r", encoding="utf-8") as f:
        val_data = json.load(f)

    for ex in train_data + val_data:
        sc = ex.get("source_case", "")
        eid = ex.get("example_id", "")
        assert sc not in FROZEN_TEST_IDS, f"Data leakage: frozen test ID {sc} in dataset"
        assert eid not in FROZEN_TEST_IDS, f"Data leakage: frozen test ID {eid} in dataset"
        for heldout_marker in ["heldout", "_vl_a1", "_vl_b1", "_vl_f1", "_vl_i2"]:
            assert heldout_marker not in sc, f"Data leakage: {heldout_marker} in source_case {sc}"


def test_zero_cross_split_module_leakage():
    _check_v7_artifacts()
    with open(TRAIN_PATH, "r", encoding="utf-8") as f:
        train_data = json.load(f)
    with open(VAL_PATH, "r", encoding="utf-8") as f:
        val_data = json.load(f)

    train_cases = set(e["source_case"] for e in train_data)
    val_cases = set(e["source_case"] for e in val_data)
    overlap = train_cases.intersection(val_cases)
    assert len(overlap) == 0, f"Cross-split leakage detected on {overlap}"


def test_unknown_calibration():
    _check_v7_artifacts()
    with open(TRAIN_PATH, "r", encoding="utf-8") as f:
        train_data = json.load(f)
    with open(VAL_PATH, "r", encoding="utf-8") as f:
        val_data = json.load(f)

    all_ex = train_data + val_data
    unk_count = sum(1 for e in all_ex if e.get("example_type") == "UNKNOWN_INSUFFICIENT" or e.get("root_cause_signal") == "unknown")
    unk_pct = (unk_count / len(all_ex)) * 100.0
    assert 10.0 <= unk_pct <= 15.0, f"UNKNOWN percentage {unk_pct:.2f}% not in [10%, 15%]"


def test_all_12_quality_gates():
    _check_v7_artifacts()
    with open(TRAIN_PATH, "r", encoding="utf-8") as f:
        train_data = json.load(f)
    with open(VAL_PATH, "r", encoding="utf-8") as f:
        val_data = json.load(f)

    all_ex = train_data + val_data
    for ex in all_ex:
        # Schema
        assert "example_id" in ex
        assert "source_dataset" in ex
        assert "source_case" in ex
        assert "license" in ex
        assert "provenance" in ex
        assert "design_family" in ex
        assert "conversations" in ex
        
        convs = ex["conversations"]
        assert len(convs) == 3
        assert convs[0]["from"] == "system"
        assert convs[1]["from"] == "human"
        assert convs[2]["from"] == "gpt"

        # Valid JSON in target
        target = json.loads(convs[2]["value"])
        assert "candidate_signal" in target
        assert "suspected_root_cause" in target
        assert "causal_chain" in target
        assert "confidence" in target
        assert 0.0 <= target["confidence"] <= 1.0

        if target["candidate_signal"] == "unknown":
            assert target["confidence"] <= 0.40
