import json
import os
import uuid
from typing import List, Dict, Any
from ..constraints.schema import NegativeConstraint

class PatternMiner:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir

    def mine_constraints(self, source: str = "both", confidence_threshold: float = 0.8) -> List[NegativeConstraint]:
        failed_runs = []
        successful_runs = []
        
        for file in os.listdir(self.log_dir):
            if file.endswith("_summary.json"):
                with open(os.path.join(self.log_dir, file), "r") as f:
                    summary = json.load(f)
                    
                    # Only mine constraints from training set instances
                    run_id = summary["run_id"]
                    try:
                        with open(os.path.join(self.log_dir, f"{run_id}.jsonl"), "r") as lfile:
                            line1 = json.loads(lfile.readline())
                            task_id = line1["task_id"]
                            if task_id not in ["fifo_b1", "fifo_b2", "fifo_b3", "fifo_b4"]:
                                continue
                    except:
                        continue

                    if summary["final_outcome"] == "FAIL":
                        failed_runs.append(run_id)
                    else:
                        successful_runs.append(run_id)
        
        action_counts = {}
        
        mining_runs = []
        if source in ["negative", "both"]:
            mining_runs.extend(failed_runs)
        if source in ["positive", "both"]:
            mining_runs.extend(successful_runs)
            
        for run_id in mining_runs:
            with open(os.path.join(self.log_dir, f"{run_id}.jsonl"), "r") as f:
                for line in f:
                    step = json.loads(line)
                    sig = f"{step['action']}:{step['target_module']}:{','.join(step['signals'])}"
                    family = step.get('design_family', 'unknown')
                    symptom = step.get('symptom', 'unknown')
                    
                    if sig not in action_counts:
                        action_counts[sig] = {"count": 0, "runs": set(), "family": family, "symptom": symptom}
                    action_counts[sig]["count"] += 1
                    action_counts[sig]["runs"].add(run_id)

        constraints = []
        for sig, stats in action_counts.items():
            action_type, module, signals = sig.split(":")
            
            success_occurrences = 0
            for run_id in successful_runs:
                with open(os.path.join(self.log_dir, f"{run_id}.jsonl"), "r") as f:
                    for line in f:
                        step = json.loads(line)
                        if f"{step['action']}:{step['target_module']}:{','.join(step['signals'])}" == sig:
                            success_occurrences += 1
            
            fail_count = stats["count"]
            if source == "positive":
                if fail_count > success_occurrences:
                    confidence = 0.5
                else:
                    continue
            else:
                if success_occurrences == 0 and fail_count > 2:
                    confidence = 0.95
                elif fail_count > success_occurrences * 2:
                    confidence = 0.8
                else:
                    continue
            
            if confidence >= confidence_threshold:
                c = NegativeConstraint(
                    constraint_id=f"NC_{uuid.uuid4().hex[:6]}",
                    context={
                        "design_family": stats["family"],
                        "symptom": stats["symptom"]
                    },
                    pattern={
                        "action": action_type,
                        "target_module": module,
                        "signals": signals
                    },
                    effect="DEPRIORITIZE",
                    confidence=confidence,
                    support_count=stats["count"],
                    false_positive_count=success_occurrences,
                    source_runs=list(stats["runs"])
                )
                constraints.append(c)
                
        return constraints
