import os
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from src.tools.simulator import VerilogSimulator
from src.tools.waveform import WaveformTool


@dataclass
class RCAContext:
    """Structured deterministic hardware RCA evidence package with temporal waveform context."""
    task_id: str
    design_family: str
    module_name: str
    observed_symptom: str
    initiating_event: str
    ports: List[str]
    internal_signals: List[str]
    all_declared_signals: List[str]
    candidate_signals: List[str]
    rtl_code: str
    simulation_log: str
    failing_assertion: str
    failure_timestamp: int = 0
    temporal_waveform_summary: str = ""
    waveform_summary: Dict[str, Any] = field(default_factory=dict)
    char_length: int = 0


def parse_verilog_declarations(verilog_code: str) -> Dict[str, Any]:
    """Deterministically extracts module name, declared ports, and internal signals."""
    mod_match = re.search(r"module\s+([a-zA-Z0-9_]+)\s*\((.*?)\);", verilog_code, re.DOTALL)
    mod_name = mod_match.group(1) if mod_match else "unknown_module"
    ports_str = mod_match.group(2) if mod_match else ""
    
    ports = []
    port_names = []
    for p in ports_str.split(","):
        p_clean = p.strip()
        if p_clean:
            ports.append(p_clean)
            # Extract bare signal name (last token)
            tokens = p_clean.split()
            if tokens:
                sig = tokens[-1].strip().strip(";[]")
                if sig:
                    port_names.append(sig)
            
    # Extract internal reg/wire declarations
    internal_sigs = []
    for m in re.finditer(r"(reg|wire)\s+(\[[^\]]+\]\s+)?([a-zA-Z0-9_,\s]+);", verilog_code):
        sig_names = m.group(3).split(",")
        for s in sig_names:
            s_clean = s.strip()
            if s_clean and s_clean not in internal_sigs and s_clean not in port_names:
                internal_sigs.append(s_clean)
                
    all_sigs = list(dict.fromkeys(port_names + internal_sigs))
    
    return {
        "module_name": mod_name,
        "ports": ports,
        "port_names": port_names,
        "internal_signals": internal_sigs,
        "all_declared_signals": all_sigs
    }


def build_rca_context(task_id: str, design_family: str, metadata: Dict[str, Any],
                      workspace_root: str) -> RCAContext:
    """
    Deterministically builds a compact, observable-only hardware RCA context package
    containing static RTL evidence and dynamic temporal waveform evidence.
    Strictly excludes ground-truth labels and evaluation-only fields.
    """
    rtl_dir = os.path.join(workspace_root, "rtl")
    designs_dir = os.path.join(rtl_dir, "designs")
    rtl_path = os.path.join(designs_dir, f"{task_id}.v")

    rtl_code = ""
    if os.path.exists(rtl_path):
        with open(rtl_path, "r", encoding="utf-8") as f:
            rtl_code = f.read().strip()

    parsed = parse_verilog_declarations(rtl_code)
    
    # Run simulation to extract observable assertion failure log & failure timestamp
    sim = VerilogSimulator(rtl_dir)
    sim_res = sim.run_simulation(task_id, design_family)
    raw_log = sim_res.get("output", "") + "\n" + sim_res.get("error", "")
    
    # Extract failing assertion line
    failing_assertion = ""
    for line in raw_log.splitlines():
        if "FAIL:" in line or "Assertion failed" in line or "Error:" in line:
            failing_assertion = line.strip()
            break

    # Extract failure timestamp
    finish_m = re.search(r"\$finish called at (\d+)", raw_log)
    failure_timestamp = int(finish_m.group(1)) if finish_m else 100

    # Concise simulation log
    log_lines = [l.strip() for l in raw_log.splitlines() if l.strip()]
    concise_log = "\n".join(log_lines[-4:]) if log_lines else "Simulation completed without assertion logs."

    # Extract dynamic chronological waveform transitions
    waveform_summary: Dict[str, Any] = {}
    temporal_transitions_lines: List[str] = []
    vcd_path = os.path.join(rtl_dir, f"{task_id}.vcd")
    
    if os.path.exists(vcd_path):
        try:
            wt = WaveformTool()
            q_sigs = parsed["all_declared_signals"]
            w_res = wt.query_waveform(vcd_path, q_sigs, start_time=0, end_time=failure_timestamp)
            data = w_res.get("data", {})
            waveform_summary = {k: len(v) for k, v in data.items()}
            
            temporal_transitions_lines.append(f"Simulation Failure Timestamp: T={failure_timestamp}")
            temporal_transitions_lines.append("Chronological Signal Transitions (Leading up to Failure Timestamp):")
            
            for sig in q_sigs:
                if sig in ["clk", "rst_n"]:
                    continue
                trans = data.get(sig, [])
                if trans:
                    # Keep last 5 transitions leading up to failure
                    t_str = " -> ".join([f"T={t}: {v}" for t, v in trans[-5:]])
                    temporal_transitions_lines.append(f"  - {sig:<12}: {t_str}")
                else:
                    temporal_transitions_lines.append(f"  - {sig:<12}: (constant / no transitions in window)")
        except Exception as e:
            temporal_transitions_lines.append(f"Waveform query unavailable: {str(e)}")

    temporal_waveform_summary = "\n".join(temporal_transitions_lines)

    symptom = metadata.get("symptom", "ASSERTION_VIOLATION")
    init_event = metadata.get("initiating_event", "RESET_DEASSERTION")

    # Candidates: all declared signals excluding clk and rst_n
    candidate_sigs = [s for s in parsed["all_declared_signals"] if s not in ["clk", "rst_n"]]

    context = RCAContext(
        task_id=task_id,
        design_family=design_family,
        module_name=parsed["module_name"],
        observed_symptom=symptom,
        initiating_event=init_event,
        ports=parsed["ports"],
        internal_signals=parsed["internal_signals"],
        all_declared_signals=parsed["all_declared_signals"],
        candidate_signals=candidate_sigs,
        rtl_code=rtl_code,
        simulation_log=concise_log,
        failing_assertion=failing_assertion,
        failure_timestamp=failure_timestamp,
        temporal_waveform_summary=temporal_waveform_summary,
        waveform_summary=waveform_summary,
        char_length=len(rtl_code) + len(concise_log) + len(temporal_waveform_summary)
    )

    validate_context_no_leakage(context)
    return context


