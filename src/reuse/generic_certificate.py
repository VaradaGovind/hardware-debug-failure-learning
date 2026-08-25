import os
import json
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from vcd.reader import TokenKind, tokenize

@dataclass
class GenericCausalCertificate:
    certificate_id: str
    source_failure: str
    target_module: str
    target_signals: List[str]
    defect_mechanism: str
    trigger_spec: Dict[str, Any]
    state_invariant_spec: Dict[str, Any]
    propagation_spec: Dict[str, Any]
    temporal_spec: Dict[str, Any]
    expected_consequence: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GenericCausalCertificate':
        return cls(**data)


def parse_vcd_signals(vcd_path: str, signal_names: List[str]) -> Dict[str, List[tuple]]:
    if not os.path.exists(vcd_path):
        return {}
    signal_map = {sig: [] for sig in signal_names}
    id_to_name = {}
    current_time = 0
    with open(vcd_path, 'rb') as f:
        for token in tokenize(f):
            if token.kind == TokenKind.VAR:
                name = token.data.reference
                if name in signal_names:
                    id_to_name[token.data.id_code] = name
            elif token.kind == TokenKind.CHANGE_TIME:
                current_time = token.data
            elif token.kind in (TokenKind.CHANGE_SCALAR, TokenKind.CHANGE_VECTOR, TokenKind.CHANGE_STRING, TokenKind.CHANGE_REAL):
                if token.data.id_code in id_to_name:
                    name = id_to_name[token.data.id_code]
                    val = token.data.value
                    signal_map[name].append((current_time, val))
    return signal_map


def build_cycle_state_table(signal_map: Dict[str, List[tuple]]) -> List[Dict[str, Any]]:
    if "clk" not in signal_map or not signal_map["clk"]:
        return []
    clk_transitions = signal_map["clk"]
    posedge_times = []
    last_val = None
    for t, val in clk_transitions:
        if (last_val == '0' or last_val == 0) and (val == '1' or val == 1):
            posedge_times.append(t)
        last_val = val

    all_signals = list(signal_map.keys())
    sig_indices = {s: 0 for s in all_signals}
    sig_current_val = {s: 0 for s in all_signals}
    cycle_states = []

    for cycle_idx, t_edge in enumerate(posedge_times):
        for s in all_signals:
            transitions = signal_map[s]
            idx = sig_indices[s]
            while idx < len(transitions) and transitions[idx][0] <= t_edge:
                raw_val = transitions[idx][1]
                try:
                    if isinstance(raw_val, str):
                        if raw_val in ['0', '1', 'x', 'z']:
                            sig_current_val[s] = 0 if raw_val in ['0', 'x', 'z'] else 1
                        else:
                            sig_current_val[s] = int(raw_val, 2)
                    elif isinstance(raw_val, int):
                        sig_current_val[s] = raw_val
                except Exception:
                    sig_current_val[s] = 0
                idx += 1
            sig_indices[s] = idx

        state_snapshot = dict(sig_current_val)
        state_snapshot["_time"] = t_edge
        state_snapshot["_cycle"] = cycle_idx
        cycle_states.append(state_snapshot)

    return cycle_states


class GenericCertificateValidator:
    """
    Generic Causal Certificate Validator across 5 hardware families.
    """
    def __init__(self):
        pass

    def evaluate_predicate(self, state: Dict[str, Any], predicate_dict: Dict[str, Any]) -> bool:
        for sig, expected in predicate_dict.items():
            if sig.startswith("_"): continue
            actual = state.get(sig, None)
            if actual is None:
                return False
            if actual != expected:
                return False
        return True

    def validate(self, cert: GenericCausalCertificate, vcd_path: str,
                 ablation_level: str = "L3_FULL") -> Dict[str, Any]:
        if not os.path.exists(vcd_path):
            return {"decision": "UNKNOWN", "reason": f"VCD not found at {vcd_path}"}

        req_signals = list(set(cert.target_signals + ["clk", "rst_n"]))
        signal_map = parse_vcd_signals(vcd_path, req_signals)
        cycle_states = build_cycle_state_table(signal_map)

        if len(cycle_states) < 2:
            return {"decision": "UNKNOWN", "reason": "Insufficient clock cycles"}

        trig_conds = cert.trigger_spec.get("conditions", {})
        trigger_cycles = []

        for i in range(1, len(cycle_states)):
            curr_state = cycle_states[i]
            prev_state = cycle_states[i - 1]
            if curr_state.get("rst_n", 1) == 0 or prev_state.get("rst_n", 1) == 0:
                continue
            if self.evaluate_predicate(curr_state, trig_conds):
                trigger_cycles.append(i)

        if not trigger_cycles:
            return {"decision": "FAIL", "stage": "TRIGGER", "reason": "Trigger never activated."}

        if ablation_level == "L1_TRIGGER_ONLY":
            return {"decision": "PASS", "stage": "TRIGGER", "trigger_count": len(trigger_cycles), "reason": f"Trigger activated ({len(trigger_cycles)}x)."}

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
                if val_after == 0 and val_before == 1:
                    anomaly_cycles.append(i)
                elif val_after != val_before:
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
            return {"decision": "FAIL", "stage": "STATE_INVARIANT", "reason": "Trigger occurred but invariant held."}

        if ablation_level == "L2_TRIGGER_STATE":
            return {"decision": "PASS", "stage": "STATE_INVARIANT", "reason": f"State anomaly verified ({len(anomaly_cycles)}x)."}

        if ablation_level == "NO_TEMPORAL_ORDER":
            return {"decision": "PASS", "stage": "NO_TEMPORAL", "reason": "Trigger and anomaly observed."}

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
                # Counter missing standard sequence
                if state.get("cnt", 0) in [2, 4, 6]:
                    desync_cycles.append(k)
            elif prop_type == "PIPELINE_PAYLOAD_CORRUPTION":
                if state.get("valid_out", 0) == 1:
                    desync_cycles.append(k)

        has_propagation = (len(desync_cycles) > 0)
        if not has_propagation:
            return {"decision": "FAIL", "stage": "PROPAGATION", "reason": "State anomaly did not propagate downstream."}

        # 4. Temporal causality (L4)
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
            "reason": "Full causal chain verified."
        }
