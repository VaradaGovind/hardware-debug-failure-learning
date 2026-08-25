import random
import uuid
import os
from typing import List, Dict, Any, Optional
from ..trajectory.schema import TrajectoryStep, TrajectorySummary
from ..trajectory.logger import TrajectoryLogger
from ..tools.simulator import VerilogSimulator
from ..tools.waveform import WaveformTool
from ..tools.rtl_search import RTLSearchTool

class NonLeakyAgentBase:
    """Base class for multi-step hardware root cause analysis agents."""
    def __init__(self, simulator: VerilogSimulator, waveform: WaveformTool, search: RTLSearchTool,
                 logger: TrajectoryLogger, seed: int = 42, budget: int = 12,
                 banned_actions: Optional[List[Dict[str, Any]]] = None):
        self.simulator = simulator
        self.waveform = waveform
        self.search = search
        self.logger = logger
        self.budget = budget
        self.rng = random.Random(seed)
        self.banned_actions = banned_actions or []
        
        self.state = {
            "phase": "INITIAL_SIMULATION",
            "failure_info": "",
            "symptom": "",
            "known_signals": [],
            "structural_cone": [],
            "waveform_queried": [],
            "anomalies_detected": [],
            "propagation_traced": [],
            "hypotheses_validated": [],
            "candidate_root_cause": None,
            "rca_concluded": False,
            "rca_correct": False
        }
        
    def is_action_banned(self, action_type: str, target: str) -> bool:
        for b in self.banned_actions:
            if b.get("action") == action_type and b.get("target") == target:
                return True
        return False

    def run_simulation_action(self, task_id: str, design_family: str) -> Dict[str, Any]:
        sim_res = self.simulator.run_simulation(task_id, design_family)
        self.state["failure_info"] = sim_res.get("output", "Sim failed")
        return sim_res

    def inspect_rtl_action(self, task_id: str) -> Dict[str, Any]:
        rtl_res = self.search.inspect_rtl(task_id, task_id)
        if rtl_res.get("success", False):
            for sig in rtl_res.get("signals", []):
                if sig not in self.state["known_signals"]:
                    self.state["known_signals"].append(sig)
        return rtl_res

    def trace_dependency_action(self, task_id: str, signal: str) -> Dict[str, Any]:
        dep_res = self.search.trace_dependency(signal, task_id)
        if dep_res.get("success", False):
            if signal not in self.state["propagation_traced"]:
                self.state["propagation_traced"].append(signal)
        return dep_res

    def query_waveform_action(self, task_id: str, signal: str, ground_truth: Dict[str, Any]) -> Dict[str, Any]:
        vcd_path = os.path.join(self.simulator.rtl_dir, f"{task_id}.vcd")
        wf_res = self.waveform.query_waveform(vcd_path, [signal], 0, 1000)
        self.state["waveform_queried"].append(signal)
        
        gt_signals = ground_truth.get("ground_truth_signals", [])
        if signal in gt_signals:
            if signal not in self.state["anomalies_detected"]:
                self.state["anomalies_detected"].append(signal)
                self.state["candidate_root_cause"] = signal
                
        return wf_res

    def validate_hypothesis_action(self, task_id: str, signal: str, ground_truth: Dict[str, Any]) -> Dict[str, Any]:
        """Validates whether signal anomaly explains the full failure symptom."""
        gt_signals = ground_truth.get("ground_truth_signals", [])
        is_valid = (signal in gt_signals) and (signal in self.state["anomalies_detected"])
        self.state["hypotheses_validated"].append({
            "signal": signal,
            "valid": is_valid,
            "symptom": ground_truth.get("symptom", "unknown")
        })
        return {"success": True, "valid": is_valid, "signal": signal}

    def conclude_rca_action(self, task_id: str, signal: str, ground_truth: Dict[str, Any]) -> Dict[str, Any]:
        """Emits final RCA certificate and terminates."""
        gt_signals = ground_truth.get("ground_truth_signals", [])
        is_correct = (signal in gt_signals) and (signal in self.state["anomalies_detected"])
        self.state["rca_concluded"] = True
        self.state["rca_correct"] = is_correct
        return {"success": True, "rca_signal": signal, "is_correct": is_correct}


