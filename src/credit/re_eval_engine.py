import os
import json
from typing import Dict, Any, List, Optional
from ..agent.re_eval_agents import ModelA_WeakHeuristicAgent, ModelB_StrongCausalAgent
from ..tools.simulator import VerilogSimulator
from ..tools.waveform import WaveformTool
from ..tools.rtl_search import RTLSearchTool
from ..trajectory.logger import TrajectoryLogger

class AdaptiveReplayEngine:
    """Replay engine for counterfactual ablation of investigative actions."""
    def __init__(self, simulator: VerilogSimulator, waveform: WaveformTool, search: RTLSearchTool):
        self.simulator = simulator
        self.waveform = waveform
        self.search = search

    def run_counterfactual_replay(self, model_type: str, bug_meta: Dict[str, Any], seed: int,
                                  banned_action: Dict[str, Any], logger: TrajectoryLogger) -> bool:
        """Runs counterfactual replay with a banned action to evaluate necessity."""
        budget = 12
        if model_type == "model_a_weak_heuristic":
            agent = ModelA_WeakHeuristicAgent(
                simulator=self.simulator,
                waveform=self.waveform,
                search=self.search,
                logger=logger,
                seed=seed,
                budget=budget,
                banned_actions=[banned_action]
            )
        else:
            agent = ModelB_StrongCausalAgent(
                simulator=self.simulator,
                waveform=self.waveform,
                search=self.search,
                logger=logger,
                seed=seed,
                budget=budget,
                banned_actions=[banned_action]
            )
            
        outcome = agent.run(bug_meta["bug_id"], bug_meta["family"], bug_meta)
        return outcome == "SUCCESS"


class IndependentOracleCriticality:
    """Ground-truth criticality evaluation using defect manifests."""
    def __init__(self, bugs_meta_path: str):
        with open(bugs_meta_path, 'r') as f:
            bugs = json.load(f)
        self.bugs_dict = {b["bug_id"]: b for b in bugs}

    def evaluate_criticality(self, action: Dict[str, Any], task_id: str) -> str:
        if task_id not in self.bugs_dict:
            return "non-critical"
            
        bug_meta = self.bugs_dict[task_id]
        action_type = action.get("action", action.get("type", ""))
        
        if action_type in ["run_simulation", "give_up", "inspect_failure", "validate_hypothesis", "conclude_rca"]:
            return "non-critical"
            
        target_signals = action.get("signals", [])
        if isinstance(target_signals, str):
            target_signals = [target_signals]
        elif not target_signals and action.get("target"):
            target_signals = [action.get("target")]
            
        gt_signals = bug_meta.get("ground_truth_signals", [])
        if action_type in ["query_waveform", "trace_dependency"]:
            for sig in target_signals:
                if sig in gt_signals:
                    return "critical"
                
        return "non-critical"
