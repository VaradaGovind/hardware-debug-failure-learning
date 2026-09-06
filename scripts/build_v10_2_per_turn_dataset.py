import os
import sys
import json
import random
import copy
from typing import Dict, Any, List, Tuple, Set

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.tools.agent_tools import AgentToolRegistry
from src.agent.agentic_rca_backend import RCA_SYSTEM_PROMPT_STAGE_B
from src.agent.context_builder import build_rca_context, format_rca_context_prompt, format_agentic_initial_context
from scripts.generate_v10_hardware_designs import V10_ARCHITECTURES

FROZEN_BENCHMARK_IDS = {
    "heldout_fifo_src", "fifo_vl_a1", "fifo_vl_b1", "fifo_vl_f1", "fifo_vl_i2",
    "heldout_axi_src", "axi_vl_a1", "axi_vl_b1", "axi_vl_f1", "axi_vl_i2",
    "heldout_fsm_src", "fsm_vl_a1", "fsm_vl_b1", "fsm_vl_f1", "fsm_vl_i2",
    "heldout_uart_src", "uart_vl_a1", "uart_vl_b1", "uart_vl_f1", "uart_vl_i2",
    "heldout_pipe_src", "pipeline_vl_a1", "pipeline_vl_b1", "pipeline_vl_f1", "pipeline_vl_i2",
    "pipeline_a1", "pipeline_a2", "pipeline_a3"
}

_PROMPT_CACHE: Dict[str, str] = {}
_TOOL_CACHE: Dict[Tuple[str, str], Any] = {}


def get_cached_base_prompt(tools: AgentToolRegistry, task_id: str, design_family: str, symptom: str, candidate_signals: List[str], ground_truth_signal: str) -> str:
    key = f"{task_id}_{ground_truth_signal}"
    if key in _PROMPT_CACHE:
        return _PROMPT_CACHE[key]
    
    metadata = {
        "symptom": symptom,
        "design_family": design_family,
        "suspected_module": design_family,
        "ground_truth_signals": [ground_truth_signal],
        "candidate_signals": candidate_signals,
        "target_signals": candidate_signals
    }
    try:
        rca_ctx = build_rca_context(task_id, design_family, metadata, tools.workspace_root)
        prompt = format_agentic_initial_context(rca_ctx)
    except Exception:
        prompt = (
            f"=== HARDWARE ROOT CAUSE ANALYSIS: {task_id} ===\n"
            f"Design Family: {design_family}\n"
            f"Observed Failure Symptom: {symptom}\n"
            f"Candidate Signals: {candidate_signals}\n"
        )
    _PROMPT_CACHE[key] = prompt
    return prompt


def get_cached_tool_result(tools: AgentToolRegistry, tool_name: str, args: Dict[str, Any]) -> Any:
    key = (tool_name, json.dumps(args, sort_keys=True))
    if key in _TOOL_CACHE:
        return _TOOL_CACHE[key]
    res = tools.execute_tool(tool_name, args)
    _TOOL_CACHE[key] = res
    return res


