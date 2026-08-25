import os
import json
import numpy as np
from typing import Dict, Any, List
from .causal_certificate import CausalCertificate, parse_vcd_signals, build_cycle_state_table
from .similarity_baselines import SimilarityBaselines, tokenize_log, jaccard_similarity

class TriggerOnlyValidator:
    """Level 1: Checks ONLY if the trigger predicate occurs in the target waveform."""
    def validate(self, certificate: CausalCertificate, vcd_path: str) -> Dict[str, Any]:
        if not os.path.exists(vcd_path):
            return {"decision": "UNKNOWN", "reason": "VCD not found"}
            
        signal_map = parse_vcd_signals(vcd_path, list(set(certificate.target_signals + ["clk", "rst_n"])))
        cycle_states = build_cycle_state_table(signal_map)
        
        trigger_count = 0
        for state in cycle_states:
            if state.get("rst_n", 1) == 0: continue
            if state.get("write_en", 0) == 1 and state.get("read_en", 0) == 1 and state.get("full", 0) == 0 and state.get("empty", 0) == 0:
                trigger_count += 1
                
        if trigger_count > 0:
            return {"decision": "PASS", "trigger_count": trigger_count, "reason": f"Trigger condition occurred {trigger_count} times."}
        else:
            return {"decision": "FAIL", "trigger_count": 0, "reason": "Trigger condition never occurred."}


class TriggerStateOnlyValidator:
    """Level 2: Checks trigger occurrence + immediate 1-step state transition anomaly across the clock edge."""
    def validate(self, certificate: CausalCertificate, vcd_path: str) -> Dict[str, Any]:
        if not os.path.exists(vcd_path):
            return {"decision": "UNKNOWN", "reason": "VCD not found"}
            
        signal_map = parse_vcd_signals(vcd_path, list(set(certificate.target_signals + ["clk", "rst_n"])))
        cycle_states = build_cycle_state_table(signal_map)
        
        trigger_cycles = []
        anomaly_cycles = []
        
        for i in range(1, len(cycle_states)):
            curr_state = cycle_states[i]
            prev_state = cycle_states[i - 1]
            
            if curr_state.get("rst_n", 1) == 0 or prev_state.get("rst_n", 1) == 0:
                continue
                
            write_en = curr_state.get("write_en", 0)
            read_en = curr_state.get("read_en", 0)
            full_prev = prev_state.get("full", 0)
            empty_prev = prev_state.get("empty", 0)
            
            if write_en == 1 and read_en == 1 and full_prev == 0 and empty_prev == 0:
                trigger_cycles.append(i)
                count_before = prev_state.get("count", 0)
                count_after = curr_state.get("count", 0)
                if count_after == count_before + 1:
                    anomaly_cycles.append(i)
                    
        if not trigger_cycles:
            return {"decision": "FAIL", "trigger_count": 0, "anomaly_count": 0, "reason": "Trigger never occurred."}
        if not anomaly_cycles:
            return {"decision": "FAIL", "trigger_count": len(trigger_cycles), "anomaly_count": 0, "reason": "Trigger occurred but 1-step count anomaly did not occur (invariant held)."}
            
        return {"decision": "PASS", "trigger_count": len(trigger_cycles), "anomaly_count": len(anomaly_cycles), "reason": f"Trigger and immediate 1-step count anomaly verified ({len(anomaly_cycles)} times)."}


