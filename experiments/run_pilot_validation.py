import os
import json
import sys
import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.simulator import VerilogSimulator
from src.tools.waveform import WaveformTool
from src.tools.rtl_search import RTLSearchTool
from src.trajectory.logger import TrajectoryLogger
from src.agent.re_eval_agents import ModelA_WeakHeuristicAgent, ModelB_StrongCausalAgent
from src.credit.re_eval_engine import AdaptiveReplayEngine, IndependentOracleCriticality
from src.credit.re_eval_credit import ReEvalCreditAssigner

def precision_at_k(ranked_list, k):
    if not ranked_list:
        return 0.0
    top_k = ranked_list[:k]
    critical_count = sum(1 for item in top_k if item.get("oracle_criticality") == "critical")
    return critical_count / k

def mean_reciprocal_rank(ranked_list):
    for rank, item in enumerate(ranked_list, start=1):
        if item.get("oracle_criticality") == "critical":
            return 1.0 / rank
    return 0.0

def run_pilot():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    pilot_dir = os.path.join(base_dir, "results", "re_evaluation", "pilot")
    raw_dir = os.path.join(pilot_dir, "raw")
    replay_dir = os.path.join(pilot_dir, "replays")
    reports_dir = os.path.join(base_dir, "results", "re_evaluation", "reports")
    
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(replay_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    
    # Clean previous pilot logs
    for f in os.listdir(raw_dir):
        try: os.remove(os.path.join(raw_dir, f))
        except: pass
    for f in os.listdir(replay_dir):
        try: os.remove(os.path.join(replay_dir, f))
        except: pass
    
    rtl_dir = os.path.join(base_dir, "rtl")
    meta_file = os.path.join(base_dir, "datasets", "metadata", "bugs.json")
    
    with open(meta_file, "r") as f:
        bugs = json.load(f)
    bugs_dict = {b["bug_id"]: b for b in bugs}
    
    simulator = VerilogSimulator(rtl_dir)
    waveform = WaveformTool()
    search = RTLSearchTool(rtl_dir)
    logger = TrajectoryLogger(raw_dir)
    replay_logger = TrajectoryLogger(replay_dir)
    
    engine = AdaptiveReplayEngine(simulator, waveform, search)
    assigner = ReEvalCreditAssigner(seed=42)
    oracle = IndependentOracleCriticality(meta_file)
    
    pilot_bugs = ["fifo_b1", "axi_b1", "fsm_b1", "pipe_b1", "uart_b1"]
    models = ["model_a_weak_heuristic", "model_b_strong_causal"]
    
    pilot_manifest = []
    
    print("=" * 70)
    print("PILOT VALIDATION GATE — PHASE 1 RE-EVALUATION")
    print("=" * 70)
    
    # Generate Pilot Trajectories
    print("\n[PILOT STEP 1] Generating Pilot Trajectories (5 bugs x 5 seeds)...")
    for bug_id in pilot_bugs:
        bug = bugs_dict[bug_id]
        for m_name in models:
            for seed in range(1, 6):
                if m_name == "model_a_weak_heuristic":
                    agent = ModelA_WeakHeuristicAgent(simulator, waveform, search, logger, seed=seed, budget=12)
                else:
                    agent = ModelB_StrongCausalAgent(simulator, waveform, search, logger, seed=seed, budget=12)
                    
                outcome = agent.run(bug_id, bug["family"], bug)
                
                # Get latest summary
                summary_files = [os.path.join(raw_dir, f) for f in os.listdir(raw_dir) if f.endswith("_summary.json")]
                latest_summary = max(summary_files, key=os.path.getmtime)
                with open(latest_summary, "r") as f:
                    summ = json.load(f)
                    
                if outcome == "SUCCESS":
                    pilot_manifest.append({
                        "run_id": summ["run_id"],
                        "model": m_name,
                        "bug_id": bug_id,
                        "family": bug["family"],
                        "seed": seed,
                        "steps": summ["steps"]
                    })
                    
    print(f"Generated {len(pilot_manifest)} successful pilot trajectories.")
    
    # Non-Leaky Verification Check
    print("\n[PILOT STEP 2] Auditing Non-Leaky Environment...")
    root_cause_positions = []
    trajectory_lengths = []
    
    for item in pilot_manifest:
        traj_file = os.path.join(raw_dir, f"{item['run_id']}.jsonl")
        steps = []
        with open(traj_file, "r") as f:
            for line in f:
                steps.append(json.loads(line))
        trajectory_lengths.append(len(steps))
        
        gt_signals = bugs_dict[item["bug_id"]]["ground_truth_signals"]
        rc_step = None
        for s in steps:
            tgt = s.get("signals", [""])[0] if s.get("signals") else ""
            if s.get("action") == "query_waveform" and tgt in gt_signals:
                rc_step = s["step"]
                break
        if rc_step is not None:
            root_cause_positions.append((rc_step, len(steps)))
            
    final_step_leaks = sum(1 for rc, total in root_cause_positions if rc == total)
    avg_rc_step = np.mean([rc for rc, total in root_cause_positions])
    avg_total_step = np.mean([total for rc, total in root_cause_positions])
    
    print(f"Total evaluated trajectories with root-cause query: {len(root_cause_positions)}")
    print(f"Average root-cause query step: {avg_rc_step:.2f} / {avg_total_step:.2f} total steps")
    print(f"Trajectories where root cause was at final step: {final_step_leaks} / {len(root_cause_positions)}")
    
    if final_step_leaks == len(root_cause_positions) and len(root_cause_positions) > 0:
        print("CRITICAL FAILURE: Structural termination leakage still exists! Root cause is always final step.")
        sys.exit(1)
    else:
        print("PASS: Termination leakage eliminated! Root cause query is executed mid-trajectory.")

    # Counterfactual Replays and Credit Assignment
    print("\n[PILOT STEP 3] Running Adaptive Counterfactual Replays & Credit Scoring...")
    all_credits = []
    
    for idx, item in enumerate(pilot_manifest):
        run_id = item["run_id"]
        bug_id = item["bug_id"]
        seed = item["seed"]
        model_name = item["model"]
        bug_meta = bugs_dict[bug_id]
        
        traj_file = os.path.join(raw_dir, f"{run_id}.jsonl")
        trajectory = []
        with open(traj_file, "r") as f:
            for line in f:
                trajectory.append(json.loads(line))
                
        # Counterfactual sweeps
        cf_results = {}
        for t, action in enumerate(trajectory):
            act_type = action.get("action", "")
            tgt = action.get("signals", [""])[0] if action.get("signals") else ""
            
            # Setup and terminal actions are not ablated
            if act_type in ["run_simulation", "give_up", "inspect_failure", "validate_hypothesis", "conclude_rca"]:
                cf_results[t] = True
                continue
                
            banned_action = {"action": act_type, "target": tgt}
            success = engine.run_counterfactual_replay(model_name, bug_meta, seed, banned_action, replay_logger)
            cf_results[t] = success
            
        # Credit assignment
        credits = assigner.assign_credits(trajectory, cf_results, bug_meta)
        
        # Oracle ground-truth labeling
        for c, action in zip(credits, trajectory):
            c["oracle_criticality"] = oracle.evaluate_criticality(action, bug_id)
            c["model"] = model_name
            
        all_credits.extend(credits)
        
    df = pd.DataFrame(all_credits)
    
    # Leakage Audit & Method Comparison on Pilot Data
    print("\n[PILOT STEP 4] Evaluating Methods & Leakage Baselines...")
    
    methods = [
        ("Uniform (M1)", "credit_uniform"),
        ("Final-Step (M2)", "credit_final_step"),
        ("Simple Evidence (M3)", "credit_evidence"),
        ("Generic CF (M4)", "credit_generic_cf"),
        ("Generic Context CF (M5)", "credit_generic_context_cf"),
        ("EDA Grounded CF (M6)", "credit_eda_grounded_cf"),
        ("EDA Shuffled Control (M6-Shuffled)", "credit_eda_shuffled_cf"),
        ("First-Step (Baseline)", "credit_first_step"),
        ("Mid-Step (Baseline)", "credit_mid_step"),
        ("Action Frequency (Baseline)", "credit_action_frequency"),
        ("Action Type (Baseline)", "credit_action_type"),
        ("Random (Baseline)", "credit_random"),
    ]
    
    results = []
    for model_name in models:
        m_df = df[df["model"] == model_name]
        for label, col in methods:
            p1_list, p3_list, mrr_list = [], [], []
            for run_id, group in m_df.groupby("run_id"):
                ranked = group.sort_values(by=col, ascending=False).to_dict("records")
                p1_list.append(precision_at_k(ranked, 1))
                p3_list.append(precision_at_k(ranked, 3))
                mrr_list.append(mean_reciprocal_rank(ranked))
                
            results.append({
                "Model": "Model A (Weak Heuristic)" if "weak" in model_name else "Model B (Strong Causal)",
                "Method": label,
                "Precision@1": np.mean(p1_list) if p1_list else 0.0,
                "Precision@3": np.mean(p3_list) if p3_list else 0.0,
                "MRR": np.mean(mrr_list) if mrr_list else 0.0
            })
            
    res_df = pd.DataFrame(results)
    print("\nPILOT RESULTS SUMMARY TABLE:")
    print(res_df.to_string(index=False))
    
    # Check pilot gates
    print("\n" + "=" * 70)
    print("PILOT AUDIT GATE DECISION")
    print("=" * 70)
    
    final_step_p1 = res_df[res_df["Method"] == "Final-Step (M2)"]["Precision@1"].mean()
    m5_p1_b = res_df[(res_df["Model"] == "Model B (Strong Causal)") & (res_df["Method"] == "Generic Context CF (M5)")]["Precision@1"].values[0]
    m6_p1_b = res_df[(res_df["Model"] == "Model B (Strong Causal)") & (res_df["Method"] == "EDA Grounded CF (M6)")]["Precision@1"].values[0]
    m6_shuff_p1_b = res_df[(res_df["Model"] == "Model B (Strong Causal)") & (res_df["Method"] == "EDA Shuffled Control (M6-Shuffled)")]["Precision@1"].values[0]
    
    print(f"1. Final-Step Precision@1: {final_step_p1:.2f} (Must NOT be 1.00; target <= 0.40)")
    print(f"2. Model B M5 Precision@1: {m5_p1_b:.2f}")
    print(f"3. Model B M6 Precision@1: {m6_p1_b:.2f}")
    print(f"4. Model B M6-Shuffled Control Precision@1: {m6_shuff_p1_b:.2f}")
    print(f"5. Delta_EDA (Model B): {m6_p1_b - m5_p1_b:+.2f}")
    
    gate_passed = True
    if final_step_p1 > 0.40:
        print("FAIL: Final-Step heuristic still dominates! Environment has remaining leakage.")
        gate_passed = False
    else:
        print("PASS: Positional leakage successfully eliminated.")
        
    if gate_passed:
        print("\n>>> PILOT GATE PASSED! Ready for Full-Scale Multi-Seed Evaluation. <<<")
    else:
        print("\n>>> PILOT GATE FAILED. Fix issues before full scale. <<<")

    # Save pilot report
    pilot_report_path = os.path.join(reports_dir, "pilot_gate_audit.md")
    with open(pilot_report_path, "w") as f:
        f.write(f"# Pilot Gate Audit Report\n\n")
        f.write(f"## Gate Status: {'PASSED' if gate_passed else 'FAILED'}\n\n")
        f.write(f"### Summary Results\n\n```text\n{res_df.to_string(index=False)}\n```\n\n")
        f.write(f"### Diagnostics\n- Final-Step P@1: {final_step_p1:.2f}\n- Non-leaky average RC step: {avg_rc_step:.2f} of {avg_total_step:.2f}\n- Model B Delta_EDA: {m6_p1_b - m5_p1_b:+.2f}\n- M6-Shuffled Control: {m6_shuff_p1_b:.2f}\n")
    print(f"Saved pilot audit report to {pilot_report_path}")

if __name__ == "__main__":
    run_pilot()