def validate_context_no_leakage(context: RCAContext) -> None:
    """
    Automated check verifying that the context package contains ZERO ground truth leakage.
    Fails if hidden benchmark labels or answers are detected.
    """
    forbidden_keys = [
        "ground_truth_signal",
        "ground_truth_signals",
        "defect_mechanism",
        "is_source_manifestation",
        "ground_truth_match"
    ]
    
    # Check context object attributes
    for k in forbidden_keys:
        if hasattr(context, k):
            raise AssertionError(f"DATA LEAKAGE ERROR: RCAContext contains forbidden attribute '{k}'")

    # Check text fields for raw leak phrases
    text_content = f"{context.observed_symptom} {context.simulation_log} {context.failing_assertion} {context.temporal_waveform_summary}"
    for k in ["ground_truth_signal", "defect_mechanism"]:
        if k in text_content.lower():
            raise AssertionError(f"DATA LEAKAGE ERROR: Context text contains forbidden keyword '{k}'")


def format_rca_context_prompt(context: RCAContext) -> str:
    """
    Formats the structured RCAContext into an evidence-rich prompt
    clearly separating static RTL structure from dynamic temporal waveform behavior.
    """
    ports_formatted = ", ".join(context.ports) if context.ports else "None declared"
    internals_formatted = ", ".join(context.internal_signals) if context.internal_signals else "None"
    candidate_list = ", ".join(context.candidate_signals) if context.candidate_signals else "None"
    
    prompt = (
        f"=== HARDWARE ROOT CAUSE ANALYSIS INVESTIGATION: {context.task_id} ===\n"
        f"Design Family: {context.design_family}\n"
        f"Target Module: {context.module_name}\n"
        f"Observed Symptom: {context.observed_symptom}\n"
        f"Initiating Event: {context.initiating_event}\n\n"
        f"=== SECTION A: STATIC RTL EVIDENCE ===\n"
        f"Declared Ports: {ports_formatted}\n"
        f"Internal Signals: {internals_formatted}\n"
        f"Verilog Source Code:\n"
        f"```verilog\n"
        f"{context.rtl_code}\n"
        f"```\n\n"
        f"=== SECTION B: DYNAMIC SIMULATION & TEMPORAL WAVEFORM EVIDENCE ===\n"
        f"Simulation Assertion Log:\n{context.simulation_log}\n\n"
        f"Waveform Activity:\n{context.temporal_waveform_summary}\n\n"
        f"=== CANDIDATE SIGNALS ===\n"
        f"[{candidate_list}]\n\n"
        f"CRITICAL CAUSAL ANALYSIS INSTRUCTIONS:\n"
        f"1. Cross-reference the RTL logic against the chronological waveform transitions.\n"
        f"2. Trace which signal exhibited the FIRST abnormal transition or failed to update as required by RTL logic.\n"
        f"3. Distinguish upstream root causes from downstream symptom signals.\n"
        f"4. 'candidate_signal' MUST be chosen from [{candidate_list}] or 'unknown'.\n"
        f"5. Provide a 3-step causal chain explaining: initiating condition -> anomalous signal behavior -> assertion failure."
    )
    return prompt


def format_agentic_initial_context(context: RCAContext) -> str:
    """
    Formats the initial observation state for multi-turn tool-assisted agentic RCA.
    Contains failure symptoms, simulation assertion logs, and candidate signal list,
    requiring the agent to invoke tools to inspect RTL and waveform transitions.
    """
    ports_formatted = ", ".join(context.ports) if context.ports else "None declared"
    internals_formatted = ", ".join(context.internal_signals) if context.internal_signals else "None"
    candidate_list = ", ".join(context.candidate_signals) if context.candidate_signals else "None"

    prompt = (
        f"=== HARDWARE ROOT CAUSE ANALYSIS INVESTIGATION: {context.task_id} ===\n"
        f"Design Family: {context.design_family}\n"
        f"Target Module: {context.module_name}\n"
        f"Observed Symptom: {context.observed_symptom}\n"
        f"Initiating Event: {context.initiating_event}\n\n"
        f"Simulation Assertion Log:\n{context.simulation_log}\n\n"
        f"Declared Signals: [{ports_formatted}, {internals_formatted}]\n"
        f"Candidate Signals: [{candidate_list}]\n\n"
        f"Instructions: You must investigate this failure using your verification tools step-by-step (e.g. read_rtl_file, get_waveform_summary) before concluding."
    )
    return prompt