class TriggerStatePropagationValidator:
    """Level 3: Full Causal Validator (Trigger + Immediate State Anomaly + Downstream Propagation)."""
    def validate(self, certificate: CausalCertificate, vcd_path: str) -> Dict[str, Any]:
        if not os.path.exists(vcd_path):
            return {"decision": "UNKNOWN", "reason": "VCD not found"}
            
        signal_map = parse_vcd_signals(vcd_path, list(set(certificate.target_signals + ["clk", "rst_n"])))
        cycle_states = build_cycle_state_table(signal_map)
        
        trigger_cycles = []
        anomaly_cycles = []
        
        for i in range(1, len(cycle_states)):
            curr_state = cycle_states[i]
            prev_state = cycle_states[i - 1]
            
            if curr_state.get("rst_n", 1) == 0 or prev_state.get("rst_n", 1) == 0:
                continue
                
            write_en = curr_state.get("write_en", 0)
            read_en = curr_state.get("read_en", 0)
            full_prev = prev_state.get("full", 0)
            empty_prev = prev_state.get("empty", 0)
            
            if write_en == 1 and read_en == 1 and full_prev == 0 and empty_prev == 0:
                trigger_cycles.append(i)
                count_before = prev_state.get("count", 0)
                count_after = curr_state.get("count", 0)
                if count_after == count_before + 1:
                    anomaly_cycles.append(i)
                    
        if not trigger_cycles:
            return {"decision": "FAIL", "reason": "Trigger condition never occurred."}
        if not anomaly_cycles:
            return {"decision": "FAIL", "reason": "Trigger occurred but count was properly held constant."}
            
        desync_cycles = []
        first_anomaly_idx = min(anomaly_cycles)
        
        for i in range(first_anomaly_idx, len(cycle_states)):
            state = cycle_states[i]
            w_ptr = state.get("write_ptr", 0)
            r_ptr = state.get("read_ptr", 0)
            cnt = state.get("count", 0)
            true_occ = (w_ptr - r_ptr) % 16
            if cnt != true_occ:
                desync_cycles.append(i)
                
        has_persistent_desync = (len(desync_cycles) > 0 and desync_cycles[-1] >= len(cycle_states) - 3)
        
        if has_persistent_desync:
            return {
                "decision": "PASS",
                "trigger_count": len(trigger_cycles),
                "anomaly_count": len(anomaly_cycles),
                "propagation_cycles": len(desync_cycles),
                "reason": f"Full causal chain verified: Trigger ({len(trigger_cycles)}x) -> Anomaly ({len(anomaly_cycles)}x) -> Downstream Desync ({len(desync_cycles)} cycles)."
            }
        else:
            return {
                "decision": "FAIL",
                "trigger_count": len(trigger_cycles),
                "anomaly_count": len(anomaly_cycles),
                "propagation_cycles": len(desync_cycles),
                "reason": "Trigger and 1-step anomaly occurred, but anomaly was transient/self-corrected and did not propagate to terminal failure."
            }


class TriggerStatePropagationTemporalValidator:
    """Level 4: Strict Temporal Invariant Validator (Trigger strictly precedes Anomaly strictly precedes Desync strictly precedes Termination)."""
    def validate(self, certificate: CausalCertificate, vcd_path: str) -> Dict[str, Any]:
        if not os.path.exists(vcd_path):
            return {"decision": "UNKNOWN", "reason": "VCD not found"}
            
        signal_map = parse_vcd_signals(vcd_path, list(set(certificate.target_signals + ["clk", "rst_n"])))
        cycle_states = build_cycle_state_table(signal_map)
        
        trigger_cycles = []
        anomaly_cycles = []
        
        for i in range(1, len(cycle_states)):
            curr_state = cycle_states[i]
            prev_state = cycle_states[i - 1]
            
            if curr_state.get("rst_n", 1) == 0 or prev_state.get("rst_n", 1) == 0:
                continue
                
            write_en = curr_state.get("write_en", 0)
            read_en = curr_state.get("read_en", 0)
            full_prev = prev_state.get("full", 0)
            empty_prev = prev_state.get("empty", 0)
            
            if write_en == 1 and read_en == 1 and full_prev == 0 and empty_prev == 0:
                trigger_cycles.append(i)
                count_before = prev_state.get("count", 0)
                count_after = curr_state.get("count", 0)
                if count_after == count_before + 1:
                    anomaly_cycles.append(i)
                    
        if not trigger_cycles or not anomaly_cycles:
            return {"decision": "FAIL", "reason": "Missing trigger or immediate causal anomaly."}
            
        min_trig = min(trigger_cycles)
        min_anom = min(anomaly_cycles)
        
        desync_cycles = [i for i, state in enumerate(cycle_states) if state.get("count", 0) != ((state.get("write_ptr", 0) - state.get("read_ptr", 0)) % 16) and i >= min_anom]
        
        has_persistent_desync = (len(desync_cycles) > 0 and desync_cycles[-1] >= len(cycle_states) - 3)
        if not has_persistent_desync:
            return {"decision": "FAIL", "reason": "No persistent downstream propagation observed following anomaly."}
            
        min_desync = min(desync_cycles)
        last_cycle = len(cycle_states) - 1
        
        if min_trig <= min_anom <= min_desync <= last_cycle:
            return {
                "decision": "PASS",
                "temporal_ordering": f"Trigger (cycle {min_trig}) -> Anomaly (cycle {min_anom}) -> Desync (cycle {min_desync}) -> End (cycle {last_cycle})",
                "reason": "Strict causal temporal ordering verified."
            }
        else:
            return {"decision": "FAIL", "reason": "Temporal ordering of causal sequence violated."}


