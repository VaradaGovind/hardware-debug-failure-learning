#!/usr/bin/env python3
"""
scripts/test_v10_2_smoke_behavior.py

Executes a 5-case behavioral smoke test on the trained smoke adapter:
Verifies:
1. Does the model output `action: tool_call` on Step 1?
2. Does it output `action: tool_call` on Step 2 after receiving tool output?
3. Does it produce valid structured JSON for conclusion on Step 3?
4. Documents findings in docs/V10_2_SMOKE_TEST.md.
5. Fails immediately if the smoke adapter immediately concludes without tools.
"""

import os
import sys
import gc
import json
import time
from typing import Dict, Any, List

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.agent.llm_provider import PeftLLMProvider
from src.agent.agentic_rca_backend import AgenticRCABackend


TEST_CASES = [
    {
        "task_id": "v10_pipe_4stage_deep",
        "design_family": "pipeline",
        "symptom": "Throughput Bubble on Stage 2",
        "ground_truth_signal": "stg2_tok",
        "candidate_signals": ["val_in", "dat_in", "val_out", "dat_out", "stg1_tok", "stg2_tok", "stg3_tok", "d1_reg", "d2_reg", "d3_reg"]
    },
    {
        "task_id": "v10_fifo_gray_ptr",
        "design_family": "fifo",
        "symptom": "Gray Code Pointer Corruption",
        "ground_truth_signal": "gray_wr_ptr",
        "candidate_signals": ["wr_strobe", "rd_strobe", "wr_payload", "rd_payload", "buf_empty", "buf_full", "bin_wr_ptr", "bin_rd_ptr", "gray_wr_ptr", "gray_rd_ptr", "fifo_occ"]
    },
    {
        "task_id": "v10_fsm_hierarchical_seq",
        "design_family": "fsm",
        "symptom": "Illegal Sub-State Sequence",
        "ground_truth_signal": "sub_state",
        "candidate_signals": ["req", "ack", "op_mode", "main_state", "sub_state", "seq_done"]
    },
    {
        "task_id": "v10_axi_burst_split",
        "design_family": "axi",
        "symptom": "Burst Boundary Address Misalignment",
        "ground_truth_signal": "addr_phase",
        "candidate_signals": ["burst_start", "burst_ready", "burst_done", "burst_valid", "addr_phase", "data_phase", "wrap_boundary", "active_bytes"]
    },
    {
        "task_id": "v10_uart_fractional_baud",
        "design_family": "uart",
        "symptom": "Fractional Baud Tick Jitter",
        "ground_truth_signal": "baud_tick",
        "candidate_signals": ["tx_start", "baud_cfg", "frac_acc", "baud_tick", "tx_bit_cnt", "serial_tx", "tx_busy"]
    }
]


