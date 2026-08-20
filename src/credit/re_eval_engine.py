import os
import json
from typing import Dict, Any, List, Optional
from ..agent.re_eval_agents import ModelA_WeakHeuristicAgent, ModelB_StrongCausalAgent
from ..tools.simulator import VerilogSimulator
from ..tools.waveform import WaveformTool
from ..tools.rtl_search import RTLSearchTool
from ..trajectory.logger import TrajectoryLogger

class AdaptiveReplayEngine:
    """
    Adaptive Counterfactual Replay Engine (Information Necessity Semantics).
    
    When an investigative action a_t (action type + target signal) is counterfactually ablated:
    - The agent is re-instantiated with that action/signal banned.
    - The agent is allowed to adaptively re-plan and explore alternative paths using its budget.
    - If the agent fails to reach a verified correct RCA without that information, R_cf(a_t) = 0.
    - If the agent still successfully finds and validates the RCA, R_cf(a_t) = 1.
    """
    def __init__(self, simulator: VerilogSimulator, waveform: WaveformTool, search: RTLSearchTool):
        self.simulator = simulator
        self.waveform = waveform
        self.search = search

    def run_counterfactual_replay(self, model_type: str, bug_meta: Dict[str, Any], seed: int,
                                  banned_action: Dict[str, Any], logger: TrajectoryLogger) -> bool:
        """
        Runs adaptive counterfactual replay for a specific banned action.
        Returns True if the agent still successfully achieves verified RCA, False otherwise.
        """
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
    """
    Independent Ground-Truth Criticality Oracle.
    
    Derives ground truth directly from injected defect metadata:
    - An action is critical if it is the causal investigative query (query_waveform or direct causal dependency trace)
      targeting the ground-truth defect signal.
    - Generic setup (simulation), exploratory distractors on non-bug signals, and terminal administrative steps
      (validation check, RCA conclusion emission) are non-critical.
    - Ground truth is strictly independent of step position, trajectory length, agent method outputs, or runtime heuristics.
    """
    def __init__(self, bugs_meta_path: str):
        with open(bugs_meta_path, 'r') as f:
            bugs = json.load(f)
        self.bugs_dict = {b["bug_id"]: b for b in bugs}

    def evaluate_criticality(self, action: Dict[str, Any], task_id: str) -> str:
        if task_id not in self.bugs_dict:
            return "non-critical"
            
        bug_meta = self.bugs_dict[task_id]
        action_type = action.get("action", action.get("type", ""))
        
        # Setup and administrative conclusion actions are non-critical
        if action_type in ["run_simulation", "give_up", "inspect_failure", "validate_hypothesis", "conclude_rca"]:
            return "non-critical"
            
        # Target signals
        target_signals = action.get("signals", [])
        if isinstance(target_signals, str):
            target_signals = [target_signals]
        elif not target_signals and action.get("target"):
            target_signals = [action.get("target")]
            
        gt_signals = bug_meta.get("ground_truth_signals", [])
        
        # An action is genuinely critical if it is an investigative query (e.g. query_waveform) targeting the ground truth signal
        if action_type in ["query_waveform", "trace_dependency"]:
            for sig in target_signals:
                if sig in gt_signals:
                    return "critical"
                
        return "non-critical"
