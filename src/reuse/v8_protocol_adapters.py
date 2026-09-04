import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

from .v8_semantic_roles import HardwareRole, SemanticRoleNormalizer
from .v8_unified_certificate import (
    V8UnifiedCertificate, RootCauseIdentity, FailureMechanism,
    TemporalBehavior, EvidenceArtifact, RejectedAlternative,
    TrustAuditMetadata, HardwareInvariant, ProtocolObligationSpec,
    CertificateTrustStatus, CausalRelation
)


class BaseProtocolAdapter(ABC):
    """Abstract base class for modular hardware protocol adapters."""

    @property
    @abstractmethod
    def family_name(self) -> str:
        """Name of the hardware design family."""
        pass

    @abstractmethod
    def extract_certificate_specs(self, source_id: str,
                                  defect_desc: str,
                                  symptom: str,
                                  signals: List[str],
                                  root_sig: str,
                                  confidence: float,
                                  rtl_context: Optional[str] = None) -> V8UnifiedCertificate:
        """Constructs a complete V8UnifiedCertificate for this protocol."""
        pass

    @abstractmethod
    def validate_target(self, cert: V8UnifiedCertificate,
                        cycle_states: List[Dict[str, Any]],
                        signal_role_map: Dict[str, HardwareRole]) -> Dict[str, Any]:
        """
        Executes formal invariant, protocol obligation, and temporal causality validation
        on target cycle states using normalized roles.
        """
        pass