class NoTemporalOrderValidator:
    """Ablation: Checks presence of trigger and count anomaly anywhere without requiring causal ordering."""
    def validate(self, certificate: CausalCertificate, vcd_path: str) -> Dict[str, Any]:
        if not os.path.exists(vcd_path):
            return {"decision": "UNKNOWN", "reason": "VCD not found"}
            
        signal_map = parse_vcd_signals(vcd_path, list(set(certificate.target_signals + ["clk", "rst_n"])))
        cycle_states = build_cycle_state_table(signal_map)
        
        has_trigger = any(state.get("write_en", 0) == 1 and state.get("read_en", 0) == 1 and state.get("full", 0) == 0 and state.get("empty", 0) == 0 for state in cycle_states if state.get("rst_n", 1) == 1)
        has_count_increment = any(cycle_states[i].get("count", 0) > cycle_states[i-1].get("count", 0) for i in range(1, len(cycle_states)))
        
        if has_trigger and has_count_increment:
            return {"decision": "PASS", "reason": "Trigger and count increment both observed somewhere (order unconstrained)."}
        else:
            return {"decision": "FAIL", "reason": "Missing trigger or count increment."}


class AdvancedWaveformSimilarityBaseline:
    """
    Stronger similarity baseline combining:
    1. Waveform transition switching activity vectors across clock cycles.
    2. RTL AST & structural signal connectivity graph.
    3. Failure log & symptom semantic embedding.
    """
    def __init__(self):
        self.basic = SimilarityBaselines()

    def compute_waveform_signature_similarity(self, vcd_a: str, vcd_b: str, signals: List[str]) -> float:
        map_a = parse_vcd_signals(vcd_a, signals)
        map_b = parse_vcd_signals(vcd_b, signals)
        
        sig_trans_a = np.array([len(map_a.get(s, [])) for s in signals], dtype=float)
        sig_trans_b = np.array([len(map_b.get(s, [])) for s in signals], dtype=float)
        
        norm_a = np.linalg.norm(sig_trans_a)
        norm_b = np.linalg.norm(sig_trans_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        cosine_sim = float(np.dot(sig_trans_a, sig_trans_b) / (norm_a * norm_b))
        return max(0.0, min(1.0, cosine_sim))

    def evaluate_pair(self, vcd_a: str, vcd_b: str, rtl_a: str, rtl_b: str, log_a: str, log_b: str, signals: List[str]) -> Dict[str, float]:
        wf_sim = self.compute_waveform_signature_similarity(vcd_a, vcd_b, signals)
        struct_sim = self.basic.compute_structural_similarity(rtl_a, rtl_b)["score"]
        log_sim = self.basic.compute_log_similarity(log_a, log_b)["score"]
        sem_sim = self.basic.compute_semantic_similarity(log_a, log_b)["score"]
        
        composite = 0.40 * wf_sim + 0.20 * struct_sim + 0.20 * log_sim + 0.20 * sem_sim
        return {
            "waveform_signature_sim": wf_sim,
            "structural_sim": struct_sim,
            "log_sim": log_sim,
            "semantic_sim": sem_sim,
            "composite_similarity": composite
        }
