import os
import sys
import json
import pytest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.agent.llm_provider import LLMProvider, MockLLMProvider
from src.agent.agentic_rca_backend import AgenticRCABackend


def test_schema_robustness_trailing_comma():
    raw_json_with_comma = """
    {
      "action": "conclude",
      "thought": "Analysis completed successfully.",
      "candidate_signal": "s1_valid",
      "confidence": 0.95,
    }
    """
    parsed = LLMProvider._extract_and_parse_json(raw_json_with_comma)
    assert parsed is not None
    assert parsed.get("action") == "conclude"
    assert parsed.get("candidate_signal") == "s1_valid"


def test_schema_robustness_markdown_block():
    raw_md = """
    Here is the diagnosis:
    ```json
    {
      "action": "tool_call",
      "thought": "Need to check waveform",
      "tool_name": "get_waveform_summary",
      "tool_args": {"signals": ["s1_valid", "s1_data"]}
    }
    ```
    """
    parsed = LLMProvider._extract_and_parse_json(raw_md)
    assert parsed is not None
    assert parsed.get("action") == "tool_call"
    assert parsed.get("tool_name") == "get_waveform_summary"


def test_schema_robustness_regex_fallback():
    raw_semi_broken = """
    The suspected signal is: "candidate_signal": "stg2_tok"
    Explanation: "thought": "Signal dropped during stall"
    """
    parsed = LLMProvider._extract_and_parse_json(raw_semi_broken)
    assert parsed is not None
    assert parsed.get("action") == "conclude"
    assert parsed.get("candidate_signal") == "stg2_tok"


def test_explicit_machine_states():
    # Mock unknown conclusion
    mock_unknown = MockLLMProvider(
        canned_responses={
            "[Step 1/4]": json.dumps({"action": "conclude", "candidate_signal": "unknown", "thought": "Insufficient evidence"}),
            "[Step 1/3]": json.dumps({"action": "conclude", "candidate_signal": "unknown", "thought": "Insufficient evidence"})
        },
        default_signal="unknown"
    )
    backend = AgenticRCABackend(provider=mock_unknown, mode="tool_assisted", workspace_root=WORKSPACE_ROOT)
    res = backend.diagnose_failure("v10_pipe_2stage_decoupled", "pipeline", {"candidate_signals": ["s1_valid", "s1_data"]})
    assert res.root_cause_signal == "unknown"
    assert res.trajectory_summary.get("machine_state") == "UNKNOWN"

    # Mock tool call then valid conclusion
    mock_success = MockLLMProvider(
        canned_responses={
            "[Step 1/4]": json.dumps({"action": "tool_call", "tool_name": "read_rtl_file", "tool_args": {"task_id": "v10_pipe_2stage_decoupled"}}),
            "[Step 2/4]": json.dumps({"action": "conclude", "candidate_signal": "s1_valid", "thought": "Root cause verified"})
        },
        default_signal="s1_valid"
    )
    backend_succ = AgenticRCABackend(provider=mock_success, mode="tool_assisted", workspace_root=WORKSPACE_ROOT)
    res_succ = backend_succ.diagnose_failure("v10_pipe_2stage_decoupled", "pipeline", {"candidate_signals": ["s1_valid", "s1_data"]})
    assert res_succ.root_cause_signal == "s1_valid"
    assert res_succ.trajectory_summary.get("machine_state") == "FINAL_RCA"


def test_v10_zero_leakage_assertion():
    v10_ds_dir = os.path.join(WORKSPACE_ROOT, "datasets", "v10")
    if not os.path.exists(os.path.join(v10_ds_dir, "agentic_train_v10.json")):
        pytest.skip("V10 dataset not yet generated")

    with open(os.path.join(v10_ds_dir, "agentic_train_v10.json"), "r", encoding="utf-8") as f:
        train = json.load(f)
    with open(os.path.join(v10_ds_dir, "agentic_val_v10.json"), "r", encoding="utf-8") as f:
        val = json.load(f)

    train_ids = set(t["task_id"] for t in train)
    val_ids = set(t["task_id"] for t in val)

    assert len(train_ids.intersection(val_ids)) == 0, "Train and Validation share task IDs!"
    
    frozen_ids = {"heldout_pipe_src", "heldout_fifo_src", "heldout_axi_src", "heldout_fsm_src", "heldout_uart_src"}
    assert len(train_ids.intersection(frozen_ids)) == 0, "Frozen benchmark found in training set!"