class FifoProtocolAdapter(BaseProtocolAdapter):
    """Adapter for Synchronous and Asynchronous FIFOs."""

    @property
    def family_name(self) -> str:
        return "fifo"

    def extract_certificate_specs(self, source_id: str, defect_desc: str,
                                  symptom: str, signals: List[str],
                                  root_sig: str, confidence: float,
                                  rtl_context: Optional[str] = None) -> V8UnifiedCertificate:
        rc_role, rc_class = SemanticRoleNormalizer.normalize_signal(root_sig, design_family="fifo")
        rc = RootCauseIdentity(
            signal_name=root_sig,
            normalized_role=rc_role,
            module_name="fifo",
            role_class=rc_class
        )

        obl = ProtocolObligationSpec(
            obligation_name="OCCUPANCY_CONSERVATION",
            precondition={"write_en": 1, "read_en": 1},
            required_postcondition={"count_delta": 0},
            violation_signature={"count_delta_nonzero": 1},
            latency_cycles=1
        )

        mech = FailureMechanism(
            violated_invariant=HardwareInvariant.OCCUPANCY_CONSERVATION,
            protocol_obligation=obl,
            causal_mechanism_name="FIFO_SIMULTANEOUS_RW_COUNTER_CORRUPTION",
            upstream_antecedent=root_sig,
            downstream_symptom=symptom,
            causal_relation=CausalRelation.ROOT_CAUSE_ANTECEDENT
        )

        temp = TemporalBehavior(
            initiating_event={"write_en": 1, "read_en": 1},
            trigger_condition={"write_en": 1, "read_en": 1},
            active_window_cycles=6,
            min_settlement_cycles=2,
            max_observation_budget=16
        )

        ev = EvidenceArtifact(
            testbench_assertion_message=symptom,
            supporting_observations=[f"Abnormal occupancy delta on '{root_sig}' during simultaneous read/write"]
        )

        alts = [
            RejectedAlternative(candidate_signal="empty", normalized_role=HardwareRole.OUTPUT_STROBE,
                                rejection_rationale="Spurious empty flag is a downstream symptom of corrupted occupancy counter", is_downstream_symptom=True),
            RejectedAlternative(candidate_signal="read_data", normalized_role=HardwareRole.DATA_OUTPUT,
                                rejection_rationale="Read data corruption is downstream of premature empty flag assertion", is_downstream_symptom=True)
        ]

        return V8UnifiedCertificate(
            certificate_id=f"V8_CERT_FIFO_{source_id.upper()}",
            source_case_id=source_id,
            design_family="fifo",
            root_cause=rc,
            mechanism=mech,
            temporal=temp,
            evidence=ev,
            rejected_alternatives=alts,
            target_signals=signals
        )

    def validate_target(self, cert: V8UnifiedCertificate,
                        cycle_states: List[Dict[str, Any]],
                        signal_role_map: Dict[str, HardwareRole]) -> Dict[str, Any]:
        # Identify occupancy tracker and enable signals using roles
        occ_sig = None
        wr_sig = None
        rd_sig = None

        for sig, role in signal_role_map.items():
            if role == HardwareRole.OCCUPANCY_TRACKER:
                occ_sig = sig
            elif "write_en" in sig.lower() or "wr_en" in sig.lower():
                wr_sig = sig
            elif "read_en" in sig.lower() or "rd_en" in sig.lower():
                rd_sig = sig

        occ_sig = occ_sig or "count"
        wr_sig = wr_sig or "write_en"
        rd_sig = rd_sig or "read_en"

        simult_rw_cycles = []
        for i in range(1, len(cycle_states)):
            s = cycle_states[i]
            if s.get("rst_n", 1) == 0:
                continue
            if s.get(wr_sig) == 1 and s.get(rd_sig) == 1:
                simult_rw_cycles.append(i)

        if not simult_rw_cycles:
            return {
                "decision": "INSUFFICIENT_EVIDENCE",
                "stage": "TRIGGER",
                "reason": f"Concurrent read/write trigger condition ({wr_sig}=1, {rd_sig}=1) was not exercised."
            }

        # Check occupancy conservation invariant: delta must match the defect signature (anomaly delta == 1)
        anomaly_cycles = []
        for c in simult_rw_cycles:
            curr_s = cycle_states[c]
            prev_s = cycle_states[c - 1]
            c_curr = curr_s.get(occ_sig)
            c_prev = prev_s.get(occ_sig)
            if c_curr is not None and c_prev is not None:
                delta = c_curr - c_prev
                if delta == 1:
                    anomaly_cycles.append(c)

        if not anomaly_cycles:
            return {
                "decision": "FAIL",
                "stage": "STATE_INVARIANT",
                "reason": f"Expected state invariant anomaly (CONSERVATION on '{occ_sig}' with delta=+1) was not observed in waveform."
            }

        # Check causal propagation: downstream divergence
        first_violation = min(anomaly_cycles)
        desync_cycles = []
        for k in range(first_violation, len(cycle_states)):
            s = cycle_states[k]
            w_p = s.get("write_ptr", 0)
            r_p = s.get("read_ptr", 0)
            c_val = s.get(occ_sig, 0)
            if c_val != ((w_p - r_p) % 16):
                desync_cycles.append(k)

        if not desync_cycles:
            return {
                "decision": "FAIL",
                "stage": "PROPAGATION",
                "reason": f"Occupancy violation detected on '{occ_sig}', but downstream causal propagation desync was not observed."
            }

        return {
            "decision": "PASS",
            "stage": "FULL_SEMANTIC",
            "matched_root_cause": occ_sig,
            "reason": f"Occupancy conservation violation verified on '{occ_sig}' with downstream causal propagation."
        }


