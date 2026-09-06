import os
import sys
import json
import time
from typing import Dict, Any, List

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.agent.llm_provider import PeftLLMProvider
from src.agent.agentic_rca_backend import AgenticRCABackend, RCA_SYSTEM_PROMPT_STAGE_B
from src.agent.context_builder import build_rca_context, format_rca_context_prompt
from experiments.run_rca_vs_reuse_controlled_comparison import get_controlled_comparison_stream

REPRESENTATIVE_CASES = [
    # 1-5: Frozen Benchmark Source Cases
    {"task_id": "heldout_fifo_src", "family": "fifo", "defect": "FIFO_SIMULTANEOUS_RW", "gt": "count", "type": "SOURCE", "signals": ["clk", "rst_n", "write_en", "read_en", "count", "write_ptr", "read_ptr"]},
    {"task_id": "heldout_axi_src", "family": "axi", "defect": "AXI_HANDSHAKE_DROP", "gt": "wvalid", "type": "SOURCE", "signals": ["aclk", "aresetn", "wvalid", "wready", "wdata", "bvalid", "bready"]},
    {"task_id": "heldout_fsm_src", "family": "fsm", "defect": "FSM_DEADLOCK", "gt": "state", "type": "SOURCE", "signals": ["clk", "rst_n", "start", "state", "next_state", "done", "out_pulse"]},
    {"task_id": "heldout_uart_src", "family": "uart", "defect": "UART_BAUD_DRIFT", "gt": "baud_cnt", "type": "SOURCE", "signals": ["clk", "rst_n", "tx_start", "baud_cnt", "bit_idx", "tx_out", "busy"]},
    {"task_id": "heldout_pipe_src", "family": "pipeline", "defect": "PIPE_STALL_DROP", "gt": "v1", "type": "SOURCE", "signals": ["clk", "rst_n", "in_val", "in_dat", "v1", "d1", "v2", "d2", "out_val", "out_dat"]},

    # 6-10: Frozen Benchmark Target Cases (Reuses / Negatives)
    {"task_id": "fifo_vl_a1", "family": "fifo", "defect": "FIFO_SIMULTANEOUS_RW", "gt": "count", "type": "TARGET_REUSE", "signals": ["clk", "rst_n", "write_en", "read_en", "count", "write_ptr", "read_ptr"]},
    {"task_id": "axi_vl_a1", "family": "axi", "defect": "AXI_HANDSHAKE_DROP", "gt": "wvalid", "type": "TARGET_REUSE", "signals": ["aclk", "aresetn", "wvalid", "wready", "wdata", "bvalid", "bready"]},
    {"task_id": "pipeline_vl_a1", "family": "pipeline", "defect": "PIPE_STALL_DROP", "gt": "v1", "type": "TARGET_REUSE", "signals": ["clk", "rst_n", "in_val", "in_dat", "v1", "d1", "v2", "d2", "out_val", "out_dat"]},
    {"task_id": "fifo_vl_f1", "family": "fifo", "defect": "FIFO_UNDERFLOW", "gt": "read_ptr", "type": "TARGET_NEGATIVE", "signals": ["clk", "rst_n", "write_en", "read_en", "count", "write_ptr", "read_ptr"]},
    {"task_id": "pipeline_vl_f1", "family": "pipeline", "defect": "PIPE_FORWARD_HAZARD", "gt": "d1", "type": "TARGET_NEGATIVE", "signals": ["clk", "rst_n", "in_val", "in_dat", "v1", "d1", "v2", "d2", "out_val", "out_dat"]},

    # 11-15: V10 Architecture-Disjoint Validation Cases
    {"task_id": "v10_val_pipe_3stage_split", "family": "pipeline", "defect": "PIPE_STALL_BUBBLE", "gt": "p1_val", "type": "VAL_POSITIVE", "signals": ["clk", "rst_n", "p_in_val", "p_in_dat", "p1_val", "p1_dat", "p2_val", "p2_dat", "p_out_val"]},
    {"task_id": "v10_val_fifo_ring_buf", "family": "fifo", "defect": "FIFO_RING_ITEMS", "gt": "items_avail", "type": "VAL_POSITIVE", "signals": ["clk", "rst_n", "push_cmd", "pop_cmd", "data_in", "head_idx", "tail_idx", "items_avail", "data_out"]},
    {"task_id": "v10_val_axi_stream_fifo", "family": "axi", "defect": "AXI_STREAM_STABILITY", "gt": "strm_val", "type": "VAL_POSITIVE", "signals": ["clk", "rst_n", "strm_val_in", "strm_rdy_out", "strm_val", "strm_rdy", "occupancy_tok", "strm_val_out"]},
    {"task_id": "v10_pipe_3stage_hazard", "family": "pipeline", "defect": "PIPE_FORWARD_HAZARD", "gt": "fwd_data", "type": "TRAIN_HARD_NEG", "signals": ["clk", "rst_n", "in_valid", "in_payload", "stage1_vld", "stage2_vld", "fwd_data", "op_reg", "out_valid", "out_payload"]},
    {"task_id": "v10_fifo_gray_ptr", "family": "fifo", "defect": "FIFO_GRAY_SYNC", "gt": "gray_wr_ptr", "type": "TRAIN_HARD_NEG", "signals": ["clk", "rst_n", "wr_strobe", "rd_strobe", "wr_payload", "gray_wr_ptr", "gray_rd_ptr", "bin_wr_ptr", "bin_rd_ptr", "fifo_occ", "buf_full"]},

    # 16-20: UNKNOWN & Generalization Cases
    {"task_id": "v10_val_fifo_ring_buf", "family": "fifo", "defect": "TRUNCATED_SIMULATION_ABORT", "gt": "unknown", "type": "VAL_UNKNOWN", "signals": ["clk", "rst_n", "push_cmd", "pop_cmd", "data_in", "head_idx", "tail_idx", "items_avail"]},
    {"task_id": "v10_val_pipe_3stage_split", "family": "pipeline", "defect": "TRUNCATED_SIMULATION_ABORT", "gt": "unknown", "type": "VAL_UNKNOWN", "signals": ["clk", "rst_n", "p_in_val", "p_in_dat", "p1_val", "p1_dat", "p_out_val"]},
    {"task_id": "v10_gen_pipe_5stage_branch", "family": "pipeline", "defect": "PIPE_BRANCH_FLUSH_LEAK", "gt": "ex_v", "type": "GEN_TOPOLOGY", "signals": ["clk", "rst_n", "fetch_req", "fetch_v", "dec_v", "ex_v", "mem_v", "wb_v", "branch_flush", "retire_v"]},
    {"task_id": "v10_gen_pipe_elastic_ring", "family": "pipeline", "defect": "PIPE_RING_TOKEN_COLLAPSE", "gt": "token_ring", "type": "GEN_TOPOLOGY", "signals": ["clk", "rst_n", "ring_inject", "token_ring", "packet_id", "route_valid", "ring_eject"]},
    {"task_id": "gen_pipe_4stage_hazard", "family": "pipeline", "defect": "PIPE_RAW_HAZARD", "gt": "fwd_data", "type": "GEN_PIPELINE_SUITE", "signals": ["clk", "rst_n", "in_valid", "in_data", "s1_valid", "s1_data", "fwd_data", "out_valid"]}
]


