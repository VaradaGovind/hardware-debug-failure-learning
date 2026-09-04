import os
import json
import numpy as np
from typing import Dict, Any, List, Optional
from .generic_certificate import parse_vcd_signals, build_cycle_state_table
from .transaction_semantic_certificate import TransactionSemanticCertificate

class TransactionSemanticValidator:
    """
    Evaluates Transaction-Level Semantic Causal Certificates with exact protocol latency contracts.
    """
    def __init__(self):
        pass

    def evaluate_predicate(self, state: Dict[str, Any], predicate_dict: Dict[str, Any]) -> bool:
        for sig, expected in predicate_dict.items():
            if sig.startswith("_"): continue
            actual = state.get(sig, None)
            if actual is None or actual != expected:
                return False
        return True

    def detect_transaction_events(self, ctx_spec: Any, cycle_states: List[Dict[str, Any]]) -> List[int]:
        init_event = ctx_spec.initiating_event
        tx_cycles = []

        for i in range(1, len(cycle_states)):
            curr_s = cycle_states[i]
            prev_s = cycle_states[i - 1]

            if curr_s.get("rst_n", 1) == 0 or prev_s.get("rst_n", 1) == 0:
                continue

            is_active_init = True
            for sig, exp_val in init_event.items():
                curr_val = curr_s.get(sig, None)
                if curr_val != exp_val:
                    is_active_init = False
                    break

            if is_active_init:
                tx_cycles.append(i)

        return tx_cycles

    def validate(self, cert: TransactionSemanticCertificate, vcd_path: str,
                 ablation_mode: str = "FULL_SEMANTIC") -> Dict[str, Any]:
        if not os.path.exists(vcd_path):
            return {
                "decision": "INSUFFICIENT_EVIDENCE",
                "stage": "PRECHECK",
                "reason": f"VCD waveform not found at {vcd_path}"
            }

        req_signals = list(set(cert.target_signals + ["clk", "rst_n"]))
        signal_map = parse_vcd_signals(vcd_path, req_signals)
        cycle_states = build_cycle_state_table(signal_map)

        if len(cycle_states) < 3:
            return {
                "decision": "INSUFFICIENT_EVIDENCE",
                "stage": "PRECHECK",
                "reason": "Insufficient clock cycles in target waveform."
            }

        tx_cycles = self.detect_transaction_events(cert.transaction_context, cycle_states)
        
        if not tx_cycles:
            return {
                "decision": "INSUFFICIENT_EVIDENCE",
                "stage": "TRANSACTION_CONTEXT",
                "reason": f"Required transaction context ({cert.transaction_context.transaction_type}) was never initiated in waveform.",
                "unexercised_precondition": cert.transaction_context.initiating_event
            }

        trig_conds = cert.trigger_spec.get("conditions", {})
        trig_cycles = []
        
        for t_idx in tx_cycles:
            window_len = cert.transaction_context.active_window_cycles
            for w in range(t_idx, min(t_idx + window_len, len(cycle_states))):
                if self.evaluate_predicate(cycle_states[w], trig_conds):
                    trig_cycles.append(w)

        if not trig_cycles:
            return {
                "decision": "INSUFFICIENT_EVIDENCE",
                "stage": "TRIGGER",
                "reason": "Transaction context was active, but trigger condition was not exercised in transaction window."
            }

        if ablation_mode == "TRIGGER_ONLY":
            return {"decision": "PASS", "stage": "TRIGGER", "trigger_count": len(trig_cycles)}

        obl = cert.protocol_obligation
        obl_violations = []

        for c_idx in trig_cycles:
            curr_s = cycle_states[c_idx]
            prev_s = cycle_states[c_idx - 1]
            next_idx = min(c_idx + obl.temporal_latency, len(cycle_states) - 1)
            next_s = cycle_states[next_idx]

            if obl.obligation_type == "STATE_TRANSITION_OBLIGATION":
                if curr_s.get("state") == 0 and curr_s.get("start") == 1 and next_s.get("state") == 0:
                    obl_violations.append(c_idx)

            elif obl.obligation_type == "FORWARDING_HAZARD_RESOLUTION":
                in_data = curr_s.get("d_in", 0)
                staged_data = curr_s.get("d1", 0)
                out_data = next_s.get("d_out", 0)
                if out_data == in_data and out_data != staged_data:
                    obl_violations.append(c_idx)

            elif obl.obligation_type == "STALL_DRAINAGE_PRESERVATION":
                if curr_s.get("valid_in") == 1 and next_s.get("valid_out") == 0:
                    obl_violations.append(c_idx)

            elif obl.obligation_type == "STAGE_ENABLE_COUPLING":
                if prev_s.get("v1") == 0 and curr_s.get("valid_out") == 1:
                    obl_violations.append(c_idx)

            elif obl.obligation_type == "HANDSHAKE_DATA_STABILITY":
                if prev_s.get("valid_out") == 1 and curr_s.get("valid_out") == 0 and curr_s.get("ready_in") == 0:
                    obl_violations.append(c_idx)

            elif obl.obligation_type == "OCCUPANCY_CONSERVATION":
                if curr_s.get("read_en") == 1 and curr_s.get("write_en") == 1:
                    if curr_s.get("count") != prev_s.get("count"):
                        obl_violations.append(c_idx)

        if not obl_violations:
            return {
                "decision": "FAIL",
                "stage": "PROTOCOL_OBLIGATION",
                "reason": "Transaction occurred, but protocol obligation was fulfilled (defect mechanism was absent)."
            }

        if ablation_mode == "OBLIGATION_ONLY":
            return {"decision": "PASS", "stage": "PROTOCOL_OBLIGATION", "violation_count": len(obl_violations)}

        inv_spec = cert.state_invariant_spec
        inv_type = inv_spec.get("type", "CONSERVATION")
        target_reg = inv_spec.get("target_register")
        anomaly_cycles = []

        for c_idx in obl_violations:
            curr_s = cycle_states[c_idx]
            prev_s = cycle_states[c_idx - 1]
            delta = curr_s.get(target_reg, 0) - prev_s.get(target_reg, 0)

            if inv_type == "CONSERVATION":
                if delta == inv_spec.get("anomaly_delta", 1):
                    anomaly_cycles.append(c_idx)
            elif inv_type == "STATE_TRANSITION":
                if curr_s.get(target_reg) == inv_spec.get("anomaly_state", 0):
                    anomaly_cycles.append(c_idx)
            elif inv_type == "STABILITY":
                if curr_s.get(target_reg) != prev_s.get(target_reg):
                    anomaly_cycles.append(c_idx)
            elif inv_type == "LATENCY_PIPELINE":
                if curr_s.get("d_out") != prev_s.get("d1"):
                    anomaly_cycles.append(c_idx)

        if not anomaly_cycles:
            return {
                "decision": "FAIL",
                "stage": "STATE_INVARIANT",
                "reason": f"Expected state invariant anomaly ({inv_type} on {target_reg}) was not observed in waveform."
            }

        if ablation_mode == "TRIGGER_STATE":
            return {"decision": "PASS", "stage": "STATE_INVARIANT", "anomaly_count": len(anomaly_cycles)}

        prop_spec = cert.causal_propagation_spec
        first_anom = min(anomaly_cycles)
        prop_type = prop_spec.get("type", "OCCUPANCY_DIVERGENCE")
        desync_cycles = []

        for k in range(first_anom, len(cycle_states)):
            s = cycle_states[k]
            if prop_type == "OCCUPANCY_DIVERGENCE":
                w_ptr = s.get("write_ptr", 0)
                r_ptr = s.get("read_ptr", 0)
                cnt = s.get("count", 0)
                if cnt != ((w_ptr - r_ptr) % 16):
                    desync_cycles.append(k)
            elif prop_type in ["STALL_PROPAGATION", "STATE_DEADLOCK"]:
                if s.get("valid_out", 0) == 0 or s.get("done", 0) == 0:
                    desync_cycles.append(k)
            elif prop_type == "PIPELINE_CORRUPTION":
                if s.get("valid_out", 0) == 1:
                    desync_cycles.append(k)

        if not desync_cycles:
            return {
                "decision": "FAIL",
                "stage": "PROPAGATION",
                "reason": "Protocol obligation violated, but did not causally propagate downstream."
            }

        if ablation_mode in ["TRIGGER_PROPAGATION", "OBLIGATION_PROPAGATION"]:
            return {"decision": "PASS", "stage": "PROPAGATION", "desync_count": len(desync_cycles)}

        min_tx = min(tx_cycles)
        min_obl = min(obl_violations)
        min_prop = min(desync_cycles)
        last_c = len(cycle_states) - 1

        if not (min_tx <= min_obl <= min_prop <= last_c):
            return {
                "decision": "FAIL",
                "stage": "TEMPORAL",
                "reason": "Causal event sequence was out of order."
            }

        return {
            "decision": "PASS",
            "stage": "FULL_TRANSACTION_SEMANTIC",
            "tx_count": len(tx_cycles),
            "obligation_violations": len(obl_violations),
            "propagation_cycles": len(desync_cycles),
            "reason": "Full transaction obligation violation and causal propagation verified."
        }