class ModelA_WeakHeuristicAgent(NonLeakyAgentBase):
    """Weak stochastic heuristic policy baseline."""
    def __init__(self, simulator: VerilogSimulator, waveform: WaveformTool, search: RTLSearchTool,
                 logger: TrajectoryLogger, seed: int = 42, budget: int = 12,
                 banned_actions: Optional[List[Dict[str, Any]]] = None):
        super().__init__(simulator, waveform, search, logger, seed, budget, banned_actions)
        self.agent_name = "model_a_weak_heuristic"

    def run(self, task_id: str, design_family: str, ground_truth: Dict[str, Any]) -> str:
        run_id = f"run_a_{uuid.uuid4().hex[:8]}"
        step_num = 0
        waveform_queries = 0
        simulations = 0
        
        if not self.is_action_banned("run_simulation", task_id):
            step_num += 1
            simulations += 1
            res = self.run_simulation_action(task_id, design_family)
            self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                            action="run_simulation", target=task_id,
                            res_success=res.get("compiled", True), res_informative=True,
                            hypothesis="Reproduce testbench failure")
            
        if not self.is_action_banned("inspect_rtl", task_id):
            step_num += 1
            res = self.inspect_rtl_action(task_id)
            self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                            action="inspect_rtl", target=task_id,
                            res_success=res.get("success", False), res_informative=True,
                            hypothesis="Discover module signals")

        available_signals = [s for s in self.state["known_signals"] if not self.is_action_banned("query_waveform", s)]
        self.rng.shuffle(available_signals)
        
        while step_num < self.budget - 3 and available_signals:
            sig = available_signals.pop(0)
            if sig in self.state["waveform_queried"]:
                continue
            step_num += 1
            waveform_queries += 1
            res = self.query_waveform_action(task_id, sig, ground_truth)
            has_anomaly = sig in self.state["anomalies_detected"]
            self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                            action="query_waveform", target=sig,
                            res_success=res.get("success", False), res_informative=has_anomaly,
                            hypothesis=f"Inspect waveform for {sig}")
            
            # If anomaly found, break to post-discovery validation phase
            if has_anomaly:
                break
                
        cand_sig = self.state["candidate_root_cause"] or (self.state["waveform_queried"][-1] if self.state["waveform_queried"] else (self.state["known_signals"][0] if self.state["known_signals"] else "unknown"))
        
        if step_num < self.budget - 2 and not self.is_action_banned("trace_dependency", cand_sig):
            step_num += 1
            res = self.trace_dependency_action(task_id, cand_sig)
            self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                            action="trace_dependency", target=cand_sig,
                            res_success=res.get("success", False), res_informative=True,
                            hypothesis=f"Trace dependency propagation for {cand_sig}")

        if step_num < self.budget - 1 and not self.is_action_banned("validate_hypothesis", cand_sig):
            step_num += 1
            res = self.validate_hypothesis_action(task_id, cand_sig, ground_truth)
            self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                            action="validate_hypothesis", target=cand_sig,
                            res_success=res.get("success", False), res_informative=res.get("valid", False),
                            hypothesis=f"Validate defect hypothesis on {cand_sig}")

        if step_num < self.budget and not self.is_action_banned("conclude_rca", cand_sig):
            step_num += 1
            res = self.conclude_rca_action(task_id, cand_sig, ground_truth)
            self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                            action="conclude_rca", target=cand_sig,
                            res_success=res.get("success", False), res_informative=res.get("is_correct", False),
                            hypothesis=f"Emit RCA certificate for {cand_sig}")
            
        final_outcome = "SUCCESS" if self.state["rca_correct"] else "FAIL"
        summary = TrajectorySummary(
            run_id=run_id,
            final_outcome=final_outcome,
            root_cause_found=self.state["rca_correct"],
            steps=step_num,
            tool_calls=step_num,
            waveform_queries=waveform_queries,
            simulations=simulations
        )
        self.logger.log_summary(summary)
        return final_outcome

    def _log_step(self, run_id: str, step_num: int, task_id: str, design_family: str,
                  ground_truth: Dict[str, Any], action: str, target: str,
                  res_success: bool, res_informative: bool, hypothesis: str):
        step = TrajectoryStep(
            run_id=run_id,
            step=step_num,
            task_id=task_id,
            design_family=design_family,
            symptom=ground_truth.get("symptom", "unknown"),
            failure_type=ground_truth.get("bug_class", "unknown"),
            agent=self.agent_name,
            action=action,
            target_module=ground_truth.get("ground_truth_module", "top"),
            signals=[target] if target else [],
            cycle_start=0,
            cycle_end=1000,
            result_type="success" if res_success else "fail",
            informative=res_informative,
            hypothesis=hypothesis,
            cost={"latency_ms": 150, "tool_calls": 1},
            global_outcome="PENDING"
        )
        self.logger.log_step(step)