def run_behavioral_comparison():
    print("=" * 96)
    print("V10.1 FORENSICS: SAME-INPUT BEHAVIORAL COMPARISON (V8 vs Model A vs Model B)")
    print("=" * 96)

    ckpts = {
        "V8": "C:/Users/varad/ml-cache/rca-reuse/v7/checkpoints/soup_v7_qwen_lora/best_v7_checkpoint",
        "Model_A": "C:/Users/varad/ml-cache/rca-reuse/v10/checkpoints/v10_model_a_generic_lora/best_v10_checkpoint",
        "Model_B": "C:/Users/varad/ml-cache/rca-reuse/v10/checkpoints/v10_model_b_topological_lora/best_v10_checkpoint"
    }

    raw_model_runs = {"V8": {}, "Model_A": {}, "Model_B": {}}

    stage_failure_counts = {
        "V8": {"initial_interpretation": 0, "tool_selection": 0, "tool_arg_gen": 0, "tool_result_interpretation": 0, "temporal_reasoning": 0, "candidate_discrimination": 0, "final_rca": 0, "formatting": 0, "success": 0},
        "Model_A": {"initial_interpretation": 0, "tool_selection": 0, "tool_arg_gen": 0, "tool_result_interpretation": 0, "temporal_reasoning": 0, "candidate_discrimination": 0, "final_rca": 0, "formatting": 0, "success": 0},
        "Model_B": {"initial_interpretation": 0, "tool_selection": 0, "tool_arg_gen": 0, "tool_result_interpretation": 0, "temporal_reasoning": 0, "candidate_discrimination": 0, "final_rca": 0, "formatting": 0, "success": 0}
    }

    schema_stats = {
        "V8": {"total": 0, "valid_json": 0, "tool_call": 0, "conclude": 0, "invalid_output": 0, "premature_conclude": 0, "hallucinated_candidate": 0},
        "Model_A": {"total": 0, "valid_json": 0, "tool_call": 0, "conclude": 0, "invalid_output": 0, "premature_conclude": 0, "hallucinated_candidate": 0},
        "Model_B": {"total": 0, "valid_json": 0, "tool_call": 0, "conclude": 0, "invalid_output": 0, "premature_conclude": 0, "hallucinated_candidate": 0}
    }

    for model_name, path in ckpts.items():
        print(f"\n==================================================")
        print(f"Running Evaluation for {model_name} ({path})...")
        print(f"==================================================")
        
        provider = PeftLLMProvider(
            base_model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
            adapter_path=path
        )
        backend = AgenticRCABackend(
            provider=provider,
            mode="tool_assisted",
            max_iterations=4,
            max_tokens=192,
            temperature=0.1,
            workspace_root=WORKSPACE_ROOT
        )

        for idx, case in enumerate(REPRESENTATIVE_CASES):
            t_id = case["task_id"]
            fam = case["family"]
            gt = case["gt"]
            signals = case["signals"]

            meta = {
                "symptom": f"ASSERTION_FAILED on {t_id}",
                "design_family": fam,
                "ground_truth_signals": [gt],
                "candidate_signals": signals,
                "target_signals": signals
            }

            diag = backend.diagnose_failure(t_id, fam, meta)
            traj = diag.trajectory_summary
            steps = traj.get("trajectory_steps", [])
            pred = diag.root_cause_signal
            is_corr = (pred.lower() == gt.lower())

            first_action = steps[0].get("action") if steps else "none"
            first_tool = steps[0].get("tool_name", "") if steps and first_action == "tool_call" else ""

            schema_stats[model_name]["total"] += 1
            if diag.rca_status != "INVALID_OUTPUT":
                schema_stats[model_name]["valid_json"] += 1
            else:
                schema_stats[model_name]["invalid_output"] += 1

            if first_action == "tool_call":
                schema_stats[model_name]["tool_call"] += 1
            elif first_action == "conclude":
                schema_stats[model_name]["conclude"] += 1
                schema_stats[model_name]["premature_conclude"] += 1

            if pred != "unknown" and pred not in signals and pred != gt:
                schema_stats[model_name]["hallucinated_candidate"] += 1

            fail_stage = "none"
            if is_corr:
                stage_failure_counts[model_name]["success"] += 1
            else:
                if diag.rca_status == "INVALID_OUTPUT":
                    fail_stage = "formatting"
                elif first_action == "conclude" and len(steps) == 1:
                    fail_stage = "tool_selection"
                elif first_action == "tool_call" and steps[0].get("tool_status") != "OK":
                    fail_stage = "tool_arg_gen"
                elif pred == "unknown" and gt != "unknown":
                    fail_stage = "candidate_discrimination"
                elif pred != gt:
                    fail_stage = "temporal_reasoning"
                stage_failure_counts[model_name][fail_stage] += 1

            raw_model_runs[model_name][t_id] = {
                "prediction": pred,
                "is_correct": is_corr,
                "status": diag.rca_status,
                "steps_taken": diag.steps_taken,
                "first_action": first_action,
                "first_tool": first_tool,
                "failure_stage": fail_stage,
                "trajectory": steps,
                "notes": diag.notes
            }
            print(f"  [{idx+1}/20] {t_id} | Pred: '{pred}' | Correct: {is_corr} | Steps: {diag.steps_taken} | 1st Act: {first_action} | Fail: {fail_stage}")

        # Unload model from GPU
        del backend
        del provider
        import gc
        gc.collect()

    # Reassemble results per case
    results = []
    for idx, case in enumerate(REPRESENTATIVE_CASES):
        t_id = case["task_id"]
        results.append({
            "case_id": t_id,
            "family": case["family"],
            "type": case["type"],
            "ground_truth": case["gt"],
            "candidate_signals": case["signals"],
            "model_runs": {
                "V8": raw_model_runs["V8"][t_id],
                "Model_A": raw_model_runs["Model_A"][t_id],
                "Model_B": raw_model_runs["Model_B"][t_id]
            }
        })

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_cases_evaluated": len(REPRESENTATIVE_CASES),
        "stage_failure_counts": stage_failure_counts,
        "schema_statistics": schema_stats,
        "cases": results
    }

    out_p = os.path.join(WORKSPACE_ROOT, "results", "reports", "v10_1_behavioral_comparison.json")
    os.makedirs(os.path.dirname(out_p), exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 96)
    print(f"V10.1 BEHAVIORAL COMPARISON COMPLETE. Saved to: {out_p}")
    print("=" * 96)
    print("\nStage Failure Breakdown:")
    for m, stats in stage_failure_counts.items():
        print(f"  [{m}]: Success: {stats['success']}/20 | Tool Selection Fail: {stats['tool_selection']} | Formatting: {stats['formatting']} | Temporal/Discrim: {stats['temporal_reasoning'] + stats['candidate_discrimination']}")
    print("\nAction Distribution (Step 1):")
    for m, s in schema_stats.items():
        print(f"  [{m}]: Called Tools at Step 1: {s['tool_call']} | Concluded Immediately at Step 1: {s['conclude']} | Hallucinated Sigs: {s['hallucinated_candidate']}")


if __name__ == "__main__":
    run_behavioral_comparison()
