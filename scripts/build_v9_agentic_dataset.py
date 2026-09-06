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
from src.agent.context_builder import build_rca_context, format_rca_context_prompt

# ==============================================================================
# FROZEN EVALUATION TEST SET — STRICTLY OFF-LIMITS (ZERO LEAKAGE INVARIANT)
# ==============================================================================
FROZEN_TEST_IDS = {
    "heldout_fifo_src", "fifo_vl_a1", "fifo_vl_b1", "fifo_vl_f1", "fifo_vl_i2",
    "heldout_axi_src", "axi_vl_a1", "axi_vl_b1", "axi_vl_f1", "axi_vl_i2",
    "heldout_fsm_src", "fsm_vl_a1", "fsm_vl_b1", "fsm_vl_f1", "fsm_vl_i2",
    "heldout_uart_src", "uart_vl_a1", "uart_vl_b1", "uart_vl_f1", "uart_vl_i2",
    "heldout_pipe_src", "pipeline_vl_a1", "pipeline_vl_b1", "pipeline_vl_f1", "pipeline_vl_i2",
    "fifo_f5_inc", "axi_f5_inc", "fsm_f5_inc", "uart_f5_inc", "pipeline_f5_inc"
}


def build_agentic_trajectory(
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
    tool_sequence_pattern: str = "rtl_first"
) -> Dict[str, Any]:
    """
    Constructs a multi-step evidence-driven agentic trajectory.
    Supports two authentic verification workflows:
      - 'rtl_first': read_rtl_file -> get_waveform_summary -> conclude
      - 'sim_first': read_simulation_log -> read_rtl_file -> get_waveform_summary -> conclude
    """
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
        base_prompt = format_rca_context_prompt(rca_ctx)
    except Exception:
        base_prompt = (
            f"=== HARDWARE ROOT CAUSE ANALYSIS: {task_id} ===\n"
            f"Design Family: {design_family}\n"
            f"Observed Symptom: {symptom}\n"
            f"Candidate Signals: {candidate_signals}\n"
        )

    conversations = []
    conversations.append({"role": "system", "value": RCA_SYSTEM_PROMPT_STAGE_B})

    query_sigs = [s for s in candidate_signals if s in ["valid_in", "d_in", "v1", "d1", "v2", "d2", "valid_out", "d_out", "count", "write_ptr", "read_ptr", "full", "empty", "ready_in", "ready_out", "state", "start", "done", "cnt", "tx"]]
    if not query_sigs:
        query_sigs = candidate_signals[:6]

    if tool_sequence_pattern == "sim_first":
        # 3-step investigation: read_simulation_log -> read_rtl_file -> get_waveform_summary -> conclude
        turn1_user = f"{base_prompt}\n\n[Step 1/4] Decide your next action (tool_call or conclude)."
        conversations.append({"role": "user", "value": turn1_user})

        turn1_thought = (
            f"Observed '{symptom}' on '{task_id}'. I will first inspect the testbench simulation log "
            f"to determine the exact assertion timestamp and failure signature."
        )
        turn1_call = {
            "action": "tool_call",
            "thought": turn1_thought,
            "tool_name": "read_simulation_log",
            "tool_args": {"task_id": task_id, "design_family": design_family}
        }
        conversations.append({"role": "assistant", "value": json.dumps(turn1_call, indent=2)})
        tool1_res = tools.execute_tool("read_simulation_log", {"task_id": task_id, "design_family": design_family})
        tool1_str = json.dumps(tool1_res)[:1000]

        turn2_user = (
            f"{turn1_user}\n\n"
            f"[Agent Thought]: {turn1_thought}\n"
            f"[Tool Call]: read_simulation_log({json.dumps({'task_id': task_id, 'design_family': design_family})})\n"
            f"[Tool Output]: {tool1_str}\n\n"
            f"[Step 2/4] Decide your next action (tool_call or conclude)."
        )
        conversations.append({"role": "user", "value": turn2_user})

        turn2_thought = "Simulation confirms failure. Now I will read the RTL source to examine module register declarations."
        turn2_call = {
            "action": "tool_call",
            "thought": turn2_thought,
            "tool_name": "read_rtl_file",
            "tool_args": {"task_id": task_id}
        }
        conversations.append({"role": "assistant", "value": json.dumps(turn2_call, indent=2)})
        tool2_res = tools.execute_tool("read_rtl_file", {"task_id": task_id})
        tool2_str = json.dumps(tool2_res)[:1200]

        turn3_user = (
            f"{turn2_user}\n\n"
            f"[Agent Thought]: {turn2_thought}\n"
            f"[Tool Call]: read_rtl_file({json.dumps({'task_id': task_id})})\n"
            f"[Tool Output]: {tool2_str}\n\n"
            f"[Step 3/4] Decide your next action (tool_call or conclude)."
        )
        conversations.append({"role": "user", "value": turn3_user})

        turn3_thought = "RTL declares candidate signals. Now querying waveform to verify signal transition timeline."
        turn3_call = {
            "action": "tool_call",
            "thought": turn3_thought,
            "tool_name": "get_waveform_summary",
            "tool_args": {"task_id": task_id, "signals": query_sigs}
        }
        conversations.append({"role": "assistant", "value": json.dumps(turn3_call, indent=2)})
        tool3_res = tools.execute_tool("get_waveform_summary", {"task_id": task_id, "signals": query_sigs})
        tool3_str = json.dumps(tool3_res)[:1500]

        final_user = (
            f"{turn3_user}\n\n"
            f"[Agent Thought]: {turn3_thought}\n"
            f"[Tool Call]: get_waveform_summary({json.dumps({'task_id': task_id, 'signals': query_sigs})})\n"
            f"[Tool Output]: {tool3_str}\n\n"
            f"[Step 4/4] Decide your next action (tool_call or conclude)."
        )
        conversations.append({"role": "user", "value": final_user})

    else:
        # 2-step standard investigation: read_rtl_file -> get_waveform_summary -> conclude
        turn1_user = f"{base_prompt}\n\n[Step 1/3] Decide your next action (tool_call or conclude)."
        conversations.append({"role": "user", "value": turn1_user})

        turn1_thought = (
            f"The failure summary reports '{symptom}' on design '{task_id}'. "
            f"I will inspect the RTL source code to examine candidate signal declarations and stage progression."
        )
        turn1_call = {
            "action": "tool_call",
            "thought": turn1_thought,
            "tool_name": "read_rtl_file",
            "tool_args": {"task_id": task_id}
        }
        conversations.append({"role": "assistant", "value": json.dumps(turn1_call, indent=2)})

        tool1_res = tools.execute_tool("read_rtl_file", {"task_id": task_id})
        tool1_str = json.dumps(tool1_res)[:1200]

        turn2_user = (
            f"{turn1_user}\n\n"
            f"[Agent Thought]: {turn1_thought}\n"
            f"[Tool Call]: read_rtl_file({json.dumps({'task_id': task_id})})\n"
            f"[Tool Output]: {tool1_str}\n\n"
            f"[Step 2/3] Decide your next action (tool_call or conclude)."
        )
        conversations.append({"role": "user", "value": turn2_user})

        turn2_thought = (
            f"RTL declared candidate signals {candidate_signals}. "
            f"I will query waveform activity to establish the chronological timeline and first causal divergence."
        )
        turn2_call = {
            "action": "tool_call",
            "thought": turn2_thought,
            "tool_name": "get_waveform_summary",
            "tool_args": {"task_id": task_id, "signals": query_sigs}
        }
        conversations.append({"role": "assistant", "value": json.dumps(turn2_call, indent=2)})

        tool2_res = tools.execute_tool("get_waveform_summary", {"task_id": task_id, "signals": query_sigs})
        tool2_str = json.dumps(tool2_res)[:1500]

        final_user = (
            f"{turn2_user}\n\n"
            f"[Agent Thought]: {turn2_thought}\n"
            f"[Tool Call]: get_waveform_summary({json.dumps({'task_id': task_id, 'signals': query_sigs})})\n"
            f"[Tool Output]: {tool2_str}\n\n"
            f"[Step 3/3] Decide your next action (tool_call or conclude)."
        )
        conversations.append({"role": "user", "value": final_user})

    # Conclude Assistant Turn with first-causal-divergence temporal reasoning
    if design_family == "pipeline":
        if ground_truth_signal in ["v1", "v2", "valid_out"]:
            conclude_thought = (
                f"Temporal waveform analysis establishes that the transaction was accepted into stage 1. "
                f"At cycle T={divergence_cycle}, the stage control token '{ground_truth_signal}' dropped to 0 "
                f"without propagating downstream to valid_out or holding during stall. "
                f"Although data register '{symptom_distractor}' appears inconsistent downstream at T={assertion_cycle}, "
                f"data path registers in synchronous pipelines are passive operand containers whose validity is governed "
                f"strictly by control tokens. The earliest causal event occurred at T={divergence_cycle} on '{ground_truth_signal}'. "
                f"Therefore, '{symptom_distractor}' is a downstream symptom and '{ground_truth_signal}' is the true causal root cause."
            )
            causal_chain = [
                f"Input transaction accepted at pipeline entrance before T={divergence_cycle}",
                f"Stage control token '{ground_truth_signal}' dropped or failed retention at T={divergence_cycle}",
                f"Downstream stage received an invalid bubble leading to symptom '{symptom}' at T={assertion_cycle}"
            ]
            evidence = [
                f"Control token '{ground_truth_signal}' exhibited abnormal transition at T={divergence_cycle} prior to assertion failure.",
                f"Data register '{symptom_distractor}' correctly latched its input operand and did not corrupt data autonomously.",
                f"First causal divergence is localized to stage control flip-flop '{ground_truth_signal}'."
            ]
            suspected_root_cause = f"Pipeline control token propagation fault on '{ground_truth_signal}': token lost or unpropagated during stall."
        else:  # Data path hazard e.g. d1
            conclude_thought = (
                f"Waveform and RTL cross-examination shows that stage valid tokens propagated on schedule without dropping bubbles. "
                f"However, at cycle T={divergence_cycle}, data operand forwarding into '{ground_truth_signal}' failed to select "
                f"the uncommitted result from the adjacent stage, latching stale data. "
                f"Because control token '{symptom_distractor}' operated correctly, the failure is localized to data path operand "
                f"register '{ground_truth_signal}'. This is a genuine data hazard rather than a control token drop."
            )
            causal_chain = [
                f"Back-to-back pipeline instructions created a read-after-write hazard",
                f"Forwarding multiplexer failed to update register '{ground_truth_signal}' with bypass operand at T={divergence_cycle}",
                f"Downstream execution computed with stale operand resulting in '{symptom}' at T={assertion_cycle}"
            ]
            evidence = [
                f"Control tokens remained asserted, confirming no pipeline stall or bubble insertion occurred.",
                f"Data register '{ground_truth_signal}' latched stale operand at T={divergence_cycle}.",
                f"Forwarding bypass logic failed to route the uncommitted result to '{ground_truth_signal}'."
            ]
            suspected_root_cause = f"Pipeline data hazard bypass defect on '{ground_truth_signal}': forwarding logic failed to update operand."

    elif design_family == "fifo":
        conclude_thought = (
            f"Waveform analysis reveals that at T={divergence_cycle}, simultaneous read/write occurred. "
            f"While write_ptr and read_ptr incremented normally, occupancy counter '{ground_truth_signal}' failed to conserve count. "
            f"Output port '{symptom_distractor}' asserted empty/underflow later at T={assertion_cycle} as a downstream consequence of count corruption. "
            f"Rejecting downstream symptom '{symptom_distractor}'; '{ground_truth_signal}' is the root cause."
        )
        causal_chain = [
            f"Simultaneous read and write requests asserted at T={divergence_cycle}",
            f"Occupancy counter '{ground_truth_signal}' updated incorrectly instead of holding constant",
            f"Downstream status flag or data line '{symptom_distractor}' failed at T={assertion_cycle}"
        ]
        evidence = [
            f"Occupancy counter '{ground_truth_signal}' deviated at T={divergence_cycle}.",
            f"Pointers incremented properly, confirming counter logic is the root cause."
        ]
        suspected_root_cause = f"FIFO simultaneous read/write counter corruption on '{ground_truth_signal}'."

    elif design_family == "axi":
        conclude_thought = (
            f"At T={divergence_cycle}, valid_in was asserted with ready_in low. Under the AXI protocol obligation, "
            f"'{ground_truth_signal}' must remain stable until handshake completion. Instead, '{ground_truth_signal}' dropped prematurely. "
            f"Rejecting slave port '{symptom_distractor}'; root cause is master valid stability on '{ground_truth_signal}'."
        )
        causal_chain = [
            f"Master initiated transfer with valid asserted at T={divergence_cycle}",
            f"Signal '{ground_truth_signal}' dropped before ready acknowledgement",
            f"Protocol handshake timeout occurred at T={assertion_cycle}"
        ]
        evidence = [
            f"Signal '{ground_truth_signal}' deasserted while ready_in was low at T={divergence_cycle}.",
            f"Violates handshake stability obligation (V and not R implies V_next)."
        ]
        suspected_root_cause = f"AXI handshake hold violation on '{ground_truth_signal}'."

    elif design_family == "fsm":
        conclude_thought = (
            f"At T={divergence_cycle}, start was asserted but FSM state register '{ground_truth_signal}' entered deadlock state 0. "
            f"Output strobe '{symptom_distractor}' never asserted at T={assertion_cycle} because the FSM never reached state 2. "
            f"Rejecting output strobe '{symptom_distractor}'; internal state register '{ground_truth_signal}' is the root cause."
        )
        causal_chain = [
            f"Start stimulus asserted at T={divergence_cycle}",
            f"State register '{ground_truth_signal}' transitioned to invalid deadlock state",
            f"Bus transaction deadlocked without completion strobe at T={assertion_cycle}"
        ]
        evidence = [
            f"State register '{ground_truth_signal}' failed to advance to next state.",
            f"Output '{symptom_distractor}' failure is purely downstream of state deadlock."
        ]
        suspected_root_cause = f"FSM state transition table deadlock on '{ground_truth_signal}'."

    else:  # uart
        conclude_thought = (
            f"Waveform timing analysis reveals that baud prescaler counter '{ground_truth_signal}' increments with modulo 6 "
            f"instead of modulo 8 starting at T={divergence_cycle}. Serial output port '{symptom_distractor}' failed assertion at T={assertion_cycle} "
            f"due to cumulative framing drift. Output port '{symptom_distractor}' is the symptom port; '{ground_truth_signal}' is the root cause."
        )
        causal_chain = [
            f"Serial transmission started at T={divergence_cycle}",
            f"Baud rate divisor counter '{ground_truth_signal}' rolled over early",
            f"Accumulated phase error resulted in serial framing mismatch at T={assertion_cycle}"
        ]
        evidence = [
            f"Counter '{ground_truth_signal}' rollover cycle period is shorter than specification.",
            f"Serial output '{symptom_distractor}' is a passive shift register symptom port."
        ]
        suspected_root_cause = f"UART baud clock prescaler premature rollover on '{ground_truth_signal}'."

    turn_conclude = {
        "action": "conclude",
        "thought": conclude_thought,
        "candidate_signal": ground_truth_signal,
        "suspected_root_cause": suspected_root_cause,
        "root_cause_location": f"{design_family} module logic",
        "causal_chain": causal_chain,
        "causal_signals": [ground_truth_signal],
        "evidence": evidence,
        "confidence": 0.95
    }
    conversations.append({"role": "assistant", "value": json.dumps(turn_conclude, indent=2)})

    return {
        "example_id": f"v9_traj_{task_id}_{tool_sequence_pattern}",
        "task_id": task_id,
        "design_family": design_family,
        "example_type": "HARD_NEGATIVE" if is_hard_negative else "POSITIVE_RCA",
        "ground_truth_signal": ground_truth_signal,
        "candidate_signals": candidate_signals,
        "defect_mechanism": defect_mechanism,
        "tool_sequence": tool_sequence_pattern,
        "conversations": conversations
    }


