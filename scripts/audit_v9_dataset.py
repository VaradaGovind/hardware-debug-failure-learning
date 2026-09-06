import os
import sys
import json
from typing import Dict, Any, List

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.tools.agent_tools import AgentToolRegistry

FROZEN_TEST_IDS = {
    "heldout_fifo_src", "fifo_vl_a1", "fifo_vl_b1", "fifo_vl_f1", "fifo_vl_i2",
    "heldout_axi_src", "axi_vl_a1", "axi_vl_b1", "axi_vl_f1", "axi_vl_i2",
    "heldout_fsm_src", "fsm_vl_a1", "fsm_vl_b1", "fsm_vl_f1", "fsm_vl_i2",
    "heldout_uart_src", "uart_vl_a1", "uart_vl_b1", "uart_vl_f1", "uart_vl_i2",
    "heldout_pipe_src", "pipeline_vl_a1", "pipeline_vl_b1", "pipeline_vl_f1", "pipeline_vl_i2",
    "fifo_f5_inc", "axi_f5_inc", "fsm_f5_inc", "uart_f5_inc", "pipeline_f5_inc"
}

ALLOWED_TOOLS = set(AgentToolRegistry.ALLOWED_TOOLS)


def audit_dataset_file(file_path: str) -> Dict[str, Any]:
    """Audits an agentic trajectory dataset file across all 5 quality gates."""
    print(f"Auditing Dataset: {file_path}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        trajectories = json.load(f)

    report = {
        "total_trajectories": len(trajectories),
        "gate1_structural_passed": 0,
        "gate2_evidence_passed": 0,
        "gate3_causality_passed": 0,
        "gate4_safety_passed": 0,
        "gate5_leakage_passed": 0,
        "violations": []
    }

    for idx, traj in enumerate(trajectories):
        t_id = traj.get("task_id", "")
        ex_id = traj.get("example_id", f"item_{idx}")
        convs = traj.get("conversations", [])

        # GATE 5: ZERO LEAKAGE
        is_leak = False
        for f_id in FROZEN_TEST_IDS:
            if t_id == f_id:
                report["violations"].append(f"[LEAKAGE] {ex_id}: Exact match with frozen test {f_id}")
                is_leak = True
                break
        if not is_leak:
            report["gate5_leakage_passed"] += 1

        # GATE 1: STRUCTURAL INTEGRITY
        struct_ok = True
        if len(convs) < 3:
            report["violations"].append(f"[STRUCTURAL] {ex_id}: Too few conversation turns ({len(convs)})")
            struct_ok = False
        
        # Check system turn
        if convs[0].get("role") != "system" or not convs[0].get("value"):
            report["violations"].append(f"[STRUCTURAL] {ex_id}: Invalid system turn")
            struct_ok = False

        # Check last assistant turn (Conclusion)
        last_turn = convs[-1]
        if last_turn.get("role") != "assistant":
            report["violations"].append(f"[STRUCTURAL] {ex_id}: Last turn is not assistant")
            struct_ok = False
        else:
            try:
                conclude_data = json.loads(last_turn.get("value", "{}"))
                if conclude_data.get("action") != "conclude":
                    report["violations"].append(f"[STRUCTURAL] {ex_id}: Last action is not 'conclude'")
                    struct_ok = False
                if not conclude_data.get("candidate_signal"):
                    report["violations"].append(f"[STRUCTURAL] {ex_id}: Missing candidate_signal")
                    struct_ok = False
                if not conclude_data.get("thought"):
                    report["violations"].append(f"[STRUCTURAL] {ex_id}: Missing conclusion thought")
                    struct_ok = False
            except Exception as e:
                report["violations"].append(f"[STRUCTURAL] {ex_id}: JSON parse failure in last turn: {str(e)}")
                struct_ok = False

        if struct_ok:
            report["gate1_structural_passed"] += 1

        # GATE 4: SAFETY (Sandboxed tools only, no arbitrary command injection)
        safety_ok = True
        for turn in convs:
            if turn.get("role") == "assistant":
                try:
                    c_data = json.loads(turn.get("value", "{}"))
                    if c_data.get("action") == "tool_call":
                        t_name = c_data.get("tool_name", "")
                        if t_name not in ALLOWED_TOOLS:
                            report["violations"].append(f"[SAFETY] {ex_id}: Unsanctioned tool '{t_name}'")
                            safety_ok = False
                        t_args = c_data.get("tool_args", {})
                        for arg_v in t_args.values():
                            if isinstance(arg_v, str) and (".." in arg_v or "/" in arg_v or "\\" in arg_v):
                                report["violations"].append(f"[SAFETY] {ex_id}: Potential path traversal in args '{arg_v}'")
                                safety_ok = False
                except Exception:
                    pass
        if safety_ok:
            report["gate4_safety_passed"] += 1

        # GATE 2: EVIDENCE GROUNDING
        evidence_ok = True
        found_tool_output = False
        for turn in convs:
            if turn.get("role") == "user" and "[Tool Output]:" in turn.get("value", ""):
                found_tool_output = True
                break
        if not found_tool_output and traj.get("example_type") != "UNKNOWN_INSUFFICIENT":
            report["violations"].append(f"[EVIDENCE] {ex_id}: Missing grounded [Tool Output] block in user turns")
            evidence_ok = False
        if evidence_ok:
            report["gate2_evidence_passed"] += 1

        # GATE 3: CAUSALITY & TEMPORAL DISCRIMINATION
        causality_ok = True
        if struct_ok and traj.get("example_type") != "UNKNOWN_INSUFFICIENT":
            try:
                conclude_data = json.loads(last_turn.get("value", "{}"))
                thought_text = conclude_data.get("thought", "")
                if "T=" not in thought_text and "divergence" not in thought_text.lower() and "earliest" not in thought_text.lower():
                    report["violations"].append(f"[CAUSALITY] {ex_id}: Conclusion thought lacks temporal divergence markers")
                    causality_ok = False
            except Exception:
                causality_ok = False
        if causality_ok:
            report["gate3_causality_passed"] += 1

    print("-" * 72)
    print(f"Total Trajectories Audited:    {report['total_trajectories']}")
    print(f"  Gate 1 (Structural) Passed:  {report['gate1_structural_passed']} / {report['total_trajectories']}")
    print(f"  Gate 2 (Evidence) Passed:    {report['gate2_evidence_passed']} / {report['total_trajectories']}")
    print(f"  Gate 3 (Causality) Passed:   {report['gate3_causality_passed']} / {report['total_trajectories']}")
    print(f"  Gate 4 (Safety) Passed:      {report['gate4_safety_passed']} / {report['total_trajectories']}")
    print(f"  Gate 5 (Zero Leakage) Passed:{report['gate5_leakage_passed']} / {report['total_trajectories']}")
    print(f"  Total Violations Detected:   {len(report['violations'])}")
    print("-" * 72)

    if report["violations"]:
        print("First 5 Violations:")
        for v in report["violations"][:5]:
            print(f"  ! {v}")
        raise RuntimeError(f"Audit failed with {len(report['violations'])} violations.")

    print("ALL 5 QUALITY GATES PASSED WITH ZERO VIOLATIONS.\n")
    return report


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ws_train = os.path.join(base, "datasets", "v9", "agentic_train_v9.json")
    ws_val = os.path.join(base, "datasets", "v9", "agentic_val_v9.json")
    audit_dataset_file(ws_train)
    audit_dataset_file(ws_val)
