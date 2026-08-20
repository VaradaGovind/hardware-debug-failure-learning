import os
import json
from typing import Dict, Any, Optional

class AdaptiveReusePolicy:
    """
    Conservative Online Reuse Decision Policy for Adaptive Transaction-Semantic RCA.
    
    Decision Rules:
    - PASS: Safely reuse existing RCA (bypasses expensive independent diagnosis).
    - FAIL: Certificate disproven on target. Fallback to independent RCA.
    - INSUFFICIENT_EVIDENCE: Preconditions or boundaries incomplete. 
                            DO NOT REUSE. Fallback to independent RCA.
    
    SAFETY PRINCIPLE:
    INSUFFICIENT_EVIDENCE is never converted to PASS. It strictly guards against false reuse.
    Zero access to benchmark labels, defect IDs, or ground-truth metadata.
    """
    def __init__(self, validation_cost_calls: float = 2.0, 
                 independent_rca_cost_calls: float = 8.9,
                 cert_extraction_cost_calls: float = 0.6):
        self.validation_cost_calls = validation_cost_calls
        self.independent_rca_cost_calls = independent_rca_cost_calls
        self.cert_extraction_cost_calls = cert_extraction_cost_calls

    def decide(self, validation_result: Any) -> Dict[str, Any]:
        if isinstance(validation_result, str):
            raw_decision = validation_result
            stage = "UNKNOWN"
            reason = ""
        elif isinstance(validation_result, dict):
            raw_decision = validation_result.get("decision", "INSUFFICIENT_EVIDENCE")
            stage = validation_result.get("stage", "UNKNOWN")
            reason = validation_result.get("reason", "")
        else:
            raw_decision = "INSUFFICIENT_EVIDENCE"
            stage = "UNKNOWN"
            reason = ""
        
        if raw_decision == "PASS":
            policy_action = "REUSE_RCA"
            incurred_cost = self.validation_cost_calls
            safe_to_reuse = True
        elif raw_decision == "FAIL":
            policy_action = "FALLBACK_INDEPENDENT_RCA"
            incurred_cost = self.validation_cost_calls + self.independent_rca_cost_calls
            safe_to_reuse = False
        else: # INSUFFICIENT_EVIDENCE
            policy_action = "FALLBACK_INDEPENDENT_RCA"
            incurred_cost = self.validation_cost_calls + self.independent_rca_cost_calls
            safe_to_reuse = False

        return {
            "raw_decision": raw_decision,
            "policy_action": policy_action,
            "safe_to_reuse": safe_to_reuse,
            "stage": stage,
            "reason": reason,
            "incurred_cost_calls": incurred_cost
        }