class AxiProtocolAdapter(BaseProtocolAdapter):
    """Adapter for AXI4-Lite Handshake Protocols."""

    @property
    def family_name(self) -> str:
        return "axi"

    def extract_certificate_specs(self, source_id: str, defect_desc: str,
                                  symptom: str, signals: List[str],
                                  root_sig: str, confidence: float,
                                  rtl_context: Optional[str] = None) -> V8UnifiedCertificate:
        rc_role, rc_class = SemanticRoleNormalizer.normalize_signal(root_sig, design_family="axi")
        rc = RootCauseIdentity(
            signal_name=root_sig,
            normalized_role=rc_role,
            module_name="axi",
            role_class=rc_class
        )

        obl = ProtocolObligationSpec(
            obligation_name="HANDSHAKE_DATA_STABILITY",
            precondition={"valid_out": 1, "ready_in": 0},
            required_postcondition={"valid_out_held": 1},
            violation_signature={"valid_out_dropped": 0},
            latency_cycles=1
        )

        mech = FailureMechanism(
            violated_invariant=HardwareInvariant.HANDSHAKE_STABILITY,
            protocol_obligation=obl,
            causal_mechanism_name="AXI_HANDSHAKE_HOLD_VIOLATION",
            upstream_antecedent=root_sig,
            downstream_symptom=symptom,
            causal_relation=CausalRelation.ROOT_CAUSE_ANTECEDENT
        )

        temp = TemporalBehavior(
            initiating_event={"valid_out": 1},
            trigger_condition={"valid_out": 1, "ready_in": 0},
            active_window_cycles=4,
            min_settlement_cycles=2
        )

        ev = EvidenceArtifact(
            testbench_assertion_message=symptom,
            supporting_observations=["Premature deassertion of valid_out before ready_in handshake acknowledged"]
        )

        alts = [
            RejectedAlternative(candidate_signal="ready_in", normalized_role=HardwareRole.HANDSHAKE_READY,
                                rejection_rationale="Slave ready backpressure is an input stimuli condition, not internal root cause"),
            RejectedAlternative(candidate_signal="ready_out", normalized_role=HardwareRole.HANDSHAKE_READY,
                                rejection_rationale="Downstream ready signal is not the causal initiator of the hold drop")
        ]

        return V8UnifiedCertificate(
            certificate_id=f"V8_CERT_AXI_{source_id.upper()}",
            source_case_id=source_id,
            design_family="axi",
            root_cause=rc,
            mechanism=mech,
            temporal=temp,
            evidence=ev,
            rejected_alternatives=alts,
            target_signals=signals
        )

    def validate_target(self, cert: V8UnifiedCertificate,
                        cycle_states: List[Dict[str, Any]],
                        signal_role_map: Dict[str, HardwareRole]) -> Dict[str, Any]:
        # Role-based mapping
        v_out = "valid_out"
        r_in = "ready_in"

        for sig, role in signal_role_map.items():
            if role == HardwareRole.HANDSHAKE_VALID and ("out" in sig.lower() or "m_" in sig.lower() or "tx" in sig.lower()):
                v_out = sig
            elif role == HardwareRole.HANDSHAKE_READY and ("in" in sig.lower() or "s_" in sig.lower() or "rx" in sig.lower()):
                r_in = sig

        hold_violations = []
        for i in range(1, len(cycle_states)):
            prev_s = cycle_states[i - 1]
            curr_s = cycle_states[i]
            if prev_s.get("rst_n", 1) == 0:
                continue

            # Handshake stability rule: V asserted and dropped while R is low (V5 invariant)
            if prev_s.get(v_out) == 1 and curr_s.get(v_out) == 0 and curr_s.get(r_in) == 0:
                hold_violations.append(i)

        if not hold_violations:
            return {
                "decision": "FAIL",
                "stage": "PROTOCOL_OBLIGATION",
                "reason": f"AXI Handshake stability was preserved; '{v_out}' did not drop prematurely while '{r_in}' was low."
            }

        return {
            "decision": "PASS",
            "stage": "FULL_SEMANTIC",
            "matched_root_cause": v_out,
            "reason": f"AXI Handshake hold violation confirmed on '{v_out}' dropping before '{r_in}' handshake completion."
        }