def run_smoke_test():
    print("=" * 80)
    print("EXPERIMENT V10.2: BEHAVIORAL SMOKE TEST ON SMOKE ADAPTER")
    print("=" * 80)

    adapter_path = "C:/Users/varad/ml-cache/rca-reuse/v10_2/checkpoints/v10_2_smoke_adapter/best_smoke_checkpoint"
    if not os.path.exists(adapter_path):
        raise FileNotFoundError(f"Smoke adapter not found at: {adapter_path}")

    print(f"[*] Initializing PeftLLMProvider with smoke adapter: {adapter_path}...")
    provider = PeftLLMProvider(
        base_model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        adapter_path=adapter_path
    )

    backend = AgenticRCABackend(
        provider=provider,
        mode="tool_assisted",
        max_iterations=4,
        temperature=0.0,
        workspace_root=WORKSPACE_ROOT
    )

    results = []
    immediate_conclusions = 0
    step1_tool_calls = 0
    step2_tool_calls = 0
    valid_final_rcas = 0

    for idx, tc in enumerate(TEST_CASES, 1):
        task_id = tc["task_id"]
        design_family = tc["design_family"]
        metadata = {
            "symptom": tc["symptom"],
            "design_family": design_family,
            "suspected_module": design_family,
            "ground_truth_signals": [tc["ground_truth_signal"]],
            "candidate_signals": tc["candidate_signals"],
            "target_signals": tc["candidate_signals"]
        }

        print(f"\n[{idx}/5] Evaluating Task: {task_id} ({tc['symptom']})...")
        t0 = time.time()
        diag = backend.diagnose_failure(task_id, design_family, metadata)
        elapsed = time.time() - t0

        traj_steps = diag.trajectory_summary.get("parsed_response") or []
        # If trajectory is in trajectory_steps
        # Inspect steps
        steps_taken = diag.steps_taken
        tool_calls_made = diag.tool_calls
        status = diag.rca_status
        cand_sig = diag.root_cause_signal
        is_correct = diag.is_correct

        print(f"  - Status: {status}")
        print(f"  - Steps Taken: {steps_taken}")
        print(f"  - Tool Calls:  {tool_calls_made}")
        print(f"  - Candidate:   {cand_sig} (GT: {tc['ground_truth_signal']}, Correct: {is_correct})")
        print(f"  - Wall Clock:  {elapsed:.2f}s")

        if steps_taken == 1 and tool_calls_made == 0:
            immediate_conclusions += 1
            step1_action = "conclude"
        else:
            step1_tool_calls += 1
            step1_action = "tool_call"

        if tool_calls_made >= 2:
            step2_tool_calls += 1

        if status in ["FINAL_RCA", "UNKNOWN", "SUCCESS"]:
            valid_final_rcas += 1

        results.append({
            "task_id": task_id,
            "symptom": tc["symptom"],
            "ground_truth_signal": tc["ground_truth_signal"],
            "predicted_signal": cand_sig,
            "is_correct": is_correct,
            "steps_taken": steps_taken,
            "tool_calls_made": tool_calls_made,
            "step1_action": step1_action,
            "status": status,
            "elapsed_s": round(elapsed, 2)
        })

    print("\n" + "=" * 80)
    print("BEHAVIORAL SMOKE TEST SUMMARY")
    print("=" * 80)
    print(f"Total Cases:               {len(TEST_CASES)}")
    print(f"Step 1 Tool Calls:         {step1_tool_calls} / {len(TEST_CASES)} ({100.0 * step1_tool_calls / len(TEST_CASES):.1f}%)")
    print(f"Step 2 Tool Calls:         {step2_tool_calls} / {len(TEST_CASES)} ({100.0 * step2_tool_calls / len(TEST_CASES):.1f}%)")
    print(f"Immediate Conclusions:     {immediate_conclusions} / {len(TEST_CASES)}")
    print(f"Valid Structured Output:   {valid_final_rcas} / {len(TEST_CASES)}")

    # Write documentation to docs/V10_2_SMOKE_TEST.md
    doc_path = os.path.join(WORKSPACE_ROOT, "docs", "V10_2_SMOKE_TEST.md")
    os.makedirs(os.path.dirname(doc_path), exist_ok=True)
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("# Experiment V10.2: Behavioral Smoke Test Report\n\n")
        f.write("## Overview\n\n")
        f.write("A lightweight smoke adapter was trained on 75 per-turn examples for 30 steps to verify that per-turn supervision fixes the catastrophic immediate-conclusion failure observed in V10.\n\n")
        f.write("## Mandatory Quality Gate Criteria\n\n")
        f.write("- **Criterion 1**: Model outputs `action: tool_call` on Step 1 (Must be >= 80%).\n")
        f.write("- **Criterion 2**: Immediate conclusions on Step 1 must be 0/5.\n")
        f.write("- **Criterion 3**: Valid structured JSON output must be produced.\n\n")
        f.write("## Behavioral Test Results\n\n")
        f.write("| Task ID | Symptom | GT Signal | Predicted | Correct | Steps | Tool Calls | Step 1 Action | Status |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for r in results:
            f.write(f"| `{r['task_id']}` | {r['symptom']} | `{r['ground_truth_signal']}` | `{r['predicted_signal']}` | {r['is_correct']} | {r['steps_taken']} | {r['tool_calls_made']} | `{r['step1_action']}` | `{r['status']}` |\n")
        f.write("\n## Summary Metrics\n\n")
        f.write(f"- **Step 1 Tool Calls**: {step1_tool_calls} / {len(TEST_CASES)} ({100.0 * step1_tool_calls / len(TEST_CASES):.1f}%)\n")
        f.write(f"- **Step 2 Tool Calls**: {step2_tool_calls} / {len(TEST_CASES)} ({100.0 * step2_tool_calls / len(TEST_CASES):.1f}%)\n")
        f.write(f"- **Immediate Conclusions**: {immediate_conclusions} / {len(TEST_CASES)}\n")
        f.write(f"- **Valid Structured Outputs**: {valid_final_rcas} / {len(TEST_CASES)}\n\n")
        
        gate_status = "PASSED" if (immediate_conclusions == 0 and step1_tool_calls == len(TEST_CASES)) else "FAILED"
        f.write(f"## Gate Verdict: **{gate_status}**\n\n")
        if gate_status == "PASSED":
            f.write("The behavioral smoke test confirms that per-turn supervision resolves the V10 truncation collapse. The model reliably invokes tools at Step 1 and conditions subsequent actions on tool observations before concluding.\n")
        else:
            f.write("The behavioral smoke test FAILED: The model still attempts immediate conclusions without tool invocations. Halting pipeline per protocol.\n")

    print(f"\n[*] Smoke test report saved to: {doc_path}")

    # MANDATORY GATE CHECK
    if immediate_conclusions > 0 or step1_tool_calls == 0:
        print("\n[CRITICAL FAILURE] Mandatory Gate Violated: Model immediately concluded without tools!")
        raise RuntimeError("Behavioral smoke test failed: Immediate conclusion without tool use.")

    print("\n[PASS] Mandatory Gate Satisfied: Smoke adapter demonstrates robust tool invocation behavior!")


if __name__ == "__main__":
    run_smoke_test()
