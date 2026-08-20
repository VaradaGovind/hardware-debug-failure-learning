import random
import uuid
import os
from typing import List, Dict, Any, Optional
from ..trajectory.schema import TrajectoryStep, TrajectorySummary
from ..trajectory.logger import TrajectoryLogger
from ..tools.simulator import VerilogSimulator
from ..tools.waveform import WaveformTool
from ..tools.rtl_search import RTLSearchTool

class BaselineAgent:
    def __init__(self, simulator: VerilogSimulator, waveform: WaveformTool, search: RTLSearchTool, logger: TrajectoryLogger, seed: int = 42, budget: int = 15):
        self.simulator = simulator
        self.waveform = waveform
        self.search = search
        self.logger = logger
        self.budget = budget
        self.rng = random.Random(seed)
        self.state = {
            "known_modules": [],
            "known_signals": [],
            "waveform_queried": [],
            "failure_info": "",
            "root_cause_found": False
        }
        
    def generate_actions(self, task_id: str, ground_truth: Dict[str, Any]) -> List[Dict[str, Any]]:
        actions = []
        # Base actions
        if not self.state["failure_info"]:
            actions.append({"type": "run_simulation", "target": task_id, "base_weight": 10.0})
        
        # RTL Inspection
        if self.state["failure_info"]:
            actions.append({"type": "inspect_rtl", "target": task_id, "base_weight": 2.0})
            
        # Waveform querying
        for sig in self.state["known_signals"]:
            if sig not in self.state["waveform_queried"]:
                # The agent should sometimes pick the right signal and sometimes pick the wrong signal
                is_root_cause = sig in ground_truth["ground_truth_signals"]
                weight = 1.0 # Removed the artificial 1.5 weight skew to prevent leakage
                
                actions.append({
                    "type": "query_waveform", 
                    "target": sig, 
                    "is_root_cause": is_root_cause,
                    "base_weight": weight
                })
                
        # If no actions available or we exhausted useful things
        if not actions:
            actions.append({"type": "give_up", "target": "none", "base_weight": 1.0})
            
        return actions

    def select_action(self, available_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        weights = [a.get("base_weight", 1.0) for a in available_actions]
        selected = self.rng.choices(available_actions, weights=weights, k=1)[0]
        return selected

    def run(self, task_id: str, design_family: str, ground_truth: Dict[str, Any]) -> str:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        step_num = 0
        waveform_queries = 0
        simulations = 0
        
        while step_num < self.budget and not self.state["root_cause_found"]:
            step_num += 1
            available = self.generate_actions(task_id, ground_truth)
            action = self.select_action(available)
            
            res_success = False
            res_informative = False
            
            # Execute action
            if action["type"] == "run_simulation":
                sim_res = self.simulator.run_simulation(task_id, design_family)
                res_success = True
                res_informative = True
                self.state["failure_info"] = sim_res.get("output", "Sim failed")
                simulations += 1
                
            elif action["type"] == "inspect_rtl":
                rtl_res = self.search.inspect_rtl(task_id, task_id) # module name is task_id for simplicity here
                if rtl_res["success"]:
                    res_success = True
                    res_informative = True
                    # Add discovered signals to state
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
                
            # Log
            step = TrajectoryStep(
                run_id=run_id,
                step=step_num,
                task_id=task_id,
                design_family=design_family,
                symptom=ground_truth.get("symptom", "unknown"),
                failure_type=ground_truth.get("bug_class", "unknown"),
                agent="baseline",
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
            simulations=simulations
        )
        self.logger.log_summary(summary)
        return final_outcome
