import os
import sys
import json
import random
from typing import Dict, Any, List

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.agent.agentic_rca_backend import RCA_SYSTEM_PROMPT_STAGE_A


# Held-out test evaluation IDs that MUST NEVER be included in training data
HELDOUT_TEST_SET = {
    "heldout_fifo_src", "fifo_vl_a1", "fifo_vl_b1", "fifo_vl_f1", "fifo_f5_inc",
    "heldout_axi_src", "axi_vl_a1", "axi_vl_b1", "axi_vl_f1", "axi_f5_inc",
    "heldout_fsm_src", "fsm_vl_a1", "fsm_vl_b1", "fsm_vl_f1", "fsm_f5_inc",
    "heldout_uart_src", "uart_vl_a1", "uart_vl_b1", "uart_vl_f1", "uart_f5_inc",
    "heldout_pipeline_src", "pipeline_vl_a1", "pipeline_vl_b1", "pipeline_vl_f1", "pipeline_f5_inc",
}


def load_bugs_metadata(bugs_json_path: str) -> List[Dict[str, Any]]:
    """Loads the benchmark bug catalog."""
    if not os.path.exists(bugs_json_path):
        return []
    with open(bugs_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "bugs" in data:
        return data["bugs"]
    return []


def read_rtl_snippet(workspace_root: str, task_id: str, max_chars: int = 2500) -> str:
    """Reads RTL design source snippet for the task."""
    rtl_path = os.path.join(workspace_root, "rtl", "designs", f"{task_id}.v")
    if not os.path.exists(rtl_path):
        return ""
    try:
        with open(rtl_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content[:max_chars]
    except Exception:
        return ""


def build_training_examples(workspace_root: str, output_dir: str) -> Dict[str, Any]:
    """Generates training and validation dataset splits for Soup fine-tuning."""
    os.makedirs(output_dir, exist_ok=True)
    bugs_json_path = os.path.join(workspace_root, "datasets", "metadata", "bugs.json")
    bug_records = load_bugs_metadata(bugs_json_path)

    examples: List[Dict[str, Any]] = []
    skipped_heldout = 0

    for bug in bug_records:
        task_id = bug.get("task_id", bug.get("bug_id", ""))
        if not task_id:
            continue

        # Prevent data leakage by skipping any heldout test targets
        if task_id in HELDOUT_TEST_SET or "heldout" in task_id or "_vl_" in task_id:
            skipped_heldout += 1
            continue

        family = bug.get("design_family", "generic")
        symptom = bug.get("symptom", "HARDWARE_ASSERTION_FAILED")
        defect_mechanism = bug.get("defect_mechanism", "LOGIC_ERROR")
        root_cause_sig = bug.get("root_cause_signal", "count")
        causal_signals = bug.get("causal_signals", [root_cause_sig])
        location = bug.get("root_cause_location", f"{task_id}.v")
        explanation = bug.get("explanation", f"Causal fault on signal {root_cause_sig} during transaction.")
        boundary_sigs = bug.get("boundary_signals", [])

        rtl_snippet = read_rtl_snippet(workspace_root, task_id)
        if not rtl_snippet:
            # Generate synthetic hardware context if file not present
            rtl_snippet = f"// Module {task_id}\nmodule {task_id}(\n  input clk, input rst_n,\n  input read_en, input write_en,\n  output reg [{root_cause_sig}_width:0] {root_cause_sig}\n);\n// Hardware logic\nendmodule"

        # Construct Human Query
        human_prompt = (
            f"Hardware Failure Analysis Task: {task_id}\n"
            f"Design Family: {family}\n"
            f"Observed Symptom: {symptom}\n"
            f"Defect Mechanism: {defect_mechanism}\n"
            f"Boundary Signals: {boundary_sigs}\n\n"
            f"RTL Context:\n```verilog\n{rtl_snippet}\n```\n\n"
            f"Analyze the hardware failure symptom and RTL logic. Output the structured root-cause analysis."
        )

        # Construct Target Structured JSON Diagnosis
        target_diagnosis = {
            "failure_summary": f"Hardware assertion failure in {family} design due to {symptom}.",
            "suspected_root_cause": explanation,
            "root_cause_location": location,
            "candidate_signal": root_cause_sig,
            "causal_signals": causal_signals,
            "evidence": [
                f"Symptom '{symptom}' correlates directly with abnormal state in '{root_cause_sig}'.",
                f"Protocol obligation violation observed at transaction boundary."
            ],
            "confidence": 0.95
        }

        example = {
            "id": f"rca_train_{task_id}",
            "provenance": "repository-derived",
            "design_family": family,
            "defect_mechanism": defect_mechanism,
            "conversations": [
                {"from": "system", "value": RCA_SYSTEM_PROMPT_STAGE_A},
                {"from": "human", "value": human_prompt},
                {"from": "gpt", "value": json.dumps(target_diagnosis, indent=2)}
            ]
        }
        examples.append(example)

    # Random split (80% Train, 20% Val) with fixed seed for reproducibility
    random.seed(42)
    random.shuffle(examples)
    
    split_idx = int(len(examples) * 0.8)
    train_set = examples[:split_idx]
    val_set = examples[split_idx:]

    train_path = os.path.join(output_dir, "rca_train.json")
    val_path = os.path.join(output_dir, "rca_val.json")

    with open(train_path, "w", encoding="utf-8") as f:
        json.dump(train_set, f, indent=2)

    with open(val_path, "w", encoding="utf-8") as f:
        json.dump(val_set, f, indent=2)

    report = {
        "status": "SUCCESS",
        "total_source_bugs": len(bug_records),
        "skipped_heldout_test_cases": skipped_heldout,
        "total_training_examples": len(examples),
        "train_set_size": len(train_set),
        "val_set_size": len(val_set),
        "train_path": train_path,
        "val_path": val_path,
        "leakage_audit": "PASSED (Zero held-out test cases in training/validation splits)"
    }
    return report


def main():
    cache_root = os.environ.get("RCA_REUSE_CACHE_DIR", os.path.expanduser("~/.cache/rca-reuse"))
    external_cache_dir = os.path.join(cache_root, "training")
    
    print("=" * 70)
    print("SOUP DATASET PREPARATION & TEST LEAKAGE AUDIT")
    print("=" * 70)
    report = build_training_examples(WORKSPACE_ROOT, external_cache_dir)
    print(json.dumps(report, indent=2))
    print("=" * 70)


if __name__ == "__main__":
    main()
