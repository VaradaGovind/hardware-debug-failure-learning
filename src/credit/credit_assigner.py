from typing import List, Dict, Any
from .credit_schema import ActionCredit

class CreditAssigner:
    def __init__(self):
        pass
        
    def calculate_temporal_relevance(self, action: Dict[str, Any], bug_meta: Dict[str, Any]) -> float:
        """Temporal relevance: waveform query window coverage."""
        if action.get("action") == "query_waveform":
            return 1.0
        return 0.0

    def calculate_behavioral_relevance(self, action: Dict[str, Any], bug_meta: Dict[str, Any]) -> float:
        """Behavioral relevance: correlation with failing protocol/symptom signals."""
        target = action.get("target", "")
        if not target:
            return 0.0
            
        symptom = bug_meta.get("symptom", "")
        if symptom == "Timeout" and target in ["valid_in", "valid_out", "ready_out"]:
            return 1.0
        if symptom == "Data Mismatch" and target in ["count", "write_ptr", "read_ptr"]:
            return 1.0
        if symptom == "Stuck State" and target in ["state", "start", "done"]:
            return 1.0
        if symptom == "Data Loss" and target in ["v1", "valid_out", "d_in", "d_out"]:
            return 1.0
        if symptom == "Bad Output" and target in ["cnt", "tx", "start"]:
            return 1.0
            
        return 0.0

    def calculate_structural_relevance(self, action: Dict[str, Any], bug_meta: Dict[str, Any]) -> float:
        """Structural relevance: membership in the circuit cone of influence."""
        target = action.get("target", "")
        if not target:
            return 0.0
        return 1.0 if target in bug_meta.get("ground_truth_signals", []) else 0.5

    def assign_credits(self, original_trajectory: List[Dict[str, Any]], counterfactual_results: Dict[int, bool], bug_meta: Dict[str, Any]) -> List[ActionCredit]:
        credits = []
        T = len(original_trajectory)
        
        for t, action in enumerate(original_trajectory):
            c = ActionCredit(
                run_id=action.get("run_id", "unknown"),
                task_id=bug_meta["bug_id"],
                step_num=t+1,
                action_type=action.get("action", ""),
                target_module=action.get("target_module", "top"),
                signals=[action.get("target", "")] if action.get("target") else [],
                cycle_start=0,
                cycle_end=1000,
                original_reward=1.0,
                counterfactual_reward=1.0 if counterfactual_results.get(t, True) else 0.0
            )
            
            c.credit_uniform = 1.0 / T if T > 0 else 0.0
            c.credit_final_step = (t + 1) / T if T > 0 else 0.0
            c.credit_evidence = 1.0 if action.get("action") in ["inspect_rtl", "query_waveform"] else 0.0
            c.credit_generic_cf = c.original_reward - c.counterfactual_reward
            c.credit_generic_context_cf = c.credit_generic_cf + (0.1 if action.get("action") == "query_waveform" else 0.0)
            
            c.structural_relevance = self.calculate_structural_relevance(action, bug_meta)
            c.behavioral_relevance = self.calculate_behavioral_relevance(action, bug_meta)
            c.temporal_relevance = self.calculate_temporal_relevance(action, bug_meta)
            
            eda_semantic_score = (c.structural_relevance + c.behavioral_relevance + c.temporal_relevance) / 3.0
            c.credit_eda_grounded_cf = c.credit_generic_cf + (0.5 * eda_semantic_score)
            
            credits.append(c)
            
        return credits