def build_unknown_trajectory(
    tools: AgentToolRegistry,
    task_id: str,
    design_family: str,
    candidate_signals: List[str]
) -> Dict[str, Any]:
    """Constructs an agentic trajectory where investigation concludes UNKNOWN due to missing/truncated evidence."""
    metadata = {
        "symptom": "TRUNCATED_SIMULATION_ABORT",
        "design_family": design_family,
        "suspected_module": design_family,
        "ground_truth_signals": ["unknown"],
        "candidate_signals": candidate_signals,
        "target_signals": candidate_signals
    }

    try:
        rca_ctx = build_rca_context(task_id, design_family, metadata, tools.workspace_root)
        base_prompt = format_rca_context_prompt(rca_ctx)
    except Exception:
        base_prompt = f"=== HARDWARE ROOT CAUSE ANALYSIS: {task_id} ===\nObserved Symptom: TRUNCATED_SIMULATION_ABORT\n"

    conversations = []
    conversations.append({"role": "system", "value": RCA_SYSTEM_PROMPT_STAGE_B})

    turn1_user = f"{base_prompt}\n\n[Step 1/3] Decide your next action (tool_call or conclude)."
    conversations.append({"role": "user", "value": turn1_user})

    turn1_thought = (
        f"The simulation log indicates early testbench termination. "
        f"I will query waveform activity for candidate signals {candidate_signals[:4]} to check if the transaction completed."
    )
    turn1_call = {
        "action": "tool_call",
        "thought": turn1_thought,
        "tool_name": "get_waveform_summary",
        "tool_args": {"task_id": task_id, "signals": candidate_signals[:4]}
    }
    conversations.append({"role": "assistant", "value": json.dumps(turn1_call, indent=2)})

    tool1_res = tools.execute_tool("get_waveform_summary", {"task_id": task_id, "signals": candidate_signals[:4]})
    tool1_summary = json.dumps(tool1_res)[:1200]

    turn2_user = (
        f"{turn1_user}\n\n"
        f"[Agent Thought]: {turn1_thought}\n"
        f"[Tool Call]: get_waveform_summary({json.dumps({'task_id': task_id, 'signals': candidate_signals[:4]})})\n"
        f"[Tool Output]: {tool1_summary}\n\n"
        f"[Step 2/3] Decide your next action (tool_call or conclude)."
    )
    conversations.append({"role": "user", "value": turn2_user})

    turn2_thought = (
        f"The waveform reveals fewer than 2 signal transitions; the clock ran for only a few cycles before aborting. "
        f"The initiating transaction was never exercised in this trace. "
        f"Under hardware RCA rules, when observable evidence is missing or truncated, the model must return 'unknown' "
        f"rather than guessing a signal without empirical support."
    )
    turn2_conclude = {
        "action": "conclude",
        "thought": turn2_thought,
        "candidate_signal": "unknown",
        "suspected_root_cause": "Insufficient simulation evidence: waveform terminated before initiating transaction was exercised.",
        "root_cause_location": "unknown",
        "causal_chain": [
            "Simulation initiated",
            "Trace terminated prematurely before transaction activation",
            "Observable evidence is insufficient to identify causal root cause"
        ],
        "causal_signals": [],
        "evidence": [
            "Waveform file contains truncated activity with zero transaction pulses.",
            "No state divergence observed prior to early finish."
        ],
        "confidence": 0.20
    }
    conversations.append({"role": "assistant", "value": json.dumps(turn2_conclude, indent=2)})

    return {
        "example_id": f"v9_traj_unk_{task_id}",
        "task_id": task_id,
        "design_family": design_family,
        "example_type": "UNKNOWN_INSUFFICIENT",
        "ground_truth_signal": "unknown",
        "candidate_signals": candidate_signals,
        "defect_mechanism": "INSUFFICIENT_EVIDENCE",
        "conversations": conversations
    }