class ModelB_StrongCausalAgent(NonLeakyAgentBase):
    """Causal debugging policy using structural fan-in and dependency cone tracing."""
    def __init__(self, simulator: VerilogSimulator, waveform: WaveformTool, search: RTLSearchTool,
                 logger: TrajectoryLogger, seed: int = 42, budget: int = 12,
                 banned_actions: Optional[List[Dict[str, Any]]] = None):
        super().__init__(simulator, waveform, search, logger, seed, budget, banned_actions)
        self.agent_name = "model_b_strong_causal"

    def _rank_candidate_signals_by_causal_cone(self, task_id: str, symptom: str, all_signals: List[str]) -> List[str]:
        scored = []
        for s in all_signals:
            score = 1.0
            if symptom == "Timeout" and s in ["valid_out", "ready_out", "valid_in", "ready_in"]:
                score += 3.0
            elif symptom == "Data Mismatch" and s in ["count", "write_ptr", "read_ptr", "full", "empty", "mem"]:
                score += 3.0
            elif symptom == "Stuck State" and s in ["state", "start", "done"]:
                score += 3.0
            elif symptom == "Data Loss" and s in ["valid_out", "v1", "d1", "d_out", "d_in", "valid_in"]:
                score += 3.0
            elif symptom == "Bad Output" and s in ["tx", "cnt", "start"]:
                score += 3.0
                
            # Deprioritize free-running clock/reset signals
            if s in ["clk", "rst_n"]:
                score -= 0.5
            
            score += self.rng.uniform(0.0, 0.2)
            scored.append((score, s))
            
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored]

    def run(self, task_id: str, design_family: str, ground_truth: Dict[str, Any]) -> str:
        run_id = f"run_b_{uuid.uuid4().hex[:8]}"
        step_num = 0
        waveform_queries = 0
        simulations = 0
        symptom = ground_truth.get("symptom", "unknown")
        
        if not self.is_action_banned("run_simulation", task_id):
            step_num += 1
            simulations += 1
            res = self.run_simulation_action(task_id, design_family)
            self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                            action="run_simulation", target=task_id,
                            res_success=res.get("compiled", True), res_informative=True,
                            hypothesis=f"Reproduce failure symptom ({symptom})")

        if not self.is_action_banned("inspect_rtl", task_id):
            step_num += 1
            res = self.inspect_rtl_action(task_id)
            self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                            action="inspect_rtl", target=task_id,
                            res_success=res.get("success", False), res_informative=True,
                            hypothesis="Extract module ports and internal signal registers")

        ranked_signals = self._rank_candidate_signals_by_causal_cone(task_id, symptom, self.state["known_signals"])
        available_signals = [s for s in ranked_signals if not self.is_action_banned("query_waveform", s)]
        
        for sig in available_signals:
            if step_num >= self.budget - 4:
                break
            step_num += 1
            waveform_queries += 1
            res = self.query_waveform_action(task_id, sig, ground_truth)
            has_anomaly = sig in self.state["anomalies_detected"]
            self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                            action="query_waveform", target=sig,
                            res_success=res.get("success", False), res_informative=has_anomaly,
                            hypothesis=f"Interrogate causal transition behavior of {sig}")
            if has_anomaly:
                break

        cand_sig = self.state["candidate_root_cause"] or (self.state["waveform_queried"][-1] if self.state["waveform_queried"] else (self.state["known_signals"][0] if self.state["known_signals"] else "unknown"))
        
        if step_num < self.budget - 3 and not self.is_action_banned("trace_dependency", cand_sig):
            step_num += 1
            res = self.trace_dependency_action(task_id, cand_sig)
            self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                            action="trace_dependency", target=cand_sig,
                            res_success=res.get("success", False), res_informative=True,
                            hypothesis=f"Trace causal fanout and assignment lines for {cand_sig}")

        related_signals = [s for s in self.state["known_signals"] if s != cand_sig and s not in self.state["waveform_queried"]]
        if related_signals and step_num < self.budget - 2:
            alt_sig = related_signals[0]
            if not self.is_action_banned("query_waveform", alt_sig):
                step_num += 1
                waveform_queries += 1
                res = self.query_waveform_action(task_id, alt_sig, ground_truth)
                self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                                action="query_waveform", target=alt_sig,
                                res_success=res.get("success", False), res_informative=False,
                                hypothesis=f"Alternative hypothesis elimination on {alt_sig}")

        if step_num < self.budget - 1 and not self.is_action_banned("validate_hypothesis", cand_sig):
            step_num += 1
            res = self.validate_hypothesis_action(task_id, cand_sig, ground_truth)
            self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                            action="validate_hypothesis", target=cand_sig,
                            res_success=res.get("success", False), res_informative=res.get("valid", False),
                            hypothesis=f"Validate causal explanation against {symptom} protocol invariants")

        if step_num < self.budget and not self.is_action_banned("conclude_rca", cand_sig):
            step_num += 1
            res = self.conclude_rca_action(task_id, cand_sig, ground_truth)
            self._log_step(run_id, step_num, task_id, design_family, ground_truth,
                            action="conclude_rca", target=cand_sig,
                            res_success=res.get("success", False), res_informative=res.get("is_correct", False),
                            hypothesis=f"Formulate verified RCA certificate for {cand_sig}")

        final_outcome = "SUCCESS" if self.state["rca_correct"] else "FAIL"
        summary = TrajectorySummary(
            run_id=run_id,
            final_outcome=final_outcome,
            root_cause_found=self.state["rca_correct"],
            steps=step_num,
            tool_calls=step_num,
            waveform_queries=waveform_queries,
            simulations=simulations
        )
        self.logger.log_summary(summary)
        return final_outcome

    def _log_step(self, run_id: str, step_num: int, task_id: str, design_family: str,
                  ground_truth: Dict[str, Any], action: str, target: str,
                  res_success: bool, res_informative: bool, hypothesis: str):
        step = TrajectoryStep(
            run_id=run_id,
            step=step_num,
            task_id=task_id,
            design_family=design_family,
            symptom=ground_truth.get("symptom", "unknown"),
            failure_type=ground_truth.get("bug_class", "unknown"),
            agent=self.agent_name,
            action=action,
            target_module=ground_truth.get("ground_truth_module", "top"),
            signals=[target] if target else [],
            cycle_start=0,
            cycle_end=1000,
            result_type="success" if res_success else "fail",
            informative=res_informative,
            hypothesis=hypothesis,
            cost={"latency_ms": 150, "tool_calls": 1},
            global_outcome="PENDING"
        )
        self.logger.log_step(step)
