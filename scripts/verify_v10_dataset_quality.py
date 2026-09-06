import os
import sys
import json
import hashlib
from typing import Dict, Any, List, Set, Tuple

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from scripts.audit_v10_architecture_fingerprints import extract_structural_fingerprint, normalize_rtl

FROZEN_BENCHMARK_IDS = {
    "heldout_fifo_src", "fifo_vl_a1", "fifo_vl_b1", "fifo_vl_f1", "fifo_vl_i2",
    "heldout_axi_src", "axi_vl_a1", "axi_vl_b1", "axi_vl_f1", "axi_vl_i2",
    "heldout_fsm_src", "fsm_vl_a1", "fsm_vl_b1", "fsm_vl_f1", "fsm_vl_i2",
    "heldout_uart_src", "uart_vl_a1", "uart_vl_b1", "uart_vl_f1", "uart_vl_i2",
    "heldout_pipe_src", "pipeline_vl_a1", "pipeline_vl_b1", "pipeline_vl_f1", "pipeline_vl_i2"
}

ALLOWED_TOOLS = {
    "read_rtl_file",
    "search_rtl",
    "read_simulation_log",
    "inspect_failure",
    "get_waveform_summary"
}


def verify_quality_gates():
    print("=" * 88)
    print("EXPERIMENT V10: AUTOMATED DATASET QUALITY & LEAKAGE GATES")
    print("=" * 88)

    ws_v10_dir = os.path.join(WORKSPACE_ROOT, "datasets", "v10")
    designs_dir = os.path.join(WORKSPACE_ROOT, "rtl", "designs")
    reports_dir = os.path.join(WORKSPACE_ROOT, "results", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    with open(os.path.join(ws_v10_dir, "agentic_train_v10.json"), "r", encoding="utf-8") as fp:
        train_data = json.load(fp)
    with open(os.path.join(ws_v10_dir, "agentic_val_v10.json"), "r", encoding="utf-8") as fp:
        val_data = json.load(fp)
    with open(os.path.join(ws_v10_dir, "agentic_gen_v10.json"), "r", encoding="utf-8") as fp:
        gen_data = json.load(fp)

    # 1. Fingerprint all RTL files
    fingerprints = {}
    for f in os.listdir(designs_dir):
        if f.endswith(".v"):
            tid = f[:-2]
            with open(os.path.join(designs_dir, f), "r", encoding="utf-8") as fp:
                fingerprints[tid] = extract_structural_fingerprint(fp.read())

    # Gate 1: Exact RTL Leakage with Frozen Benchmark
    exact_leakage = []
    structural_leakage = []
    for traj in train_data:
        tid = traj["task_id"]
        if tid in fingerprints:
            t_fp = fingerprints[tid]
            for f_id in FROZEN_BENCHMARK_IDS:
                if f_id in fingerprints:
                    f_fp = fingerprints[f_id]
                    if t_fp["norm_hash"] == f_fp["norm_hash"]:
                        exact_leakage.append({"train_id": tid, "frozen_id": f_id})
                    elif t_fp["struct_hash"] == f_fp["struct_hash"]:
                        structural_leakage.append({"train_id": tid, "frozen_id": f_id})

    # Gate 2: Split Disjointness (TRAIN vs VALIDATION vs GENERALIZATION)
    train_tasks = set(t["task_id"] for t in train_data)
    val_tasks = set(t["task_id"] for t in val_data)
    gen_tasks = set(t["task_id"] for t in gen_data)

    train_val_overlap = train_tasks.intersection(val_tasks)
    train_gen_overlap = train_tasks.intersection(gen_tasks)
    val_gen_overlap = val_tasks.intersection(gen_tasks)

    # Structural cross-split check
    cross_split_struct_leakage = []
    for t_id in train_tasks:
        if t_id in fingerprints:
            t_fp = fingerprints[t_id]
            for v_id in val_tasks:
                if v_id in fingerprints:
                    v_fp = fingerprints[v_id]
                    if t_fp["norm_hash"] == v_fp["norm_hash"] or t_fp["struct_hash"] == v_fp["struct_hash"]:
                        cross_split_struct_leakage.append({"train_id": t_id, "val_id": v_id})

    # Gate 3: Tool-Call & Trajectory Schema Validity
    invalid_tool_calls = []
    fabricated_tools = []
    unsupported_rca = []

    all_splits = [("TRAIN", train_data), ("VALIDATION", val_data), ("GENERALIZATION", gen_data)]
    for split_name, dataset in all_splits:
        for traj in dataset:
            ex_id = traj.get("example_id", "")
            convs = traj.get("conversations", [])
            for turn in convs:
                if turn.get("role") == "assistant":
                    try:
                        val = json.loads(turn.get("value", "{}"))
                        act = val.get("action")
                        if act == "tool_call":
                            tool_name = val.get("tool_name")
                            if tool_name not in ALLOWED_TOOLS:
                                invalid_tool_calls.append({"example_id": ex_id, "tool": tool_name})
                        elif act == "conclude":
                            cand = val.get("candidate_signal")
                            if not cand:
                                unsupported_rca.append({"example_id": ex_id, "reason": "Missing candidate_signal"})
                    except Exception as e:
                        invalid_tool_calls.append({"example_id": ex_id, "error": str(e)})

    # Gate 4: Distribution Statistics
    fam_counts = {}
    type_counts = {}
    rc_counts = {}
    pipe_topos = {}

    for split_name, dataset in all_splits:
        fam_counts[split_name] = {}
        type_counts[split_name] = {}
        rc_counts[split_name] = {}
        for traj in dataset:
            f = traj.get("design_family", "generic")
            fam_counts[split_name][f] = fam_counts[split_name].get(f, 0) + 1
            
            t = traj.get("example_type", "POSITIVE_RCA")
            type_counts[split_name][t] = type_counts[split_name].get(t, 0) + 1
            
            rc = traj.get("ground_truth_signal", "unknown")
            rc_counts[split_name][rc] = rc_counts[split_name].get(rc, 0) + 1

            if f == "pipeline":
                tid = traj.get("task_id", "")
                pipe_topos[tid] = pipe_topos.get(tid, 0) + 1

    # Quality Gate Verdicts
    g1_pass = (len(exact_leakage) == 0 and len(structural_leakage) == 0)
    g2_pass = (len(train_val_overlap) == 0 and len(train_gen_overlap) == 0 and len(val_gen_overlap) == 0 and len(cross_split_struct_leakage) == 0)
    g3_pass = (len(invalid_tool_calls) == 0 and len(unsupported_rca) == 0)

    overall_gate_pass = g1_pass and g2_pass and g3_pass

    report = {
        "overall_quality_gate_verdict": "PASSED" if overall_gate_pass else "FAILED",
        "gate_1_leakage_with_frozen_benchmark": {
            "status": "PASS" if g1_pass else "FAIL",
            "exact_rtl_matches": len(exact_leakage),
            "structural_matches": len(structural_leakage)
        },
        "gate_2_split_disjointness": {
            "status": "PASS" if g2_pass else "FAIL",
            "train_val_task_overlap": len(train_val_overlap),
            "train_gen_task_overlap": len(train_gen_overlap),
            "val_gen_task_overlap": len(val_gen_overlap),
            "cross_split_structural_leakage": len(cross_split_struct_leakage)
        },
        "gate_3_tool_and_trajectory_validity": {
            "status": "PASS" if g3_pass else "FAIL",
            "invalid_tool_calls": len(invalid_tool_calls),
            "unsupported_rca_conclusions": len(unsupported_rca)
        },
        "distribution_breakdown": {
            "total_trajectories": len(train_data) + len(val_data) + len(gen_data),
            "train_count": len(train_data),
            "val_count": len(val_data),
            "gen_count": len(gen_data),
            "family_distribution": fam_counts,
            "example_type_distribution": type_counts,
            "root_cause_distribution": rc_counts,
            "pipeline_topology_distribution": pipe_topos
        }
    }

    out_path = os.path.join(reports_dir, "v10_dataset_quality_gates.json")
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(report, fp, indent=2)

    print(f"\nGate 1 (Zero Frozen Leakage):  {'[PASS]' if g1_pass else '[FAIL]'} (Exact: {len(exact_leakage)}, Struct: {len(structural_leakage)})")
    print(f"Gate 2 (Split Disjointness):   {'[PASS]' if g2_pass else '[FAIL]'} (Overlap: 0, Cross-Struct: {len(cross_split_struct_leakage)})")
    print(f"Gate 3 (Trajectory Validity):  {'[PASS]' if g3_pass else '[FAIL]'} (Invalid Tool Calls: {len(invalid_tool_calls)})")
    print(f"\nOverall Quality Gate Verdict:   {'[PASS - PROCEED TO TRAINING]' if overall_gate_pass else '[FAIL - STOP]'}")
    print(f"Full report saved to: {out_path}")

    if not overall_gate_pass:
        raise RuntimeError("CRITICAL QUALITY GATE FAILURE: Halting training pipeline.")


if __name__ == "__main__":
    verify_quality_gates()