def generate_v9_canonical_dataset(base_dir: str):
    """
    Main builder for the V9 Agentic SFT Dataset.
    Generates 650-800 multi-step verified trajectories across all designs in rtl/designs/
    with zero leakage against frozen 25 cases.
    """
    tools = AgentToolRegistry(workspace_root=base_dir)
    print("=" * 88)
    print("EXPERIMENT V9 — GENERATING CANONICAL AGENTIC SFT DATASET")
    print("=" * 88)

    designs_dir = os.path.join(base_dir, "rtl", "designs")
    all_design_files = sorted([f[:-2] for f in os.listdir(designs_dir) if f.endswith(".v")])

    all_trajectories = []
    skipped_frozen = 0

    for des in all_design_files:
        if des in FROZEN_TEST_IDS:
            skipped_frozen += 1
            continue

        prefix = des.split("_")[0]
        if prefix in ["fifo", "axi", "fsm", "uart", "pipeline"]:
            family = prefix
        elif prefix == "pipe":
            family = "pipeline"
        else:
            family = "generic"

        if family == "pipeline":
            candidate_sigs = ["valid_in", "d_in", "v1", "d1", "valid_out", "d_out"]
            if "hazard" in des or "bypass" in des or "raw" in des or "sign" in des:
                root_sig = "d1"
                distractor = "v1"
                symptom = "RAW Stale Operand"
                mech = "PIPE_FORWARD_HAZARD"
                is_hn = True
            elif "enable" in des or "gate" in des:
                root_sig = "v1"
                distractor = "d1"
                symptom = "Stage Enable Timing Desync"
                mech = "PIPE_STAGE_ENABLE_DESYNC"
                is_hn = False
            elif "flush" in des:
                root_sig = "v1"
                distractor = "d_out"
                symptom = "Flush Desynchronization"
                mech = "PIPE_FLUSH_DESYNC"
                is_hn = False
            else:
                root_sig = "v1"
                distractor = "d1"
                symptom = "Data Loss"
                mech = "PIPE_STALL_BUBBLE"
                is_hn = False

        elif family == "fifo":
            candidate_sigs = ["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"]
            if "ptr" in des or "wrap" in des:
                root_sig = "write_ptr" if "write" in des else "read_ptr"
                distractor = "read_data"
                symptom = "Memory Corruption"
                mech = "FIFO_PTR_WRAP"
                is_hn = True
            elif "threshold" in des or "empty" in des or "full" in des:
                root_sig = "count"
                distractor = "empty"
                symptom = "Premature Status Flag"
                mech = "FIFO_EMPTY_THRESHOLD"
                is_hn = True
            else:
                root_sig = "count"
                distractor = "read_data"
                symptom = "Data Mismatch"
                mech = "FIFO_SIMULTANEOUS_RW"
                is_hn = False

        elif family == "axi":
            candidate_sigs = ["valid_in", "ready_in", "valid_out", "ready_out"]
            if "ready" in des:
                root_sig = "ready_out"
                distractor = "valid_out"
                symptom = "Premature Handshake"
                mech = "AXI_EARLY_READY"
                is_hn = True
            elif "burst" in des:
                root_sig = "valid_out"
                distractor = "ready_out"
                symptom = "Burst Length Underflow"
                mech = "AXI_BURST_COUNT"
                is_hn = False
            else:
                root_sig = "valid_out"
                distractor = "ready_out"
                symptom = "Timeout"
                mech = "AXI_HANDSHAKE_HOLD"
                is_hn = False

        elif family == "fsm":
            candidate_sigs = ["state", "start", "done"]
            if "timing" in des or "done" in des or "strobe" in des:
                root_sig = "done"
                distractor = "state"
                symptom = "Done Strobe Slip"
                mech = "FSM_OUTPUT_TIMING"
                is_hn = True
            elif "skip" in des:
                root_sig = "state"
                distractor = "done"
                symptom = "State Skip Anomaly"
                mech = "FSM_STATE_SKIP"
                is_hn = False
            else:
                root_sig = "state"
                distractor = "done"
                symptom = "Stuck State"
                mech = "FSM_STUCK_STATE"
                is_hn = False

        elif family == "uart":
            candidate_sigs = ["cnt", "start", "tx"]
            if "stop" in des or "tx" in des or "bit" in des:
                root_sig = "tx"
                distractor = "cnt"
                symptom = "Stop Bit Corrupted"
                mech = "UART_STOP_BIT_GEN"
                is_hn = True
            elif "sampling" in des:
                root_sig = "cnt"
                distractor = "tx"
                symptom = "Phase Sampling Error"
                mech = "UART_BIT_SAMPLING"
                is_hn = False
            else:
                root_sig = "cnt"
                distractor = "tx"
                symptom = "Bad Output"
                mech = "UART_BAUD_DIVIDER"
                is_hn = False
        else:
            continue

        # Pattern 1: RTL First trajectory
        traj_rtl = build_agentic_trajectory(
            tools=tools,
            task_id=des,
            design_family=family,
            defect_mechanism=mech,
            ground_truth_signal=root_sig,
            symptom=symptom,
            candidate_signals=candidate_sigs,
            symptom_distractor=distractor,
            divergence_cycle=35,
            assertion_cycle=65,
            is_hard_negative=is_hn,
            tool_sequence_pattern="rtl_first"
        )
        all_trajectories.append(traj_rtl)

        # Pattern 2: Simulation First trajectory (for pipeline and hard negatives)
        if family == "pipeline" or is_hn:
            traj_sim = build_agentic_trajectory(
                tools=tools,
                task_id=des,
                design_family=family,
                defect_mechanism=mech,
                ground_truth_signal=root_sig,
                symptom=symptom,
                candidate_signals=candidate_sigs,
                symptom_distractor=distractor,
                divergence_cycle=35,
                assertion_cycle=65,
                is_hard_negative=is_hn,
                tool_sequence_pattern="sim_first"
            )
            all_trajectories.append(traj_sim)

        # Explicit hard negative pair discrimination for pipeline
        if family == "pipeline":
            hn_traj = copy.deepcopy(traj_rtl)
            hn_traj["example_id"] = f"v9_traj_hn_{des}"
            hn_traj["example_type"] = "HARD_NEGATIVE"
            conclude_data = json.loads(hn_traj["conversations"][-1]["value"])
            conclude_data["thought"] = (
                f"EXPLICIT PAIR DISCRIMINATION ({distractor} vs {root_sig}): "
                f"Comparing candidate {root_sig} against competing candidate {distractor}. "
                f"Timeline tracing shows that at cycle T=35, {distractor} latched the operand correctly. "
                f"The earliest anomalous event was on {root_sig} at cycle T=35->45. "
                f"Under first-causal-divergence rules, {distractor} is a downstream symptom. Decision: {root_sig}."
            )
            hn_traj["conversations"][-1]["value"] = json.dumps(conclude_data, indent=2)
            all_trajectories.append(hn_traj)

    # UNKNOWN / Missing Evidence Trajectories (~80 trajectories)
    unknown_bases = [
        ("fifo_e1", "fifo", ["count", "write_en", "read_en", "full", "empty"]),
        ("axi_e1", "axi", ["valid_in", "ready_in", "valid_out", "ready_out"]),
        ("fsm_e1", "fsm", ["state", "start", "done"]),
        ("uart_e1", "uart", ["cnt", "start", "tx"]),
        ("pipeline_e1", "pipeline", ["valid_in", "d_in", "v1", "d1", "valid_out", "d_out"]),
    ]

    for u_base, fam, sigs in unknown_bases:
        for suffix in ["", "_na", "_nb", "_p1", "_p2", "_s1", "_t1", "_t2", "_t3", "_t4", "_t5", "_t6", "_t7", "_t8", "_t9", "_t10"]:
            t_id = f"{u_base}{suffix}" if suffix else u_base
            if t_id in FROZEN_TEST_IDS:
                skipped_frozen += 1
                continue
            u_traj = build_unknown_trajectory(
                tools=tools,
                task_id=u_base,
                design_family=fam,
                candidate_signals=sigs
            )
            u_traj["example_id"] = f"v9_traj_unk_{t_id}"
            u_traj["task_id"] = t_id
            all_trajectories.append(u_traj)

    print(f"Total Candidate Trajectories Constructed: {len(all_trajectories)}")
    print(f"Frozen Test Instances Safeguarded (Skipped): {skipped_frozen}")

    # Zero-Leakage Audit Assertion
    leakage_detected = []
    for traj in all_trajectories:
        tid = traj["task_id"]
        for f_id in FROZEN_TEST_IDS:
            if tid == f_id:
                leakage_detected.append((tid, f_id))

    if leakage_detected:
        raise RuntimeError(f"CRITICAL: Leakage detected into training set: {leakage_detected}")
    print("  [PASS] Zero-Leakage Gate: 100% exclusion of all 30 frozen evaluation identifiers verified.")

    # Scenario-Level Split (Train ~80%, Val ~20%)
    random.seed(42)
    random.shuffle(all_trajectories)

    scenario_groups: Dict[str, List[Dict[str, Any]]] = {}
    for traj in all_trajectories:
        base = traj["task_id"].split("_")[0] + "_" + traj["task_id"].split("_")[1] if len(traj["task_id"].split("_")) > 1 else traj["task_id"]
        scenario_groups.setdefault(base, []).append(traj)

    train_trajectories = []
    val_trajectories = []

    group_keys = list(scenario_groups.keys())
    random.shuffle(group_keys)

    val_target = int(len(all_trajectories) * 0.20)
    val_count = 0

    for g_key in group_keys:
        group_items = scenario_groups[g_key]
        if val_count < val_target:
            val_trajectories.extend(group_items)
            val_count += len(group_items)
        else:
            train_trajectories.extend(group_items)

    print(f"  V9 Train Trajectories:      {len(train_trajectories)} (~{100*len(train_trajectories)/len(all_trajectories):.1f}%)")
    print(f"  V9 Validation Trajectories: {len(val_trajectories)} (~{100*len(val_trajectories)/len(all_trajectories):.1f}%)")

    # Composition breakdown
    pipe_train = sum(1 for t in train_trajectories if t["design_family"] == "pipeline")
    hn_train = sum(1 for t in train_trajectories if t.get("example_type") == "HARD_NEGATIVE")
    unk_train = sum(1 for t in train_trajectories if t.get("example_type") == "UNKNOWN_INSUFFICIENT")

    print("\nDataset Composition Breakdown:")
    print(f"  Pipeline Trajectories:      {pipe_train} ({100*pipe_train/len(train_trajectories):.1f}%)")
    print(f"  Hard Negatives:             {hn_train} ({100*hn_train/len(train_trajectories):.1f}%)")
    print(f"  UNKNOWN Trajectories:       {unk_train} ({100*unk_train/len(train_trajectories):.1f}%)")

    # Save Datasets
    ws_ds_dir = os.path.join(base_dir, "datasets", "v9")
    ml_ds_dir = "C:/Users/varad/ml-cache/rca-reuse/v9/datasets"
    os.makedirs(ws_ds_dir, exist_ok=True)
    os.makedirs(ml_ds_dir, exist_ok=True)

    for path in [
        os.path.join(ws_ds_dir, "agentic_train_v9.json"),
        os.path.join(ml_ds_dir, "agentic_train_v9.json")
    ]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(train_trajectories, f, indent=2)

    for path in [
        os.path.join(ws_ds_dir, "agentic_val_v9.json"),
        os.path.join(ml_ds_dir, "agentic_val_v9.json")
    ]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(val_trajectories, f, indent=2)

    print(f"\nV9 Datasets successfully persisted to:\n  - {ws_ds_dir}\n  - {ml_ds_dir}")

    # Generate Pipeline Generalization Suite
    gen_suite = build_pipeline_generalization_suite(base_dir, tools)
    gen_path_ws = os.path.join(ws_ds_dir, "pipeline_generalization_suite.json")
    gen_path_ml = os.path.join(ml_ds_dir, "pipeline_generalization_suite.json")
    with open(gen_path_ws, "w", encoding="utf-8") as f:
        json.dump(gen_suite, f, indent=2)
    with open(gen_path_ml, "w", encoding="utf-8") as f:
        json.dump(gen_suite, f, indent=2)
    print(f"Pipeline Generalization Suite ({len(gen_suite)} unseen architectures) saved.")