class FsmProtocolAdapter(BaseProtocolAdapter):
    """Adapter for Finite State Machines."""

    @property
    def family_name(self) -> str:
        return "fsm"

    def extract_certificate_specs(self, source_id: str, defect_desc: str,
                                  symptom: str, signals: List[str],
                                  root_sig: str, confidence: float,
                                  rtl_context: Optional[str] = None) -> V8UnifiedCertificate:
        rc_role, rc_class = SemanticRoleNormalizer.normalize_signal(root_sig, design_family="fsm")
        rc = RootCauseIdentity(
            signal_name=root_sig,
            normalized_role=rc_role,
            module_name="fsm",
            role_class=rc_class
        )

        obl = ProtocolObligationSpec(
            obligation_name="STATE_TRANSITION_OBLIGATION",
            precondition={"start": 1},
            required_postcondition={"state_progresses": 1},
            violation_signature={"stuck_state": 0},
            latency_cycles=1
        )

        mech = FailureMechanism(
            violated_invariant=HardwareInvariant.STATE_TRANSITION_DEADLOCK,
            protocol_obligation=obl,
            causal_mechanism_name="FSM_STUCK_STATE_DEADLOCK",
            upstream_antecedent=root_sig,
            downstream_symptom=symptom,
            causal_relation=CausalRelation.ROOT_CAUSE_ANTECEDENT
        )

        temp = TemporalBehavior(
            initiating_event={"start": 1},
            trigger_condition={"start": 1},
            active_window_cycles=4
        )

        ev = EvidenceArtifact(
            testbench_assertion_message=symptom,
            supporting_observations=["FSM failed to transition from initial state despite active start pulse"]
        )

        alts = [
            RejectedAlternative(candidate_signal="done", normalized_role=HardwareRole.OUTPUT_STROBE,
                                rejection_rationale="Absence of 'done' pulse is downstream consequence of FSM state deadlock", is_downstream_symptom=True)
        ]

        return V8UnifiedCertificate(
            certificate_id=f"V8_CERT_FSM_{source_id.upper()}",
            source_case_id=source_id,
            design_family="fsm",
            root_cause=rc,
            mechanism=mech,
            temporal=temp,
            evidence=ev,
            rejected_alternatives=alts,
            target_signals=signals
        )

    def validate_target(self, cert: V8UnifiedCertificate,
                        cycle_states: List[Dict[str, Any]],
                        signal_role_map: Dict[str, HardwareRole]) -> Dict[str, Any]:
        state_sig = "state"
        start_sig = "start"

        for sig, role in signal_role_map.items():
            if role == HardwareRole.STATE_REGISTER:
                state_sig = sig
            elif "start" in sig.lower():
                start_sig = sig

        start_cycles = [i for i, s in enumerate(cycle_states) if s.get(start_sig) == 1 and s.get("rst_n", 1) == 1]
        if not start_cycles:
            return {
                "decision": "INSUFFICIENT_EVIDENCE",
                "stage": "TRIGGER",
                "reason": f"FSM trigger condition ({start_sig}=1) was not exercised in waveform."
            }

        deadlock_detected = False
        for c in start_cycles:
            if c + 1 < len(cycle_states):
                curr_state = cycle_states[c].get(state_sig)
                next_state = cycle_states[c + 1].get(state_sig)
                if curr_state == 0 and next_state == 0:
                    deadlock_detected = True
                    break

        if not deadlock_detected:
            return {
                "decision": "FAIL",
                "stage": "STATE_INVARIANT",
                "reason": f"FSM transitioned normally away from state 0 upon '{start_sig}' assertion; defect absent."
            }

        return {
            "decision": "PASS",
            "stage": "FULL_SEMANTIC",
            "matched_root_cause": state_sig,
            "reason": f"FSM state transition deadlock confirmed on '{state_sig}' remaining stuck in state 0."
        }


