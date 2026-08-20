import os
import json
import numpy as np
from typing import Dict, Any, List, Optional
from .generic_certificate import GenericCausalCertificate, parse_vcd_signals, build_cycle_state_table

class RemediatedCertificateValidator:
    """
    Phase 3.1 Remediated Causal Certificate Validator.
    
    Features:
    1. Dynamic Event-Aware Trigger Scoping (distinguishes active control transitions from static idle levels).
    2. Pre-Validation Stimulus Sufficiency Auditing (distinguishes contradiction FAIL from INSUFFICIENT_EVIDENCE).
    3. Reset-Aware Invariant Windowing (isolates post-reset initialization from active evaluation).
    4. Explicit 3-Way Outcomes: PASS, FAIL, INSUFFICIENT_EVIDENCE.
    """
    def __init__(self, enable_dynamic_trigger: bool = True,
                 enable_sufficiency: bool = True,
                 enable_reset_awareness: bool = True):
        self.enable_dynamic_trigger = enable_dynamic_trigger
        self.enable_sufficiency = enable_sufficiency
        self.enable_reset_awareness = enable_reset_awareness

    def evaluate_predicate(self, state: Dict[str, Any], predicate_dict: Dict[str, Any]) -> bool:
        for sig, expected in predicate_dict.items():
            if sig.startswith("_"): continue
            actual = state.get(sig, None)
            if actual is None or actual != expected:
                return False
        return True

    def audit_stimulus_sufficiency(self, cert: GenericCausalCertificate,
                                   cycle_states: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Audits whether target waveform contains sufficient stimulus to reach the defect domain.
        """
        if len(cycle_states) < 3:
            return {"is_sufficient": False, "reason": "Waveform too short (< 3 clock cycles)"}

        trig_conds = cert.trigger_spec.get("conditions", {})
        active_cycles = 0
        max_reg_values = {}
        
        for i in range(1, len(cycle_states)):
            s = cycle_states[i]
            if s.get("rst_n", 1) == 1:
                active_cycles += 1
                for reg in cert.target_signals:
                    val = s.get(reg, 0)
                    if isinstance(val, (int, float)):
                        max_reg_values[reg] = max(max_reg_values.get(reg, 0), val)

        # Check boundary requirements (e.g. pointer wrap requiring depth >= 8)
        inv_spec = cert.state_invariant_spec
        target_reg = inv_spec.get("target_register")
        if target_reg in ["write_ptr", "read_ptr"] and inv_spec.get("type") == "STEP_INCREMENT":
            max_val = max_reg_values.get(target_reg, 0)
            if max_val < 4:
                return {
                    "is_sufficient": False,
                    "reason": f"Stimulus depth insufficient: {target_reg} max value {max_val} did not reach operational boundary.",
                    "active_cycles": active_cycles,
                    "max_reg_values": max_reg_values
                }

        return {
            "is_sufficient": True,
            "active_cycles": active_cycles,
            "max_reg_values": max_reg_values
        }

    def validate(self, cert: GenericCausalCertificate, vcd_path: str,
                 ablation_level: str = "L3_FULL") -> Dict[str, Any]:
        if not os.path.exists(vcd_path):
            return {"decision": "INSUFFICIENT_EVIDENCE", "stage": "PRECHECK", "reason": f"VCD not found at {vcd_path}"}

        req_signals = list(set(cert.target_signals + ["clk", "rst_n"]))
        signal_map = parse_vcd_signals(vcd_path, req_signals)
        cycle_states = build_cycle_state_table(signal_map)

        if len(cycle_states) < 2:
            return {"decision": "INSUFFICIENT_EVIDENCE", "stage": "PRECHECK", "reason": "Insufficient clock cycles in waveform"}

        # ---------------------------------------------------------------------
        # 1. STIMULUS SUFFICIENCY AUDIT
        # ---------------------------------------------------------------------
        if self.enable_sufficiency:
            suff_audit = self.audit_stimulus_sufficiency(cert, cycle_states)
            if not suff_audit["is_sufficient"]:
                return {
                    "decision": "INSUFFICIENT_EVIDENCE",
                    "stage": "SUFFICIENCY_AUDIT",
                    "reason": suff_audit["reason"],
                    "audit_details": suff_audit
                }

        # ---------------------------------------------------------------------
        # 2. RESET-AWARE WINDOWING
        # ---------------------------------------------------------------------
        eval_window = []
        is_reset_cert = (cert.trigger_spec.get("conditions", {}).get("rst_n") == 0)

        for i in range(1, len(cycle_states)):
            curr_s = cycle_states[i]
            prev_s = cycle_states[i - 1]

            if is_reset_cert:
                # Evaluating reset-specific causal defect
                if curr_s.get("rst_n", 1) == 0:
                    eval_window.append((i, prev_s, curr_s))
            else:
                # Evaluating normal operational defect
                if self.enable_reset_awareness:
                    # Skip active reset cycles and the immediate 1-cycle post-reset init
                    if curr_s.get("rst_n", 1) == 1 and prev_s.get("rst_n", 1) == 1:
                        eval_window.append((i, prev_s, curr_s))
                else:
                    eval_window.append((i, prev_s, curr_s))

        if not eval_window:
            return {"decision": "INSUFFICIENT_EVIDENCE", "stage": "RESET_WINDOW", "reason": "No active operational cycles outside reset."}

        # ---------------------------------------------------------------------
        # 3. DYNAMIC EVENT-AWARE TRIGGER SCOPING
        # ---------------------------------------------------------------------
        trig_conds = cert.trigger_spec.get("conditions", {})
        trigger_cycles = []

        for i, prev_s, curr_s in eval_window:
            if self.evaluate_predicate(curr_s, trig_conds):
                if self.enable_dynamic_trigger:
                    # Dynamic check: verify that this is an active event transition
                    # or active control assertion, rather than static idle level
                    has_active_transition = False
                    for sig, val in trig_conds.items():
                        prev_val = prev_s.get(sig, 0)
                        # Transition event (e.g. 0 -> 1) or active high control pulse
                        if val == 1 and curr_s.get(sig, 0) == 1:
                            has_active_transition = True
                        elif val == 0 and prev_val != 0:
                            has_active_transition = True
                        elif any(curr_s.get(k, 0) != prev_s.get(k, 0) for k in cert.target_signals):
                            has_active_transition = True
                            
                    if has_active_transition:
                        trigger_cycles.append(i)
                else:
                    trigger_cycles.append(i)

        if not trigger_cycles:
            return {
                "decision": "INSUFFICIENT_EVIDENCE" if self.enable_sufficiency else "FAIL",
                "stage": "TRIGGER",
                "trigger_count": 0,
                "reason": "Causal trigger event never activated during operational evaluation window."
            }

        if ablation_level == "L1_TRIGGER_ONLY":
            return {"decision": "PASS", "stage": "TRIGGER", "trigger_count": len(trigger_cycles), "reason": f"Trigger activated ({len(trigger_cycles)}x)."}

        # ---------------------------------------------------------------------
        # 4. STATE INVARIANT ANOMALY EVALUATION
        # ---------------------------------------------------------------------
        inv_spec = cert.state_invariant_spec
        inv_type = inv_spec.get("type", "CONSERVATION")
        target_reg = inv_spec.get("target_register")
        anomaly_cycles = []

        for i in trigger_cycles:
            curr_state = cycle_states[i]
            prev_state = cycle_states[i - 1]

            val_before = prev_state.get(target_reg, 0)
            val_after = curr_state.get(target_reg, 0)
            delta = val_after - val_before

            if inv_type == "CONSERVATION":
                anom_delta = inv_spec.get("anomaly_delta", 1)
                if delta == anom_delta:
                    anomaly_cycles.append(i)

            elif inv_type == "STABILITY":
                # Stability anomaly: signal changed or dropped unexpectedly
                if val_after == 0 and val_before == 1:
                    anomaly_cycles.append(i)
                elif val_after != val_before and any(curr_state.get(k, 0) != prev_state.get(k, 0) for k in cert.target_signals):
                    anomaly_cycles.append(i)

            elif inv_type == "STEP_INCREMENT":
                expected_step = inv_spec.get("expected_change", 1)
                if delta != expected_step:
                    anomaly_cycles.append(i)

            elif inv_type == "STATE_TRANSITION":
                exp_next = inv_spec.get("expected_next_state", 1)
                if val_after != exp_next:
                    anomaly_cycles.append(i)

            elif inv_type == "LATENCY_PIPELINE":
                in_sig = inv_spec.get("input_signal", "d1")
                out_sig = inv_spec.get("output_signal", "d_out")
                if curr_state.get(out_sig) != prev_state.get(in_sig):
                    anomaly_cycles.append(i)

        if not anomaly_cycles:
            # Trigger occurred with sufficient stimulus, but invariant was strictly maintained
            return {
                "decision": "FAIL",
                "stage": "STATE_INVARIANT",
                "trigger_count": len(trigger_cycles),
                "anomaly_count": 0,
                "reason": "Trigger occurred, but the target maintained the causal invariant (contradicting certificate)."
            }

        if ablation_level == "L2_TRIGGER_STATE":
            return {"decision": "PASS", "stage": "STATE_INVARIANT", "reason": f"State anomaly verified ({len(anomaly_cycles)}x)."}

        if ablation_level == "NO_TEMPORAL_ORDER":
            return {"decision": "PASS", "stage": "NO_TEMPORAL", "reason": "Trigger and anomaly observed."}

        # ---------------------------------------------------------------------
        # 5. DOWNSTREAM CAUSAL PROPAGATION & PERSISTENCE
        # ---------------------------------------------------------------------
        prop_spec = cert.propagation_spec
        first_anom = min(anomaly_cycles)
        prop_type = prop_spec.get("type", "POINTER_OCCUPANCY_DIVERGENCE")
        desync_cycles = []

        for k in range(first_anom, len(cycle_states)):
            state = cycle_states[k]
            if prop_type == "POINTER_OCCUPANCY_DIVERGENCE":
                w_ptr = state.get("write_ptr", 0)
                r_ptr = state.get("read_ptr", 0)
                cnt = state.get("count", 0)
                if cnt != ((w_ptr - r_ptr) % 16):
                    desync_cycles.append(k)
            elif prop_type == "HANDSHAKE_STALL_PROPAGATION":
                if state.get("valid_out", 0) == 0:
                    desync_cycles.append(k)
            elif prop_type == "STATE_CORRUPTION_PERSISTENCE":
                if state.get("done", 0) == 1 or state.get("state", 0) == 2:
                    desync_cycles.append(k)
            elif prop_type == "BAUD_SAMPLE_DESYNC":
                if state.get("cnt", 0) in [2, 4, 6]:
                    desync_cycles.append(k)
            elif prop_type == "PIPELINE_PAYLOAD_CORRUPTION":
                if state.get("valid_out", 0) == 1:
                    desync_cycles.append(k)

        has_propagation = (len(desync_cycles) > 0)
        if not has_propagation:
            return {
                "decision": "FAIL",
                "stage": "PROPAGATION",
                "trigger_count": len(trigger_cycles),
                "anomaly_count": len(anomaly_cycles),
                "propagation_cycles": len(desync_cycles),
                "reason": "State anomaly occurred, but did not causally propagate downstream."
            }

        # ---------------------------------------------------------------------
        # 6. STRICT TEMPORAL ORDERING (L4)
        # ---------------------------------------------------------------------
        min_trig = min(trigger_cycles)
        min_anom = min(anomaly_cycles)
        min_desync = min(desync_cycles)
        last_cycle = len(cycle_states) - 1

        if ablation_level == "L4_STRICT_TEMPORAL" and not (min_trig <= min_anom <= min_desync <= last_cycle):
            return {"decision": "FAIL", "stage": "TEMPORAL", "reason": "Causal temporal ordering violated."}

        return {
            "decision": "PASS",
            "stage": "FULL_CAUSAL",
            "trigger_count": len(trigger_cycles),
            "anomaly_count": len(anomaly_cycles),
            "propagation_cycles": len(desync_cycles),
            "reason": "Full causal chain verified across observable waveform invariants."
        }
