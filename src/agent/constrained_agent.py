import random
import uuid
import os
from typing import List, Dict, Any, Optional
from ..trajectory.schema import TrajectoryStep, TrajectorySummary
from ..trajectory.logger import TrajectoryLogger
from ..tools.simulator import VerilogSimulator
from ..tools.waveform import WaveformTool
from ..tools.rtl_search import RTLSearchTool
from ..constraints.schema import NegativeConstraint

class ConstrainedAgent:
    def __init__(self, simulator: VerilogSimulator, waveform: WaveformTool, search: RTLSearchTool, logger: TrajectoryLogger, constraints: List[NegativeConstraint], seed: int = 42, budget: int = 15, lambda_dead_end: float = 1.0, ignore_context: bool = False):
        self.simulator = simulator
        self.waveform = waveform
        self.search = search
        self.logger = logger
        self.budget = budget
        self.rng = random.Random(seed)
        self.constraints = constraints
        self.lambda_dead_end = lambda_dead_end
        self.ignore_context = ignore_context
        self.state = {
            "known_modules": [],
            "known_signals": [],
            "waveform_queried": [],
            "failure_info": "",
            "root_cause_found": False
        }
        self.false_pruning_count = 0
        self.exploration_override_count = 0
        
    def generate_actions(self, task_id: str, ground_truth: Dict[str, Any]) -> List[Dict[str, Any]]:
        actions = []
        if not self.state["failure_info"]:
            actions.append({"type": "run_simulation", "target": task_id, "base_weight": 10.0})
        
        if self.state["failure_info"]:
            actions.append({"type": "inspect_rtl", "target": task_id, "base_weight": 2.0})
            
        for sig in self.state["known_signals"]:
            if sig not in self.state["waveform_queried"]:
                is_root_cause = sig in ground_truth["ground_truth_signals"]
                weight = 1.0 
                
                actions.append({
                    "type": "query_waveform", 
                    "target": sig, 
                    "is_root_cause": is_root_cause,
                    "base_weight": weight
                })
                
        if not actions:
            actions.append({"type": "give_up", "target": "none", "base_weight": 1.0})
            
        return actions

    def score_action(self, action: Dict[str, Any], ground_truth: Dict[str, Any]) -> float:
        score = action.get("base_weight", 1.0)
        
        for c in self.constraints:
            # Check Context
            if not self.ignore_context:
                family = ground_truth.get("family", "")
                symptom = ground_truth.get("symptom", "")
                if c.context.get("design_family") and c.context["design_family"] != family:
                    continue
                if c.context.get("symptom") and c.context["symptom"] != symptom:
                    continue

            # Match pattern
            if c.pattern.get("action") == action["type"]:
                if action["type"] == "query_waveform":
                    target_signals = c.pattern.get("signals", "").split(",")
                    if action["target"] in target_signals:
                        score -= self.lambda_dead_end * c.confidence
                        # Check False pruning
                        if action.get("is_root_cause", False):
                            self.false_pruning_count += 1
                        
        return score

    def select_action(self, available_actions: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> Dict[str, Any]:
        scored_actions = []
        for a in available_actions:
            score = self.score_action(a, ground_truth)
            scored_actions.append((score, a))
        
        # Exploration Override: If all actions are highly penalized (<= 0.1) but we still have budget,
        # we revert to uniform exploration over all actions rather than getting stuck.
        max_score = max([s for s, a in scored_actions]) if scored_actions else 0
        if max_score <= 0.1:
            self.exploration_override_count += 1
            weights = [1.0 for _, a in scored_actions]
        else:
            weights = [max(0.01, s) for s, a in scored_actions]
            
        selected = self.rng.choices(available_actions, weights=weights, k=1)[0]
        return selected

    def run(self, task_id: str, design_family: str, ground_truth: Dict[str, Any], agent_name: str = "constrained") -> str:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        step_num = 0
        waveform_queries = 0
        simulations = 0
        
        while step_num < self.budget and not self.state["root_cause_found"]:
            step_num += 1
            available = self.generate_actions(task_id, ground_truth)
            action = self.select_action(available, ground_truth)
            
            res_success = False
            res_informative = False
            
            if action["type"] == "run_simulation":
                sim_res = self.simulator.run_simulation(task_id, design_family)
                res_success = True
                res_informative = True
                self.state["failure_info"] = sim_res.get("output", "Sim failed")
                simulations += 1
                
            elif action["type"] == "inspect_rtl":
                rtl_res = self.search.inspect_rtl(task_id, task_id)
                if rtl_res["success"]:
                    res_success = True
                    res_informative = True
                    for sig in rtl_res.get("signals", []):
                        if sig not in self.state["known_signals"]:
                            self.state["known_signals"].append(sig)
                            
            elif action["type"] == "query_waveform":
                vcd_path = os.path.join(self.simulator.rtl_dir, f"{task_id}.vcd")
                wf_res = self.waveform.query_waveform(vcd_path, [action["target"]], 0, 1000)
                res_success = wf_res.get("success", False)
                res_informative = res_success
                self.state["waveform_queried"].append(action["target"])
                waveform_queries += 1
                
                if action.get("is_root_cause", False):
                    self.state["root_cause_found"] = True
                    
            elif action["type"] == "give_up":
                break
                
            step = TrajectoryStep(
                run_id=run_id,
                step=step_num,
                task_id=task_id,
                design_family=design_family,
                symptom=ground_truth.get("symptom", "unknown"),
                failure_type=ground_truth.get("bug_class", "unknown"),
                agent=agent_name,
                action=action["type"],
                target_module=action.get("target_module", "top"),
                signals=[action.get("target", "")],
                cycle_start=0,
                cycle_end=1000,
                result_type="success" if res_success else "fail",
                informative=res_informative,
                hypothesis="none",
                cost={"latency_ms": 150, "tool_calls": 1},
                global_outcome="PENDING"
            )
            self.logger.log_step(step)
            
        final_outcome = "SUCCESS" if self.state["root_cause_found"] else "FAIL"
        
        summary = TrajectorySummary(
            run_id=run_id,
            final_outcome=final_outcome,
            root_cause_found=self.state["root_cause_found"],
            steps=step_num,
            tool_calls=step_num,
            waveform_queries=waveform_queries,
            simulations=simulations,
            false_pruning=self.false_pruning_count,
            exploration_overrides=self.exploration_override_count
        )
        self.logger.log_summary(summary)
        return final_outcome