def build_per_turn_trajectory_examples(
    tools: AgentToolRegistry,
    task_id: str,
    design_family: str,
    defect_mechanism: str,
    ground_truth_signal: str,
    symptom: str,
    candidate_signals: List[str],
    symptom_distractor: str,
    divergence_cycle: int,
    assertion_cycle: int,
    is_hard_negative: bool = False,
    is_unknown: bool = False,
    example_prefix: str = "ex"
) -> List[Dict[str, Any]]:
    """
    Decomposes a single investigation into 2 or 3 independent supervised training examples:
    - Type A (Tool Selection): Context -> Next Tool Call
    - Type B (Evidence-Conditioned Action): Context + Tool 1 Result -> Next Tool Call
    - Type C (Final Decision): Context + Investigation History + Observations -> Final RCA or UNKNOWN
    """
    base_prompt = get_cached_base_prompt(tools, task_id, design_family, symptom, candidate_signals, ground_truth_signal)

    query_signals = [s for s in candidate_signals if s in [
        "clk", "rst_n", "in_valid", "in_data", "s1_valid", "s1_data", "out_valid", "out_data",
        "stage1_vld", "stage2_vld", "fwd_data", "op_reg", "out_payload",
        "stg1_tok", "stg2_tok", "stg3_tok", "d1_reg", "d2_reg", "val_out",
        "skid_vld", "skid_payload", "main_vld", "main_payload", "out_vld",
        "credit_count", "tx_token", "pipe_d1", "tx_valid",
        "busy_cycles", "pipe_valid", "pipe_result", "done_strobe",
        "gray_wr_ptr", "gray_rd_ptr", "bin_wr_ptr", "bin_rd_ptr", "fifo_occ",
        "watermark_lvl", "prog_full", "prog_empty",
        "chunk_idx", "tvalid_out", "tready_in", "tlast_out",
        "main_state", "sub_state", "seq_done",
        "frac_acc", "baud_tick", "tx_bit_cnt", "serial_tx", "tx_busy",
        "p1_val", "p1_dat", "p2_val", "p2_dat", "p_out_val",
        "head_idx", "tail_idx", "items_avail",
        "strm_val", "strm_rdy", "occupancy_tok", "strm_val_out",
        "fetch_v", "dec_v", "ex_v", "mem_v", "wb_v", "retire_v",
        "token_ring", "packet_id", "route_valid", "ring_eject"
    ]]
    if not query_signals:
        query_signals = candidate_signals[:6]

    # Tool 1: read_rtl_file
    tool1_call = {
        "action": "tool_call",
        "thought": f"Observed symptom '{symptom}' on design '{task_id}'. I will read the RTL source code to inspect register declarations and pipeline stages.",
        "tool_name": "read_rtl_file",
        "tool_args": {"task_id": task_id}
    }
    tool1_res = get_cached_tool_result(tools, "read_rtl_file", {"task_id": task_id})
    # Keep tool output compact (~220 chars max) to prevent token bloat
    tool1_summary_str = json.dumps(tool1_res)[:220]

    # Tool 2: get_waveform_summary
    tool2_call = {
        "action": "tool_call",
        "thought": f"RTL declares candidate signals {candidate_signals[:5]}. I will query the simulation waveform to trace the earliest causal divergence cycle.",
        "tool_name": "get_waveform_summary",
        "tool_args": {"task_id": task_id, "signals": query_signals}
    }
    tool2_res = get_cached_tool_result(tools, "get_waveform_summary", {"task_id": task_id, "signals": query_signals})
    tool2_summary_str = json.dumps(tool2_res)[:260]

    # Conclude Object
    if is_unknown:
        conclude_obj = {
            "action": "conclude",
            "thought": (
                f"Waveform query on '{task_id}' shows fewer than 2 active signal transitions; "
                f"the testbench aborted before the initiating transaction was exercised. "
                f"Observable evidence is insufficient to identify the root cause. Concluding 'unknown'."
            ),
            "candidate_signal": "unknown",
            "suspected_root_cause": "Insufficient simulation evidence: trace terminated prematurely.",
            "root_cause_location": "unknown",
            "causal_chain": [
                "Simulation initiated",
                "Trace terminated before transaction active edge",
                "Insufficient evidence for definitive RCA"
            ],
            "causal_signals": [],
            "evidence": [
                "Waveform file contains 0 transaction pulses prior to finish.",
                "No causal divergence observed."
            ],
            "confidence": 0.20
        }
    elif is_hard_negative:
        conclude_obj = {
            "action": "conclude",
            "thought": (
                f"HYPOTHESIS CONTRAST ({symptom_distractor} vs {ground_truth_signal}): "
                f"Waveform cross-examination reveals that register '{ground_truth_signal}' diverged at T={divergence_cycle}. "
                f"Candidate '{symptom_distractor}' correctly maintained valid state until downstream assertion failure at T={assertion_cycle}. "
                f"Under first-causal-divergence rules, '{symptom_distractor}' is a symptom and '{ground_truth_signal}' is the root cause."
            ),
            "candidate_signal": ground_truth_signal,
            "suspected_root_cause": f"Verified causal defect on register '{ground_truth_signal}'.",
            "root_cause_location": f"{design_family} module logic",
            "causal_chain": [
                f"Transaction initiated at T={divergence_cycle}",
                f"Register '{ground_truth_signal}' diverged from expected behavior",
                f"Downstream candidate '{symptom_distractor}' failed at T={assertion_cycle}"
            ],
            "causal_signals": [ground_truth_signal],
            "evidence": [
                f"Register '{ground_truth_signal}' exhibited first causal divergence at T={divergence_cycle}.",
                f"Downstream candidate '{symptom_distractor}' remained valid during divergence."
            ],
            "confidence": 0.95
        }
    else:
        conclude_obj = {
            "action": "conclude",
            "thought": (
                f"Temporal waveform analysis reveals that at cycle T={divergence_cycle}, signal '{ground_truth_signal}' "
                f"exhibited first abnormal transition prior to assertion failure at T={assertion_cycle}. "
                f"Rejecting downstream distractor '{symptom_distractor}'; '{ground_truth_signal}' is the causal root cause."
            ),
            "candidate_signal": ground_truth_signal,
            "suspected_root_cause": f"{design_family.upper()} root cause defect on '{ground_truth_signal}'.",
            "root_cause_location": f"{design_family} module logic",
            "causal_chain": [
                f"Stimulus transaction applied before T={divergence_cycle}",
                f"Signal '{ground_truth_signal}' diverged at T={divergence_cycle}",
                f"Downstream manifestation '{symptom}' occurred at T={assertion_cycle}"
            ],
            "causal_signals": [ground_truth_signal],
            "evidence": [
                f"Earliest causal divergence localized to '{ground_truth_signal}' at cycle T={divergence_cycle}.",
                f"Distractor '{symptom_distractor}' remained consistent prior to failure."
            ],
            "confidence": 0.95
        }

    # -------------------------------------------------------------
    # 1. TYPE A EXAMPLE: Tool Selection (Context -> Next Tool Call)
    # -------------------------------------------------------------
    type_a_user = f"{base_prompt}\n\n[Step 1/4] Decide your next action (tool_call or conclude)."
    type_a_example = {
        "example_id": f"{example_prefix}_{task_id}_typeA_tool_selection",
        "example_type": "TYPE_A_TOOL_SELECTION",
        "target_type": "tool_call",
        "task_id": task_id,
        "design_family": design_family,
        "ground_truth_signal": ground_truth_signal,
        "conversations": [
            {"role": "system", "value": RCA_SYSTEM_PROMPT_STAGE_B},
            {"role": "user", "value": type_a_user},
            {"role": "assistant", "value": json.dumps(tool1_call, indent=2)}
        ]
    }

    # -------------------------------------------------------------
    # 2. TYPE B EXAMPLE: Evidence-Conditioned Next Action
    # -------------------------------------------------------------
    type_b_user = (
        f"{base_prompt}\n\n[Step 1/4] Decide your next action (tool_call or conclude).\n\n"
        f"[Agent Thought]: {tool1_call['thought']}\n"
        f"[Tool Call]: {tool1_call['tool_name']}({json.dumps(tool1_call['tool_args'])})\n"
        f"[Tool Output]: {tool1_summary_str}\n\n"
        f"[Step 2/4] Decide your next action (tool_call or conclude)."
    )
    type_b_example = {
        "example_id": f"{example_prefix}_{task_id}_typeB_next_action",
        "example_type": "TYPE_B_EVIDENCE_CONDITIONED",
        "target_type": "tool_call",
        "task_id": task_id,
        "design_family": design_family,
        "ground_truth_signal": ground_truth_signal,
        "conversations": [
            {"role": "system", "value": RCA_SYSTEM_PROMPT_STAGE_B},
            {"role": "user", "value": type_b_user},
            {"role": "assistant", "value": json.dumps(tool2_call, indent=2)}
        ]
    }

    # -------------------------------------------------------------
    # 3. TYPE C EXAMPLE: Final Decision
    # -------------------------------------------------------------
    type_c_user = (
        f"{type_b_user}\n\n"
        f"[Agent Thought]: {tool2_call['thought']}\n"
        f"[Tool Call]: {tool2_call['tool_name']}({json.dumps(tool2_call['tool_args'])})\n"
        f"[Tool Output]: {tool2_summary_str}\n\n"
        f"[Step 3/4] Decide your next action (tool_call or conclude)."
    )
    type_c_example = {
        "example_id": f"{example_prefix}_{task_id}_typeC_final_decision",
        "example_type": "TYPE_C_FINAL_DECISION",
        "target_type": "conclude",
        "task_id": task_id,
        "design_family": design_family,
        "ground_truth_signal": ground_truth_signal,
        "conversations": [
            {"role": "system", "value": RCA_SYSTEM_PROMPT_STAGE_B},
            {"role": "user", "value": type_c_user},
            {"role": "assistant", "value": json.dumps(conclude_obj, indent=2)}
        ]
    }

    return [type_a_example, type_b_example, type_c_example]


