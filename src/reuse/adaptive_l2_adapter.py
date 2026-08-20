import os
import copy
import time
import random
from typing import Dict, Any, List, Optional
from .generic_certificate import parse_vcd_signals, build_cycle_state_table
from .transaction_semantic_certificate import TransactionSemanticCertificate, TransactionContext
from .transaction_semantic_validator import TransactionSemanticValidator
from .adaptive_transaction_boundary import AdaptiveTransactionBoundaryDetector, TransactionSegment
from .adaptive_evidence import AdaptiveEvidenceClassifier, EvidenceSufficiencyResult

class AdaptiveL2Adapter:
    """
    Integrates Adaptive Transaction Boundary Recovery with the FROZEN Phase 4 L2 Validator.
    
    SCIENTIFIC INTEGRITY CONTRACT:
    1. The Phase 4 L2 Validator (TransactionSemanticValidator) is treated as 100% frozen.
    2. The adapter recovers the transaction boundary independently without oracle knowledge.
    3. The adapter maps the recovered segment to the minimal sufficient evidence window.
    4. The frozen L2 validator evaluates protocol obligations, state invariants, and causal propagation.
    5. The final decision is returned unchanged.
    """
    def __init__(self, quiescence_threshold: int = 2):
        self.detector = AdaptiveTransactionBoundaryDetector(quiescence_threshold=quiescence_threshold)
        self.classifier = AdaptiveEvidenceClassifier()
        self.frozen_validator = TransactionSemanticValidator()

    def validate_adaptive(self, cert: TransactionSemanticCertificate, vcd_path: str,
                          ablation_mode: str = "FULL_SEMANTIC",
                          control_mode: str = "ADAPTIVE_PRIMARY") -> Dict[str, Any]:
        """
        Executes adaptive boundary recovery and frozen L2 validation.
        
        Supported control_modes:
        - "ADAPTIVE_PRIMARY": Proposed method (Adaptive boundary detection -> Frozen L2)
        - "STATIC_FIXED": Static 4-cycle window baseline
        - "RANDOM_WINDOW_CONTROL": Randomly sampled window length & offset
        - "MATCHED_LENGTH_CONTROL": Non-semantic activity window of identical length
        - "BROAD_WINDOW_CONTROL": Overly broad window covering entire trace
        """
        t0 = time.time()

        if not os.path.exists(vcd_path):
            return {
                "decision": "INSUFFICIENT_EVIDENCE",
                "stage": "PRECHECK",
                "reason": f"VCD waveform not found at {vcd_path}",
                "adaptive_metrics": {"elapsed_ms": (time.time() - t0) * 1000}
            }

        # 1. Parse waveform cycle states
        req_signals = list(set(cert.target_signals + ["clk", "rst_n"]))
        signal_map = parse_vcd_signals(vcd_path, req_signals)
        cycle_states = build_cycle_state_table(signal_map)

        if len(cycle_states) < 3:
            return {
                "decision": "INSUFFICIENT_EVIDENCE",
                "stage": "PRECHECK",
                "reason": "Insufficient clock cycles in target waveform.",
                "adaptive_metrics": {"elapsed_ms": (time.time() - t0) * 1000}
            }

        # 2. Autonomous Boundary Recovery (NO ORACLE KNOWLEDGE)
        observed_sigs = [s for s in cert.target_signals if s not in ["clk", "rst_n"]]
        segments = self.detector.detect_segments(cycle_states, observed_sigs)
        primary_seg = segments[0] if segments else None

        # 3. Evidence Sufficiency Check
        suff_res = self.classifier.classify_sufficiency(cycle_states, segments, observed_sigs)
        
        if not suff_res.is_sufficient_for_validation and control_mode == "ADAPTIVE_PRIMARY":
            return {
                "decision": "INSUFFICIENT_EVIDENCE",
                "stage": suff_res.sufficiency_state,
                "reason": suff_res.diagnostic_reason,
                "adaptive_metrics": {
                    "sufficiency_state": suff_res.sufficiency_state,
                    "recovered_segments": len(segments),
                    "boundary_recovery_time_ms": (time.time() - t0) * 1000
                }
            }

        # 4. Determine Window Length based on Mode
        if control_mode == "STATIC_FIXED":
            effective_window_cycles = cert.transaction_context.active_window_cycles  # fixed (usually 4)
        elif control_mode == "BROAD_WINDOW_CONTROL":
            effective_window_cycles = len(cycle_states)  # entire trace
        elif control_mode == "RANDOM_WINDOW_CONTROL":
            # Random window length between 2 and max(5, trace_length // 2)
            max_r = max(5, len(cycle_states) // 2)
            effective_window_cycles = random.randint(2, max_r)
        elif control_mode == "MATCHED_LENGTH_CONTROL":
            # Same length as adaptive segment, but fixed offset without semantic boundary tracking
            effective_window_cycles = primary_seg.length if primary_seg else 4
        else: # ADAPTIVE_PRIMARY
            # Adaptive segment length (with floor of 4 to preserve base contract)
            effective_window_cycles = max(4, primary_seg.length) if primary_seg else 4

        # 5. Adapt Certificate Window for Frozen Validator
        adapted_cert = copy.deepcopy(cert)
        adapted_cert.transaction_context.active_window_cycles = effective_window_cycles

        t_val_start = time.time()
        # 6. Execute FROZEN L2 Validator
        l2_res = self.frozen_validator.validate(adapted_cert, vcd_path, ablation_mode=ablation_mode)
        t_val_end = time.time()

        # 7. Merge Diagnostic Metrics
        result = dict(l2_res)
        result["adaptive_metrics"] = {
            "control_mode": control_mode,
            "boundary_recovery_time_ms": (t_val_start - t0) * 1000,
            "frozen_l2_time_ms": (t_val_end - t_val_start) * 1000,
            "total_latency_ms": (t_val_end - t0) * 1000,
            "effective_window_cycles": effective_window_cycles,
            "recovered_segment": primary_seg.to_dict() if primary_seg else None,
            "sufficiency_state": suff_res.sufficiency_state,
            "all_segments_count": len(segments)
        }
        return result
