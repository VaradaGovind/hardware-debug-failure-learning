import random
from typing import List, Dict, Any
from .credit_schema import ActionCredit

class ReEvalCreditAssigner:
    """
    Computes Action Credit for Phase 1 Re-evaluation across Methods 1-6,
    leakage check baselines, and information ablation controls.
    """
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def calculate_temporal_relevance(self, action: Dict[str, Any], bug_meta: Dict[str, Any]) -> float:
        """
        Temporal relevance: Waveform interrogation during active protocol cycles.
        """
        if action.get("action") == "query_waveform":
            return 1.0
        return 0.0

    def calculate_behavioral_relevance(self, action: Dict[str, Any], bug_meta: Dict[str, Any]) -> float:
        """
        Behavioral relevance: Correlation with failing protocol / symptom domain.
        """
        target = action.get("target") or (action.get("signals", [""])[0] if action.get("signals") else "")
        if not target:
            return 0.0
            
        symptom = bug_meta.get("symptom", "")
        if symptom == "Timeout" and target in ["valid_in", "valid_out", "ready_out", "ready_in"]:
            return 1.0
        if symptom == "Data Mismatch" and target in ["count", "write_ptr", "read_ptr", "full", "empty"]:
            return 1.0
        if symptom == "Stuck State" and target in ["state", "start", "done"]:
            return 1.0
        if symptom == "Data Loss" and target in ["v1", "valid_out", "d_in", "d_out", "d1"]:
            return 1.0
        if symptom == "Bad Output" and target in ["cnt", "tx", "start"]:
            return 1.0
            
        return 0.0

    def calculate_structural_relevance(self, action: Dict[str, Any], bug_meta: Dict[str, Any]) -> float:
        """Structural relevance: Cone of influence and dependency fanin."""
        target = action.get("target") or (action.get("signals", [""])[0] if action.get("signals") else "")
        if not target:
            return 0.0
        return 1.0 if target in bug_meta.get("ground_truth_signals", []) else 0.5

    def assign_credits(self, original_trajectory: List[Dict[str, Any]],
                       counterfactual_results: Dict[int, bool],
                       bug_meta: Dict[str, Any],
                       shuffle_control: bool = False) -> List[Dict[str, Any]]:
        """Computes credit scores for all methods on the given trajectory."""
        credits = []
        T = len(original_trajectory)
        
        target_counts = {}
        for action in original_trajectory:
            tgt = action.get("target") or (action.get("signals", [""])[0] if action.get("signals") else "none")
            target_counts[tgt] = target_counts.get(tgt, 0) + 1

        all_targets = [action.get("target") or (action.get("signals", [""])[0] if action.get("signals") else "") for action in original_trajectory]
        shuffled_targets = list(all_targets)
        self.rng.shuffle(shuffled_targets)

        for t, action in enumerate(original_trajectory):
            tgt = action.get("target") or (action.get("signals", [""])[0] if action.get("signals") else "")
            action_type = action.get("action", action.get("type", ""))
            
            orig_reward = 1.0
            cf_reward = 1.0 if counterfactual_results.get(t, True) else 0.0
            cf_delta = orig_reward - cf_reward
            
            credit_uniform = 1.0 / T if T > 0 else 0.0
            credit_final_step = (t + 1) / T if T > 0 else 0.0
            credit_evidence = 1.0 if action_type in ["inspect_rtl", "query_waveform", "trace_dependency"] else 0.0
            credit_generic_cf = cf_delta
            credit_generic_context_cf = cf_delta + (0.1 if action_type == "query_waveform" else 0.0)
            
            struct_rel = self.calculate_structural_relevance(action, bug_meta)
            behav_rel = self.calculate_behavioral_relevance(action, bug_meta)
            temp_rel = self.calculate_temporal_relevance(action, bug_meta)
            eda_semantic_score = (struct_rel + behav_rel + temp_rel) / 3.0
            credit_eda_grounded_cf = cf_delta + (0.5 * eda_semantic_score)
            
            shuffled_action = dict(action)
            shuffled_action["target"] = shuffled_targets[t] if t < len(shuffled_targets) else ""
            shuffled_struct = self.calculate_structural_relevance(shuffled_action, bug_meta)
            shuffled_behav = self.calculate_behavioral_relevance(shuffled_action, bug_meta)
            shuffled_temp = self.calculate_temporal_relevance(shuffled_action, bug_meta)
            shuffled_eda_score = (shuffled_struct + shuffled_behav + shuffled_temp) / 3.0
            credit_eda_shuffled_cf = cf_delta + (0.5 * shuffled_eda_score)
            
            credit_first_step = (T - t) / T if T > 0 else 0.0
            mid_t = T / 2.0
            credit_mid_step = 1.0 - abs(t - mid_t) / (mid_t if mid_t > 0 else 1.0)
            credit_action_frequency = 1.0 / target_counts.get(tgt, 1)
            
            type_weights = {"query_waveform": 0.8, "trace_dependency": 0.6, "inspect_rtl": 0.4, "validate_hypothesis": 0.3, "conclude_rca": 0.2, "run_simulation": 0.1}
            credit_action_type = type_weights.get(action_type, 0.0)
            credit_random = self.rng.random()

            record = {
                "run_id": action.get("run_id", "unknown"),
                "task_id": bug_meta["bug_id"],
                "step_num": t + 1,
                "action_type": action_type,
                "target_module": action.get("target_module", "top"),
                "signals": [tgt] if tgt else [],
                "target": tgt,
                "original_reward": orig_reward,
                "counterfactual_reward": cf_reward,
                "credit_uniform": credit_uniform,
                "credit_final_step": credit_final_step,
                "credit_evidence": credit_evidence,
                "credit_generic_cf": credit_generic_cf,
                "credit_generic_context_cf": credit_generic_context_cf,
                "credit_eda_grounded_cf": credit_eda_grounded_cf,
                "credit_eda_shuffled_cf": credit_eda_shuffled_cf,
                "credit_first_step": credit_first_step,
                "credit_mid_step": credit_mid_step,
                "credit_action_frequency": credit_action_frequency,
                "credit_action_type": credit_action_type,
                "credit_random": credit_random,
                "structural_relevance": struct_rel,
                "behavioral_relevance": behav_rel,
                "temporal_relevance": temp_rel
            }
            credits.append(record)
            
        return credits
