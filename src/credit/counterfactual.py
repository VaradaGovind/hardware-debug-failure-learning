from typing import Dict, Any, List
from ..agent.baseline_agent import BaselineAgent
from ..tools.simulator import VerilogSimulator
from ..tools.waveform import WaveformTool
from ..tools.rtl_search import RTLSearchTool
from ..trajectory.logger import TrajectoryLogger

class CounterfactualAgent(BaselineAgent):
    def __init__(self, simulator: VerilogSimulator, waveform: WaveformTool, search: RTLSearchTool, 
                 logger: TrajectoryLogger, seed: int, budget: int, skip_action: Dict[str, Any]):
        super().__init__(simulator, waveform, search, logger, seed, budget)
        self.skip_action = skip_action
        
    def generate_actions(self, task_id: str, ground_truth: Dict[str, Any]) -> List[Dict[str, Any]]:
        actions = super().generate_actions(task_id, ground_truth)
        
        # Filter out the skipped action
        filtered = []
        for a in actions:
            # We match by type and target
            if a["type"] == self.skip_action.get("action") and a.get("target") == self.skip_action.get("target"):
                continue
            filtered.append(a)
            
        if not filtered:
            filtered.append({"type": "give_up", "target": "none", "base_weight": 1.0})
            
        return filtered

class ReplayEngine:
    def __init__(self, simulator: VerilogSimulator, waveform: WaveformTool, search: RTLSearchTool):
        self.simulator = simulator
        self.waveform = waveform
        self.search = search
        
    def run_counterfactual(self, bug: Dict[str, Any], seed: int, skip_action: Dict[str, Any], logger: TrajectoryLogger) -> bool:
        """
        Runs a counterfactual simulation where the specified action is globally banned.
        Returns True if the root cause was still found, False otherwise.
        """
        # Re-initialize agent with the counterfactual restriction
        agent = CounterfactualAgent(
            simulator=self.simulator,
            waveform=self.waveform,
            search=self.search,
            logger=logger,
            seed=seed,
            budget=6, # Standard budget for this benchmark
            skip_action=skip_action
        )
        
        final_outcome = agent.run(bug["bug_id"], bug["family"], bug)
        return final_outcome == "SUCCESS"