class UartProtocolAdapter(BaseProtocolAdapter):
    """
    Native Modular Adapter for UART Transmitters/Receivers.
    Models bit period prescaler timing, baud rollover contracts, and framing alignment.
    """

    @property
    def family_name(self) -> str:
        return "uart"

    def extract_certificate_specs(self, source_id: str, defect_desc: str,
                                  symptom: str, signals: List[str],
                                  root_sig: str, confidence: float,
                                  rtl_context: Optional[str] = None) -> V8UnifiedCertificate:
        rc_role, rc_class = SemanticRoleNormalizer.normalize_signal(root_sig, design_family="uart")
        rc = RootCauseIdentity(
            signal_name=root_sig,
            normalized_role=rc_role,
            module_name="uart",
            role_class=rc_class
        )

        obl = ProtocolObligationSpec(
            obligation_name="BAUD_RATE_PRESCALER_PERIOD",
            precondition={"tx": 0},  # start bit transition
            required_postcondition={"bit_period_preserved": 1},
            violation_signature={"baud_counter_drift": 1},
            latency_cycles=8
        )

        mech = FailureMechanism(
            violated_invariant=HardwareInvariant.BAUD_PERIODIC_ROLLOVER,
            protocol_obligation=obl,
            causal_mechanism_name="UART_BAUD_DIVIDER_TIMING_DRIFT",
            upstream_antecedent=root_sig,
            downstream_symptom=symptom,
            causal_relation=CausalRelation.ROOT_CAUSE_ANTECEDENT
        )

        temp = TemporalBehavior(
            initiating_event={"tx": 0},
            trigger_condition={"tx": 0},
            active_window_cycles=16,
            min_settlement_cycles=8
        )

        ev = EvidenceArtifact(
            testbench_assertion_message=symptom,
            supporting_observations=[f"Baud prescaler '{root_sig}' counts with incorrect period modulo, inducing framing drift"]
        )

        alts = [
            RejectedAlternative(candidate_signal="tx", normalized_role=HardwareRole.OUTPUT_STROBE,
                                rejection_rationale="Serial line 'tx' is the observable symptom port; timing drift originates in prescaler counter", is_downstream_symptom=True)
        ]

        return V8UnifiedCertificate(
            certificate_id=f"V8_CERT_UART_{source_id.upper()}",
            source_case_id=source_id,
            design_family="uart",
            root_cause=rc,
            mechanism=mech,
            temporal=temp,
            evidence=ev,
            rejected_alternatives=alts,
            target_signals=signals
        )

    def validate_target(self, cert: V8UnifiedCertificate,
                        cycle_states: List[Dict[str, Any]],
                        signal_role_map: Dict[str, HardwareRole]) -> Dict[str, Any]:
        prescaler_sig = "cnt"
        for sig, role in signal_role_map.items():
            if role == HardwareRole.BAUD_PRESCALER:
                prescaler_sig = sig
                break

        # Look for baud rollover anomalies
        rollover_values = []
        for i in range(1, len(cycle_states)):
            prev_s = cycle_states[i - 1]
            curr_s = cycle_states[i]
            if prev_s.get("rst_n", 1) == 0:
                continue

            c_prev = prev_s.get(prescaler_sig)
            c_curr = curr_s.get(prescaler_sig)
            if c_prev is not None and c_curr is not None:
                # Count decreased (rollover event)
                if c_curr < c_prev:
                    rollover_values.append(c_prev)

        if not rollover_values:
            return {
                "decision": "INSUFFICIENT_EVIDENCE",
                "stage": "TRIGGER",
                "reason": f"No baud prescaler rollover events observed on '{prescaler_sig}'."
            }

        # Check for modulo timing defect (e.g. modulo 6 rollover instead of modulo 8)
        # Expected max count is 7 (modulo 8). Rollover at < 7 indicates baud drift.
        defect_detected = any(max_val < 7 for max_val in rollover_values)

        if not defect_detected:
            return {
                "decision": "FAIL",
                "stage": "STATE_INVARIANT",
                "reason": f"Baud prescaler '{prescaler_sig}' completed normal modulo 8 rollover; baud drift defect absent."
            }

        return {
            "decision": "PASS",
            "stage": "FULL_SEMANTIC",
            "matched_root_cause": prescaler_sig,
            "reason": f"Baud prescaler rollover anomaly confirmed on '{prescaler_sig}' (premature rollover at count < 7)."
        }


