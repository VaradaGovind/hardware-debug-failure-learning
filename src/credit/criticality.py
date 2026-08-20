import json
import os
from typing import Dict, Any

class OracleCriticality:
    def __init__(self, bugs_meta_path: str):
        with open(bugs_meta_path, 'r') as f:
            bugs = json.load(f)
        self.bugs_dict = {b["bug_id"]: b for b in bugs}
        
    def evaluate_criticality(self, action: Dict[str, Any], task_id: str) -> str:
        """
        Determines the ground-truth criticality of an action.
        This represents the Oracle knowledge and should ONLY be used for evaluation,
        never as a feature during runtime credit assignment.
        """
        if task_id not in self.bugs_dict:
            return "unknown"
            
        bug_meta = self.bugs_dict[task_id]
        
        action_type = action.get("action", action.get("type"))
        
        # Actions that don't target specific signals/modules are non-critical baseline setup
        if action_type in ["run_simulation", "give_up", "inspect_failure"]:
            return "non-critical"
            
        # For RTL or waveform inspection, check if they hit the ground truth module/signals
        target_signals = action.get("signals", [])
        if isinstance(target_signals, str):
            target_signals = [target_signals]
            
        gt_signals = bug_meta.get("ground_truth_signals", [])
        
        # If any target signal is exactly the ground truth signal, it's critical
        for sig in target_signals:
            if sig in gt_signals:
                return "critical"
                
        # If they are inspecting something completely unrelated, we call it non-critical
        return "non-critical"