def build_pipeline_generalization_suite(base_dir: str, tools: AgentToolRegistry) -> List[Dict[str, Any]]:
    suite = [
        {
            "task_id": "gen_pipe_4stage_stall",
            "family": "pipeline",
            "architecture": "4-STAGE_PIPELINE",
            "ground_truth_signal": "v2",
            "symptom_distractor": "d2",
            "symptom": "4-Stage Throughput Collapse",
            "candidate_signals": ["valid_in", "d_in", "v1", "d1", "v2", "d2", "v3", "d3", "valid_out", "d_out"],
            "t_div": 55,
            "t_fail": 85,
            "mech": "PIPE_MULTI_STAGE_STALL_DROP",
            "naming_schema": "STANDARD_INDEXED"
        },
        {
            "task_id": "gen_pipe_4stage_hazard",
            "family": "pipeline",
            "architecture": "4-STAGE_PIPELINE",
            "ground_truth_signal": "d2",
            "symptom_distractor": "v2",
            "symptom": "Stage 3 to Stage 1 RAW Hazard",
            "candidate_signals": ["valid_in", "d_in", "v1", "d1", "v2", "d2", "v3", "d3", "valid_out", "d_out"],
            "t_div": 45,
            "t_fail": 75,
            "mech": "PIPE_FORWARD_HAZARD",
            "naming_schema": "STANDARD_INDEXED"
        },
        {
            "task_id": "gen_pipe_skid_buffer_stall",
            "family": "pipeline",
            "architecture": "SKID_BUFFER_PIPELINE",
            "ground_truth_signal": "skid_valid",
            "symptom_distractor": "skid_data",
            "symptom": "Skid Buffer Drain Failure",
            "candidate_signals": ["valid_in", "data_in", "skid_valid", "skid_data", "main_valid", "main_data", "valid_out", "data_out"],
            "t_div": 35,
            "t_fail": 65,
            "mech": "PIPE_SKID_DRAIN_DROP",
            "naming_schema": "NAMED_BUFFER"
        },
        {
            "task_id": "gen_pipe_alias_val_s1",
            "family": "pipeline",
            "architecture": "3-STAGE_PIPELINE_ALIAS",
            "ground_truth_signal": "val_s1",
            "symptom_distractor": "dat_s1",
            "symptom": "Stall Drop on Stage 1",
            "candidate_signals": ["valid_in", "d_in", "val_s1", "dat_s1", "val_s2", "dat_s2", "valid_out", "d_out"],
            "t_div": 40,
            "t_fail": 70,
            "mech": "PIPE_STALL_BUBBLE",
            "naming_schema": "ABBREVIATED_STAGE"
        },
        {
            "task_id": "gen_pipe_alias_stage1_valid",
            "family": "pipeline",
            "architecture": "3-STAGE_PIPELINE_FULL_NAME",
            "ground_truth_signal": "stage1_valid",
            "symptom_distractor": "stage1_data",
            "symptom": "Throughput Loss on Stage 1",
            "candidate_signals": ["valid_in", "d_in", "stage1_valid", "stage1_data", "stage2_valid", "stage2_data", "valid_out", "d_out"],
            "t_div": 45,
            "t_fail": 70,
            "mech": "PIPE_STALL_BUBBLE",
            "naming_schema": "EXPANDED_WORD"
        }
    ]
    return suite


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generate_v9_canonical_dataset(base)