class PipelineProtocolAdapter(BaseProtocolAdapter):
    """
    Adapter for Multi-Stage Synchronous Pipelines.
    Models control tokens, stage enable preservation, and forwarding hazards.
    """

    @property
    def family_name(self) -> str:
        return "pipeline"

    def extract_certificate_specs(self, source_id: str, defect_desc: str,
                                  symptom: str, signals: List[str],
                                  root_sig: str, confidence: float,
                                  rtl_context: Optional[str] = None) -> V8UnifiedCertificate:
        rc_role, rc_class = SemanticRoleNormalizer.normalize_signal(root_sig, design_family="pipeline")
        rc = RootCauseIdentity(
            signal_name=root_sig,
            normalized_role=rc_role,
            module_name="pipeline",
            role_class=rc_class
        )

        obl = ProtocolObligationSpec(
            obligation_name="STAGE_CONTROL_TOKEN_DRAIN",
            precondition={"valid_in": 1},
            required_postcondition={"token_preserved_during_stall": 1},
            violation_signature={"token_dropped": 0},
            latency_cycles=2
        )

        mech = FailureMechanism(
            violated_invariant=HardwareInvariant.STAGE_CONTROL_TOKEN_DRAIN,
            protocol_obligation=obl,
            causal_mechanism_name="PIPELINE_STALL_TOKEN_DROP",
            upstream_antecedent=root_sig,
            downstream_symptom=symptom,
            causal_relation=CausalRelation.ROOT_CAUSE_ANTECEDENT
        )

        temp = TemporalBehavior(
            initiating_event={"valid_in": 1},
            trigger_condition={"valid_in": 1},
            active_window_cycles=6
        )

        ev = EvidenceArtifact(
            testbench_assertion_message=symptom,
            supporting_observations=[f"Pipeline control token '{root_sig}' dropped during stall bubble"]
        )

        alts = [
            RejectedAlternative(candidate_signal="d_out", normalized_role=HardwareRole.DATA_OUTPUT,
                                rejection_rationale="Output port data corruption is downstream of dropped control token", is_downstream_symptom=True),
            RejectedAlternative(candidate_signal="valid_out", normalized_role=HardwareRole.HANDSHAKE_VALID,
                                rejection_rationale="valid_out dropping is a manifestation of upstream control token clearing", is_downstream_symptom=True)
        ]

        return V8UnifiedCertificate(
            certificate_id=f"V8_CERT_PIPE_{source_id.upper()}",
            source_case_id=source_id,
            design_family="pipeline",
            root_cause=rc,
            mechanism=mech,
            temporal=temp,
            evidence=ev,
            rejected_alternatives=alts,
            target_signals=signals
        )

    def validate_target(self, cert: V8UnifiedCertificate,
                        cycle_states: List[Dict[str, Any]],
                        signal_role_map: Dict[str, HardwareRole]) -> Dict[str, Any]:
        # Safety gate: The certificate was extracted with candidate root cause `cert.root_cause.signal_name`
        cand_sig = cert.root_cause.signal_name
        
        # If the candidate was a data register (e.g. d1) but the defect is stall drop,
        # or if the target does not exhibit a stall drop on cand_sig, safely reject!
        if cert.root_cause.normalized_role != HardwareRole.PIPELINE_TOKEN:
            return {
                "decision": "FAIL",
                "stage": "STATE_INVARIANT",
                "reason": f"Candidate signal '{cand_sig}' is role {cert.root_cause.normalized_role.value}, not PIPELINE_TOKEN. Stall control invariant cannot be satisfied."
            }

        token_sig = "v1"
        for sig, role in signal_role_map.items():
            if role == HardwareRole.PIPELINE_TOKEN:
                token_sig = sig
                break

        # Check for control token drop during stall
        token_drop_cycles = []
        for i in range(1, len(cycle_states)):
            prev_s = cycle_states[i - 1]
            curr_s = cycle_states[i]
            if prev_s.get("rst_n", 1) == 0:
                continue

            # Stall drop condition
            if prev_s.get("valid_in") == 1 and curr_s.get(token_sig) == 0:
                token_drop_cycles.append(i)

        if not token_drop_cycles:
            return {
                "decision": "FAIL",
                "stage": "PROTOCOL_OBLIGATION",
                "reason": f"Pipeline control token '{token_sig}' was correctly preserved during stall; defect absent."
            }

        return {
            "decision": "PASS",
            "stage": "FULL_SEMANTIC",
            "matched_root_cause": token_sig,
            "reason": f"Pipeline control token drop confirmed on '{token_sig}' clearing during staged execution."
        }


class ProtocolRegistry:
    """Central registry and dispatcher for all protocol adapters."""

    _adapters: Dict[str, BaseProtocolAdapter] = {}

    @classmethod
    def register_adapter(cls, adapter: BaseProtocolAdapter) -> None:
        cls._adapters[adapter.family_name.lower()] = adapter

    @classmethod
    def get_adapter(cls, family_name: str) -> Optional[BaseProtocolAdapter]:
        return cls._adapters.get(family_name.lower())

    @classmethod
    def list_supported_families(cls) -> List[str]:
        return list(cls._adapters.keys())


# Register core standard protocol adapters
ProtocolRegistry.register_adapter(FifoProtocolAdapter())
ProtocolRegistry.register_adapter(AxiProtocolAdapter())
ProtocolRegistry.register_adapter(FsmProtocolAdapter())
ProtocolRegistry.register_adapter(UartProtocolAdapter())
ProtocolRegistry.register_adapter(PipelineProtocolAdapter())
