import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from vcd.reader import TokenKind, tokenize

@dataclass
class CausalCertificate:
    certificate_id: str
    source_failure: str
    target_module: str
    target_signals: List[str]
    defect_mechanism: str
    trigger_predicate: Dict[str, Any]
    propagation_chain: List[Dict[str, Any]]
    invariant_violation: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CausalCertificate':
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


class CertificateValidator:
    """Evaluates causal certificates against VCD waveforms."""
    def __init__(self):
        pass

    def validate_certificate(self, certificate: CausalCertificate, vcd_path: str,
                             rtl_content: str = "") -> Dict[str, Any]:
        """
        Validates whether the causal certificate explains the defect in the target waveform.
        
        Returns:
            {
                "decision": "PASS" | "FAIL" | "UNKNOWN",
                "trigger_matched": bool,
                "anomaly_matched": bool,
                "propagation_matched": bool,
                "evidence": Dict[str, Any],
                "reason": str
            }
        """
        if not os.path.exists(vcd_path):
            return {
                "decision": "UNKNOWN",
                "trigger_matched": False,
                "anomaly_matched": False,
                "propagation_matched": False,
                "evidence": {},
                "reason": f"VCD file not found at {vcd_path}"
            }
            
        required_signals = list(set(certificate.target_signals + ["clk", "rst_n"]))
        signal_map = parse_vcd_signals(vcd_path, required_signals)
        
        if not signal_map.get("clk"):
            return {
                "decision": "UNKNOWN",
                "trigger_matched": False,
                "anomaly_matched": False,
                "propagation_matched": False,
                "evidence": {},
                "reason": "Missing clock signal in waveform"
            }
            
        cycle_states = build_cycle_state_table(signal_map)
        if len(cycle_states) < 2:
            return {
                "decision": "UNKNOWN",
                "trigger_matched": False,
                "anomaly_matched": False,
                "propagation_matched": False,
                "evidence": {},
                "reason": "Insufficient clock cycles in waveform"
            }
            
        trigger_cycles = []
        for i, state in enumerate(cycle_states[:-1]):
            if state.get("rst_n", 1) == 0:
                continue
                
            write_en = state.get("write_en", 0)
            read_en = state.get("read_en", 0)
            full = state.get("full", 0)
            empty = state.get("empty", 0)
            
            trig_spec = certificate.trigger_predicate
            matches_trigger = True
            
            if trig_spec.get("simultaneous_rw", True):
                if not (write_en == 1 and read_en == 1 and full == 0 and empty == 0):
                    matches_trigger = False
                    
            if matches_trigger:
                trigger_cycles.append(i)
                
        if not trigger_cycles:
            return {
                "decision": "FAIL",
                "trigger_matched": False,
                "anomaly_matched": False,
                "propagation_matched": False,
                "evidence": {"total_cycles": len(cycle_states), "trigger_occurrences": 0},
                "reason": "Trigger condition (simultaneous active write_en and read_en) never occurred in target waveform"
            }
            
        anomaly_occurrences = []
        for t_idx in trigger_cycles:
            curr_state = cycle_states[t_idx]
            next_state = cycle_states[t_idx + 1]
            
            curr_count = curr_state.get("count", 0)
            next_count = next_state.get("count", 0)
            
            if next_count == curr_count + 1:
                anomaly_occurrences.append({
                    "cycle": t_idx,
                    "time": curr_state.get("_time"),
                    "count_before": curr_count,
                    "count_after": next_count
                })
                
        if not anomaly_occurrences:
            return {
                "decision": "FAIL",
                "trigger_matched": True,
                "anomaly_matched": False,
                "propagation_matched": False,
                "evidence": {
                    "trigger_cycles": trigger_cycles,
                    "anomaly_occurrences": 0
                },
                "reason": "Trigger occurred but occupancy invariant was preserved (count did not overincrement)"
            }
            
        propagation_evidence = []
        for i, state in enumerate(cycle_states):
            w_ptr = state.get("write_ptr", 0)
            r_ptr = state.get("read_ptr", 0)
            cnt = state.get("count", 0)
            
            true_occupancy = (w_ptr - r_ptr) % 16
            if cnt != true_occupancy and any(a["cycle"] < i for a in anomaly_occurrences):
                propagation_evidence.append({
                    "cycle": i,
                    "count": cnt,
                    "true_occupancy": true_occupancy,
                    "write_ptr": w_ptr,
                    "read_ptr": r_ptr,
                    "full": state.get("full", 0),
                    "empty": state.get("empty", 0)
                })
                
        propagation_matched = len(propagation_evidence) > 0
        
        if propagation_matched:
            return {
                "decision": "PASS",
                "trigger_matched": True,
                "anomaly_matched": True,
                "propagation_matched": True,
                "evidence": {
                    "trigger_count": len(trigger_cycles),
                    "anomaly_count": len(anomaly_occurrences),
                    "propagation_cycles": len(propagation_evidence),
                    "first_anomaly": anomaly_occurrences[0],
                    "sample_desync": propagation_evidence[0] if propagation_evidence else {}
                },
                "reason": f"Causal certificate verified: Trigger matched ({len(trigger_cycles)} times), count overincrement anomaly verified ({len(anomaly_occurrences)} times), and downstream occupancy desynchronization confirmed."
            }
        else:
            return {
                "decision": "FAIL",
                "trigger_matched": True,
                "anomaly_matched": True,
                "propagation_matched": False,
                "evidence": {"anomaly_count": len(anomaly_occurrences)},
                "reason": "Anomaly occurred but did not propagate to downstream occupancy desynchronization."
            }