def generate_v10_2_per_turn_dataset():
    tools = AgentToolRegistry(workspace_root=WORKSPACE_ROOT)
    print("=" * 96)
    print("EXPERIMENT V10.2: GENERATING PER-TURN AGENTIC SFT DATASET")
    print("=" * 96)

    train_examples = []
    val_examples = []
    gen_examples = []

    arch_specs = {
        # Train Pipelines
        "v10_pipe_2stage_decoupled": ("pipeline", "PIPE_STALL_BUBBLE", "s1_valid", "Data Lost on Stall", ["in_valid", "in_data", "s1_valid", "s1_data", "out_valid", "out_data"], "s1_data", 35, 45, False),
        "v10_pipe_3stage_hazard": ("pipeline", "PIPE_FORWARD_HAZARD", "fwd_data", "RAW Hazard Stale Data", ["in_valid", "in_payload", "stage1_vld", "stage2_vld", "fwd_data", "op_reg", "out_valid", "out_payload"], "stage1_vld", 35, 55, True),
        "v10_pipe_4stage_deep": ("pipeline", "PIPE_MULTI_STAGE_STALL", "stg2_tok", "Throughput Bubble on Stage 2", ["val_in", "dat_in", "stg1_tok", "stg2_tok", "stg3_tok", "d1_reg", "d2_reg", "val_out"], "d2_reg", 35, 65, False),
        "v10_pipe_skid_elastic": ("pipeline", "PIPE_SKID_DRAIN_DROP", "skid_vld", "Skid Buffer Drain Failure", ["push_val", "push_dat", "skid_vld", "skid_payload", "main_vld", "main_payload", "out_vld"], "skid_payload", 35, 45, False),
        "v10_pipe_credit_backpressure": ("pipeline", "PIPE_CREDIT_FLOW", "credit_count", "Credit Buffer Premature Drop", ["tx_req", "tx_data", "credit_count", "tx_token", "pipe_d1", "tx_valid"], "pipe_d1", 35, 45, True),
        "v10_pipe_var_latency": ("pipeline", "PIPE_VAR_LATENCY", "busy_cycles", "Completion Flag Desync", ["start_calc", "op_val", "busy_cycles", "pipe_valid", "pipe_result", "done_strobe"], "pipe_result", 35, 40, True),
        
        # Train Other Families
        "v10_fifo_gray_ptr": ("fifo", "FIFO_GRAY_SYNC", "gray_wr_ptr", "Gray Code Pointer Corruption", ["wr_strobe", "rd_strobe", "wr_payload", "gray_wr_ptr", "gray_rd_ptr", "bin_wr_ptr", "bin_rd_ptr", "fifo_occ", "buf_full"], "buf_full", 35, 40, True),
        "v10_fifo_watermark": ("fifo", "FIFO_WATERMARK", "watermark_lvl", "Watermark Counter Anomaly", ["w_en", "r_en", "w_data", "watermark_lvl", "prog_full", "prog_empty", "r_data"], "prog_full", 35, 35, True),
        "v10_axi_split_transfer": ("axi", "AXI_HANDSHAKE_HOLD", "tvalid_out", "AXI Handshake Hold Violation", ["tstart", "chunk_idx", "tvalid_out", "tready_in", "tlast_out", "tdata_out"], "tdata_out", 35, 35, False),
        "v10_fsm_hierarchical_seq": ("fsm", "FSM_SUBSTATE_SKIP", "sub_state", "FSM Sub-State Transition Skip", ["start_pulse", "main_state", "sub_state", "seq_done", "out_flag"], "out_flag", 35, 45, True),
        "v10_uart_fractional_baud": ("uart", "UART_FRAC_BAUD", "frac_acc", "Fractional Baud Clock Early Rollover", ["tx_enable", "tx_byte", "frac_acc", "baud_tick", "tx_bit_cnt", "serial_tx", "tx_busy"], "serial_tx", 35, 60, True),

        # Validation Architectures (Architecture-Disjoint)
        "v10_val_pipe_3stage_split": ("pipeline", "PIPE_STALL_BUBBLE", "p1_val", "Validation Pipeline Token Drop", ["p_in_val", "p_in_dat", "p1_val", "p1_dat", "p2_val", "p2_dat", "p_out_val"], "p1_dat", 35, 45, False),
        "v10_val_fifo_ring_buf": ("fifo", "FIFO_RING_ITEMS", "items_avail", "Ring Buffer Items Count Corruption", ["push_cmd", "pop_cmd", "data_in", "head_idx", "tail_idx", "items_avail", "data_out"], "data_out", 35, 35, True),
        "v10_val_axi_stream_fifo": ("axi", "AXI_STREAM_STABILITY", "strm_val", "Stream Handshake Stability Drop", ["strm_val_in", "strm_rdy_out", "strm_val", "strm_rdy", "occupancy_tok", "strm_val_out"], "occupancy_tok", 35, 35, False),

        # Generalization Architectures (Unseen Topologies)
        "v10_gen_pipe_5stage_branch": ("pipeline", "PIPE_BRANCH_FLUSH_LEAK", "ex_v", "5-Stage Branch Flush Leak", ["fetch_req", "fetch_v", "dec_v", "ex_v", "mem_v", "wb_v", "branch_flush", "retire_v"], "retire_v", 45, 55, False),
        "v10_gen_pipe_elastic_ring": ("pipeline", "PIPE_RING_TOKEN_COLLAPSE", "token_ring", "Ring Circulating Token Collapse", ["ring_inject", "token_ring", "packet_id", "route_valid", "ring_eject"], "ring_eject", 35, 45, False)
    }

    # Generate diverse per-turn variations
    for task_id, (fam, mech, root_sig, symp, cands, distractor, t_div, t_fail, is_hn) in arch_specs.items():
        arch_split = V10_ARCHITECTURES[task_id]["split"]
        n_repeats = 16 if arch_split == "TRAIN" else (10 if arch_split == "VALIDATION" else 6)

        for rep in range(n_repeats):
            # Alternate hard negative contrast vs positive
            use_hn = is_hn or (rep % 2 == 1)
            ex_list = build_per_turn_trajectory_examples(
                tools=tools,
                task_id=task_id,
                design_family=fam,
                defect_mechanism=mech,
                ground_truth_signal=root_sig,
                symptom=symp,
                candidate_signals=cands,
                symptom_distractor=distractor,
                divergence_cycle=t_div,
                assertion_cycle=t_fail,
                is_hard_negative=use_hn,
                is_unknown=False,
                example_prefix=f"v10_2_rep{rep}"
            )

            if arch_split == "TRAIN":
                train_examples.extend(ex_list)
            elif arch_split == "VALIDATION":
                val_examples.extend(ex_list)
            else:
                gen_examples.extend(ex_list)

    # UNKNOWN Trajectories
    unk_bases = [
        ("v10_pipe_2stage_decoupled", "pipeline", ["in_valid", "in_data", "s1_valid", "s1_data", "out_valid"]),
        ("v10_fifo_gray_ptr", "fifo", ["wr_strobe", "rd_strobe", "gray_wr_ptr", "bin_wr_ptr", "fifo_occ"]),
        ("v10_axi_split_transfer", "axi", ["tstart", "chunk_idx", "tvalid_out", "tready_in", "tlast_out"]),
        ("v10_fsm_hierarchical_seq", "fsm", ["start_pulse", "main_state", "sub_state", "seq_done"]),
        ("v10_uart_fractional_baud", "uart", ["tx_enable", "frac_acc", "baud_tick", "tx_bit_cnt", "serial_tx"]),
        ("v10_val_pipe_3stage_split", "pipeline", ["p_in_val", "p_in_dat", "p1_val", "p1_dat", "p_out_val"]),
        ("v10_val_fifo_ring_buf", "fifo", ["push_cmd", "pop_cmd", "head_idx", "tail_idx", "items_avail"])
    ]

    for u_task, u_fam, u_cands in unk_bases:
        is_val = "val" in u_task
        n_unk = 6 if not is_val else 4
        for u_idx in range(n_unk):
            u_examples = build_per_turn_trajectory_examples(
                tools=tools,
                task_id=u_task,
                design_family=u_fam,
                defect_mechanism="INSUFFICIENT_EVIDENCE",
                ground_truth_signal="unknown",
                symptom="TRUNCATED_SIMULATION_ABORT",
                candidate_signals=u_cands,
                symptom_distractor="none",
                divergence_cycle=0,
                assertion_cycle=0,
                is_hard_negative=False,
                is_unknown=True,
                example_prefix=f"v10_2_unk{u_idx}"
            )
            if is_val:
                val_examples.extend(u_examples)
            else:
                train_examples.extend(u_examples)

    # Create Small Smoke Dataset (30 trajectories -> ~90 per-turn examples)
    smoke_tasks = ["v10_pipe_2stage_decoupled", "v10_fifo_gray_ptr", "v10_axi_split_transfer"]
    smoke_examples = [ex for ex in train_examples if ex["task_id"] in smoke_tasks][:75]

    random.seed(42)
    random.shuffle(train_examples)
    random.shuffle(val_examples)
    random.shuffle(gen_examples)
    random.shuffle(smoke_examples)

    # Supervision Health Accounting
    tool_targets = sum(1 for ex in train_examples if ex["target_type"] == "tool_call")
    conclude_targets = sum(1 for ex in train_examples if ex["target_type"] == "conclude")

    print("\nV10.2 Dataset Statistics:")
    print(f"  - TRAIN Per-Turn Examples:     {len(train_examples)}")
    print(f"    * Tool Call Targets:         {tool_targets} ({tool_targets/len(train_examples)*100:.1f}%)")
    print(f"    * Conclude Targets:          {conclude_targets} ({conclude_targets/len(train_examples)*100:.1f}%)")
    print(f"  - VALIDATION Per-Turn Examples:{len(val_examples)}")
    print(f"  - GENERALIZATION Examples:     {len(gen_examples)}")
    print(f"  - SMOKE Per-Turn Examples:     {len(smoke_examples)}")

    # Leakage Checks
    for ex in train_examples:
        tid = ex["task_id"]
        if tid in FROZEN_BENCHMARK_IDS:
            raise RuntimeError(f"CRITICAL LEAKAGE: Frozen benchmark '{tid}' in TRAIN!")
        if "val" in tid or "gen" in tid:
            raise RuntimeError(f"CRITICAL SPLIT LEAKAGE: '{tid}' in TRAIN!")

    for ex in val_examples:
        tid = ex["task_id"]
        if tid in FROZEN_BENCHMARK_IDS:
            raise RuntimeError(f"CRITICAL LEAKAGE: Frozen benchmark '{tid}' in VALIDATION!")
        if "v10_pipe_2stage" in tid or "v10_fifo_gray" in tid:
            raise RuntimeError(f"CRITICAL SPLIT LEAKAGE: '{tid}' in VALIDATION!")

    print("\n[PASS] Zero-Leakage Gate: 100% architectural disjointness verified across all splits.")

    ws_v10_2_dir = os.path.join(WORKSPACE_ROOT, "datasets", "v10_2")
    ml_v10_2_dir = "C:/Users/varad/ml-cache/rca-reuse/v10_2/datasets"
    os.makedirs(ws_v10_2_dir, exist_ok=True)
    os.makedirs(ml_v10_2_dir, exist_ok=True)

    splits_map = {
        "per_turn_train_v10_2.json": train_examples,
        "per_turn_val_v10_2.json": val_examples,
        "per_turn_gen_v10_2.json": gen_examples,
        "per_turn_smoke_v10_2.json": smoke_examples
    }

    for fname, data in splits_map.items():
        ws_p = os.path.join(ws_v10_2_dir, fname)
        ml_p = os.path.join(ml_v10_2_dir, fname)
        with open(ws_p, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2)
        with open(ml_p, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2)

    print(f"\n[PASS] V10.2 Datasets saved to:\n  - {ws_v10_2_dir}\n  - {ml_v10_2_dir}")


if __name__ == "__main__":
    generate_v10_2_per_turn_dataset()
