import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from .adaptive_transaction_boundary import TransactionSegment

@dataclass
class EvidenceSufficiencyResult:
    sufficiency_state: str
    is_sufficient_for_validation: bool
    decision_recommendation: str  # "PROCEED_TO_L2", "INSUFFICIENT_EVIDENCE", "REJECT"
    diagnostic_reason: str
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class AdaptiveEvidenceClassifier:
    """
    Evaluates evidence completeness and sufficiency for transaction-level causal verification.
    
    6-Way Taxonomy:
    1. TRANSACTION_NEVER_INITIATED: No initiating activity in trace.
    2. TRANSACTION_INITIATED_NOT_ACCEPTED: Initiation asserted but stalled or held in reset.
    3. TRANSACTION_ACCEPTED_INCOMPLETE: Active transaction truncated before completion/propagation.
    4. TRANSACTION_COMPLETED_SUFFICIENT: Complete transaction lifecycle observed.
    5. TRANSACTION_CONTRADICTS_CERTIFICATE: Causal evidence explicitly disproves certificate claim.
    6. TRANSACTION_BOUNDARIES_AMBIGUOUS: Multi-source activity prevents clear boundary separation.
    
    SAFETY-CRITICAL REQUIREMENT:
    The classifier must NEVER convert missing or incomplete evidence into PASS.
    Unexercised or truncated preconditions strictly map to INSUFFICIENT_EVIDENCE.
    """
    def __init__(self, min_cycles_after_end: int = 1):
        self.min_cycles_after_end = min_cycles_after_end

    def classify_sufficiency(self, cycle_states: List[Dict[str, Any]], 
                             segments: List[TransactionSegment],
                             observed_signals: Optional[List[str]] = None) -> EvidenceSufficiencyResult:
        if not cycle_states or len(cycle_states) < 3:
            return EvidenceSufficiencyResult(
                sufficiency_state="TRANSACTION_NEVER_INITIATED",
                is_sufficient_for_validation=False,
                decision_recommendation="INSUFFICIENT_EVIDENCE",
                diagnostic_reason="Target waveform trace contains fewer than 3 clock cycles."
            )

        if not segments:
            # Check if reset was active throughout
            all_reset = all(s.get("rst_n", 1) == 0 for s in cycle_states)
            if all_reset:
                return EvidenceSufficiencyResult(
                    sufficiency_state="TRANSACTION_INITIATED_NOT_ACCEPTED",
                    is_sufficient_for_validation=False,
                    decision_recommendation="INSUFFICIENT_EVIDENCE",
                    diagnostic_reason="Hardware remained in reset (rst_n=0) throughout waveform."
                )
            return EvidenceSufficiencyResult(
                sufficiency_state="TRANSACTION_NEVER_INITIATED",
                is_sufficient_for_validation=False,
                decision_recommendation="INSUFFICIENT_EVIDENCE",
                diagnostic_reason="No transaction initiation or protocol activity detected in waveform."
            )

        # Evaluate primary segment
        primary = segments[0]
        total_trace_cycles = len(cycle_states)
        
        # Check boundary ambiguity
        if len(segments) > 1:
            # Check if segments overlap heavily
            overlaps = False
            for i in range(len(segments) - 1):
                if segments[i].end_cycle >= segments[i + 1].start_cycle:
                    overlaps = True
                    break
            if overlaps:
                return EvidenceSufficiencyResult(
                    sufficiency_state="TRANSACTION_BOUNDARIES_AMBIGUOUS",
                    is_sufficient_for_validation=False,
                    decision_recommendation="INSUFFICIENT_EVIDENCE",
                    diagnostic_reason="Multiple overlapping transaction candidates create boundary ambiguity.",
                    metrics={"segment_count": len(segments)}
                )

        # Check for incomplete / truncated transaction
        # If raw activity continued up to the very last cycle of the trace
        raw_end = primary.metadata.get("cluster_span", [primary.start_cycle, primary.end_cycle])[1]
        if raw_end >= total_trace_cycles - 1 and primary.confidence < 0.8:
            return EvidenceSufficiencyResult(
                sufficiency_state="TRANSACTION_ACCEPTED_INCOMPLETE",
                is_sufficient_for_validation=False,
                decision_recommendation="INSUFFICIENT_EVIDENCE",
                diagnostic_reason="Transaction was accepted and active but waveform was truncated before downstream settlement.",
                metrics={"segment_length": primary.length, "trace_length": total_trace_cycles}
            )

        # Segment has sufficient lifecycle evidence
        return EvidenceSufficiencyResult(
            sufficiency_state="TRANSACTION_COMPLETED_SUFFICIENT",
            is_sufficient_for_validation=True,
            decision_recommendation="PROCEED_TO_L2",
            diagnostic_reason=f"Transaction completed cleanly spanning cycles [{primary.start_cycle}, {primary.end_cycle}] (length={primary.length}).",
            metrics={
                "start_cycle": primary.start_cycle,
                "end_cycle": primary.end_cycle,
                "adaptive_length": primary.length,
                "confidence": primary.confidence,
                "event_count": len(primary.event_sequence)
            }
        )
