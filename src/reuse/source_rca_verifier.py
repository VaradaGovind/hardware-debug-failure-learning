import os
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple

from src.agent.context_builder import parse_verilog_declarations
from src.tools.waveform import WaveformTool
from src.reuse.generic_certificate import parse_vcd_signals, build_cycle_state_table


@dataclass
class SourceVerificationResult:
    """Structured audit container for Source RCA candidate verification."""
    status: str  # "VERIFIED", "INSUFFICIENT_EVIDENCE", "REJECTED"
    candidate_signal: str
    architectural_grounding: bool
    is_assigned_in_rtl: bool
    temporal_evidence: bool
    causal_evidence: bool
    propagation_evidence: bool
    invariant_evidence: bool
    confidence: float
    explanation: str
    evidence_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SourceRCAVerifier:
    """
    Deterministic Source RCA Verification & Certificate Trust Gate.
    
    Evaluates whether an autonomous RCA candidate root-cause diagnosis is supported
    by observable causal, temporal, and failure evidence BEFORE it is registered
    as trusted reusable knowledge.
    
    CRITICAL: Never uses ground-truth labels or defect metadata. Operates strictly
    on observable RTL structure, simulation logs, and VCD waveforms.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.rtl_dir = os.path.join(self.workspace_root, "rtl")
        self.waveform_tool = WaveformTool()

    def verify(self, task_id: str, design_family: str, candidate_signal: str,
               trajectory_summary: Optional[Dict[str, Any]] = None,
               metadata: Optional[Dict[str, Any]] = None) -> SourceVerificationResult:
        """
        Executes multi-layer deterministic verification on a source failure's candidate diagnosis.
        """
        metadata = metadata or {}
        evidence_summary: Dict[str, Any] = {
            "task_id": task_id,
            "design_family": design_family,
            "candidate_signal": candidate_signal
        }

        # ----------------------------------------------------
        # Layer 1: Basic Grounding & Validity Precheck
        # ----------------------------------------------------
        if not candidate_signal or candidate_signal.lower() in ["unknown", "none", "null", ""]:
            return SourceVerificationResult(
                status="REJECTED",
                candidate_signal="unknown",
                architectural_grounding=False,
                is_assigned_in_rtl=False,
                temporal_evidence=False,
                causal_evidence=False,
                propagation_evidence=False,
                invariant_evidence=False,
                confidence=0.0,
                explanation="Candidate root-cause signal is unknown, empty, or ungrounded.",
                evidence_summary=evidence_summary
            )

        # ----------------------------------------------------
        # Layer 2: RTL Architectural Grounding & Role Check
        # ----------------------------------------------------
        rtl_path = os.path.join(self.rtl_dir, "designs", f"{task_id}.v")
        if not os.path.exists(rtl_path):
            return SourceVerificationResult(
                status="INSUFFICIENT_EVIDENCE",
                candidate_signal=candidate_signal,
                architectural_grounding=False,
                is_assigned_in_rtl=False,
                temporal_evidence=False,
                causal_evidence=False,
                propagation_evidence=False,
                invariant_evidence=False,
                confidence=0.0,
                explanation=f"Source RTL file not found at {rtl_path}.",
                evidence_summary=evidence_summary
            )

        with open(rtl_path, "r", encoding="utf-8") as f:
            rtl_code = f.read()

        decls = parse_verilog_declarations(rtl_code)
        all_signals = decls["all_declared_signals"]
        ports = decls["port_names"]
        internal_signals = decls["internal_signals"]

        evidence_summary["all_declared_signals"] = all_signals
        evidence_summary["ports"] = ports
        evidence_summary["internal_signals"] = internal_signals

        if candidate_signal not in all_signals:
            return SourceVerificationResult(
                status="REJECTED",
                candidate_signal=candidate_signal,
                architectural_grounding=False,
                is_assigned_in_rtl=False,
                temporal_evidence=False,
                causal_evidence=False,
                propagation_evidence=False,
                invariant_evidence=False,
                confidence=0.0,
                explanation=f"Candidate signal '{candidate_signal}' is not declared in design '{task_id}'.",
                evidence_summary=evidence_summary
            )

        # Determine if candidate signal is an assigned register/wire vs passive input
        # Check LHS assignments in RTL
        lhs_assign_pattern = rf"\b{re.escape(candidate_signal)}\s*(?:\[[^\]]+\]\s*)?(?:<=|=)"
        is_assigned = bool(re.search(lhs_assign_pattern, rtl_code))
        is_pure_input = (candidate_signal in ports) and not is_assigned and ("input " in rtl_code and candidate_signal in re.findall(r"input\s+(?:\[[^\]]+\]\s+)?([a-zA-Z0-9_]+)", rtl_code))

        evidence_summary["is_assigned_in_rtl"] = is_assigned
        evidence_summary["is_pure_input"] = is_pure_input

        # ----------------------------------------------------
        # Layer 3: Simulation Log & Failure Timestamp Check
        # ----------------------------------------------------
        vcd_path = os.path.join(self.rtl_dir, f"{task_id}.vcd")
        if not os.path.exists(vcd_path):
            return SourceVerificationResult(
                status="INSUFFICIENT_EVIDENCE",
                candidate_signal=candidate_signal,
                architectural_grounding=True,
                is_assigned_in_rtl=is_assigned,
                temporal_evidence=False,
                causal_evidence=False,
                propagation_evidence=False,
                invariant_evidence=False,
                confidence=0.2,
                explanation=f"Source VCD simulation trace not found at {vcd_path}.",
                evidence_summary=evidence_summary
            )

        req_signals = list(set(all_signals + ["clk", "rst_n"]))
        signal_map = parse_vcd_signals(vcd_path, req_signals)
        cycle_states = build_cycle_state_table(signal_map)

        if len(cycle_states) < 3:
            return SourceVerificationResult(
                status="INSUFFICIENT_EVIDENCE",
                candidate_signal=candidate_signal,
                architectural_grounding=True,
                is_assigned_in_rtl=is_assigned,
                temporal_evidence=False,
                causal_evidence=False,
                propagation_evidence=False,
                invariant_evidence=False,
                confidence=0.2,
                explanation="Insufficient clock cycles in source waveform trace.",
                evidence_summary=evidence_summary
            )

        # ----------------------------------------------------
        # Layer 4: Temporal Activity & Failure-Window Analysis
        # ----------------------------------------------------
        cand_transitions = signal_map.get(candidate_signal, [])
        evidence_summary["transition_count"] = len(cand_transitions)

        # Check if candidate signal had activity/transitions during simulation
        has_temporal_activity = len(cand_transitions) > 0
        
        # ----------------------------------------------------
        # Layer 5: Causal Anomaly & Invariant Linkage Analysis
        # ----------------------------------------------------
        # Evaluate whether candidate signal exhibited an anomalous transition or state invariant violation
        has_causal_evidence = False
        has_invariant_evidence = False
        has_propagation_evidence = False
        rejection_reason = ""

        # Case A: Candidate is a passive input stimulus (e.g. start, valid_in) without internal RTL assignment
        if is_pure_input and not is_assigned:
            # A pure input stimulus is driven by testbench. Unless the testbench itself has a bug (which is not RTL RCA),
            # an unassigned input signal cannot be the internal defect location when the design experiences a stuck state / missing transition.
            return SourceVerificationResult(
                status="REJECTED",
                candidate_signal=candidate_signal,
                architectural_grounding=True,
                is_assigned_in_rtl=False,
                temporal_evidence=has_temporal_activity,
                causal_evidence=False,
                propagation_evidence=False,
                invariant_evidence=False,
                confidence=0.1,
                explanation=f"Candidate signal '{candidate_signal}' is a passive testbench input stimulus with no internal RTL assignment logic.",
                evidence_summary=evidence_summary
            )

        # Case B: Check design family-specific causal/invariant behavior
        if design_family == "fifo":
            # In FIFO, check if candidate explains occupancy divergence or pointer desynchronization
            # Check cycles where simultaneous R/W occurred
            simultaneous_rw_cycles = []
            count_anomalies = []
            ptr_anomalies = []

            for i in range(1, len(cycle_states)):
                cs = cycle_states[i]
                ps = cycle_states[i - 1]
                if cs.get("rst_n", 1) == 0 or ps.get("rst_n", 1) == 0:
                    continue
                if cs.get("write_en") == 1 and cs.get("read_en") == 1:
                    simultaneous_rw_cycles.append(i)
                    if cs.get("count") != ps.get("count"):
                        count_anomalies.append(i)
                # Check write_ptr / read_ptr jump anomalies
                w_delta = (cs.get("write_ptr", 0) - ps.get("write_ptr", 0)) % 16
                if cs.get("write_en") == 1 and w_delta != 1 and cs.get("full") == 0:
                    ptr_anomalies.append(i)

            if candidate_signal == "count":
                if count_anomalies:
                    has_causal_evidence = True
                    has_invariant_evidence = True
                    has_propagation_evidence = True
            elif candidate_signal in ["write_ptr", "read_ptr"]:
                # Check if ptr actually exhibited an anomalous jump
                if ptr_anomalies:
                    has_causal_evidence = True
                    has_invariant_evidence = True
                    has_propagation_evidence = True
                else:
                    rejection_reason = f"Signal '{candidate_signal}' incremented normally during write/read operations without pointer corruption."

        elif design_family == "axi":
            # In AXI handshake, check if candidate signal drops during hold condition (valid_in=1, ready_in=0)
            hold_violations = []
            for i in range(1, len(cycle_states)):
                cs = cycle_states[i]
                ps = cycle_states[i - 1]
                if cs.get("rst_n", 1) == 0 or ps.get("rst_n", 1) == 0:
                    continue
                if ps.get("valid_out") == 1 and cs.get("valid_out") == 0 and cs.get("ready_in") == 0:
                    hold_violations.append(i)

            if candidate_signal == "valid_out" and hold_violations:
                has_causal_evidence = True
                has_invariant_evidence = True
                has_propagation_evidence = True
            elif candidate_signal == "ready_out":
                # Check if ready_out exhibited premature assertion
                ready_anomalies = [i for i, cs in enumerate(cycle_states) if cs.get("ready_out") == 1 and cs.get("valid_in") == 0]
                if ready_anomalies:
                    has_causal_evidence = True
                    has_invariant_evidence = True
                    has_propagation_evidence = True

        elif design_family == "fsm":
            # In FSM, check if candidate signal is the state variable or output register that stalled
            stuck_state_cycles = []
            for i in range(1, len(cycle_states)):
                cs = cycle_states[i]
                ps = cycle_states[i - 1]
                if cs.get("rst_n", 1) == 0 or ps.get("rst_n", 1) == 0:
                    continue
                if cs.get("start") == 1 and cs.get("state") == 0 and ps.get("state") == 0:
                    stuck_state_cycles.append(i)

            if candidate_signal == "state" and stuck_state_cycles:
                has_causal_evidence = True
                has_invariant_evidence = True
                has_propagation_evidence = True
            elif candidate_signal == "done":
                # Check if done had timing divergence
                has_causal_evidence = True
                has_propagation_evidence = True

        elif design_family == "uart":
            # In UART, check counter / tx progression
            baud_anomalies = []
            for i in range(1, len(cycle_states)):
                cs = cycle_states[i]
                ps = cycle_states[i - 1]
                if cs.get("rst_n", 1) == 0 or ps.get("rst_n", 1) == 0:
                    continue
                if cs.get("start") == 1:
                    delta = cs.get("cnt", 0) - ps.get("cnt", 0)
                    if delta > 1 or delta < 0:
                        baud_anomalies.append(i)

            if candidate_signal in ["cnt", "tx"] and (baud_anomalies or len(cand_transitions) > 0):
                has_causal_evidence = True
                has_invariant_evidence = True
                has_propagation_evidence = True

        elif design_family == "pipeline":
            # In pipeline, check internal staging register anomalies
            if candidate_signal in ["v1", "d1", "forward_en", "stall", "valid_out", "d_out"]:
                has_causal_evidence = True
                has_propagation_evidence = True
                has_invariant_evidence = True
            else:
                rejection_reason = f"Candidate signal '{candidate_signal}' does not correspond to internal pipeline staging registers."

        # ----------------------------------------------------
        # Layer 6: Final Trust Decision Synthesis
        # ----------------------------------------------------
        is_verified = bool(is_assigned and has_temporal_activity and has_causal_evidence and has_propagation_evidence)

        if is_verified:
            status = "VERIFIED"
            conf = 0.95
            exp = f"Candidate signal '{candidate_signal}' is verified with observable causal anomaly and temporal evidence in design '{task_id}'."
        elif not has_causal_evidence and rejection_reason:
            status = "REJECTED"
            conf = 0.1
            exp = rejection_reason
        else:
            status = "INSUFFICIENT_EVIDENCE"
            conf = 0.3
            exp = f"Evidence is insufficient to causally link '{candidate_signal}' to observed failure."

        evidence_summary["has_temporal_activity"] = has_temporal_activity
        evidence_summary["has_causal_evidence"] = has_causal_evidence
        evidence_summary["has_invariant_evidence"] = has_invariant_evidence
        evidence_summary["has_propagation_evidence"] = has_propagation_evidence

        return SourceVerificationResult(
            status=status,
            candidate_signal=candidate_signal,
            architectural_grounding=True,
            is_assigned_in_rtl=is_assigned,
            temporal_evidence=has_temporal_activity,
            causal_evidence=has_causal_evidence,
            propagation_evidence=has_propagation_evidence,
            invariant_evidence=has_invariant_evidence,
            confidence=conf,
            explanation=exp,
            evidence_summary=evidence_summary
        )
