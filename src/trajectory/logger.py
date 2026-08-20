import json
import os
from typing import List, Dict, Any
from .schema import TrajectoryStep, TrajectorySummary

class TrajectoryLogger:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.steps: List[TrajectoryStep] = []
        self.summary: TrajectorySummary = None

    def log_step(self, step: TrajectoryStep):
        self.steps.append(step)

    def log_summary(self, summary: TrajectorySummary):
        self.summary = summary
        # update all steps with final outcome
        for step in self.steps:
            step.global_outcome = summary.final_outcome
        
        self._flush(summary.run_id)

    def _flush(self, run_id: str):
        # Write steps to JSONL
        filepath = os.path.join(self.log_dir, f"{run_id}.jsonl")
        with open(filepath, 'w') as f:
            for step in self.steps:
                f.write(json.dumps(step.__dict__) + "\n")
        
        # Write summary to JSON
        summary_filepath = os.path.join(self.log_dir, f"{run_id}_summary.json")
        with open(summary_filepath, 'w') as f:
            json.dump(self.summary.__dict__, f, indent=2)
            
        self.steps = []
        self.summary = None
