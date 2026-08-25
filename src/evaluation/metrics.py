import json
import os
import pandas as pd
from typing import List, Dict

class MetricsCalculator:
    def __init__(self, raw_results_dir: str):
        self.raw_results_dir = raw_results_dir

    def calculate_metrics(self) -> pd.DataFrame:
        metrics = []
        for file in os.listdir(self.raw_results_dir):
            if file.endswith("_summary.json"):
                with open(os.path.join(self.raw_results_dir, file), "r") as f:
                    summary = json.load(f)
                    run_id = summary["run_id"]
                    agent_type = "unknown"
                    try:
                        with open(os.path.join(self.raw_results_dir, f"{run_id}.jsonl"), "r") as lf:
                            first_step = json.loads(lf.readline())
                            agent_type = first_step["agent"]
                    except:
                        pass
                        
                    metrics.append({
                        "run_id": summary["run_id"],
                        "agent": agent_type,
                        "success": 1 if summary["final_outcome"] == "SUCCESS" else 0,
                        "tool_calls": summary["tool_calls"],
                        "waveform_queries": summary["waveform_queries"]
                    })
        return pd.DataFrame(metrics)

    def calculate_davr(self, baseline_df, constrained_df) -> float:
        """Computes Dead-End Avoidance Rate (DAVR) relative to baseline failures."""
        baseline_fails = baseline_df[baseline_df['success'] == 0]
        constrained_fails = constrained_df[constrained_df['success'] == 0]
        
        if len(baseline_fails) == 0:
            return 0.0
            
        if len(constrained_fails) == 0:
            return 1.0
            
        davr = 1.0 - (len(constrained_fails) / len(baseline_fails))
        return davr

