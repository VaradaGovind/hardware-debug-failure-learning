import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.simulator import VerilogSimulator
from src.tools.waveform import WaveformTool
from src.tools.rtl_search import RTLSearchTool
from src.trajectory.logger import TrajectoryLogger
from src.mining.pattern_miner import PatternMiner
from src.agent.constrained_agent import ConstrainedAgent
from src.agent.baseline_agent import BaselineAgent
from dataclasses import asdict

def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    log_dir = os.path.join(base_dir, "results", "raw")
    rtl_dir = os.path.join(base_dir, "rtl")
    meta_file = os.path.join(base_dir, "datasets", "metadata", "bugs.json")
    
    # Mine constraints from baseline logs
    miner = PatternMiner(log_dir)
    constraints = miner.mine_constraints()
    
    # Save constraints
    processed_dir = os.path.join(base_dir, "results", "processed")
    os.makedirs(processed_dir, exist_ok=True)
    with open(os.path.join(processed_dir, "constraints.json"), "w") as f:
        json.dump([asdict(c) for c in constraints], f, indent=2)
    print(f"Mined {len(constraints)} constraints.")
    
    logger = TrajectoryLogger(log_dir)
    simulator = VerilogSimulator(rtl_dir)
    waveform = WaveformTool()
    search = RTLSearchTool(rtl_dir)
    
    with open(meta_file, "r") as f:
        bugs = json.load(f)
        
    # Split A Test: FIFO Bug 4 (Unseen)
    # Split B Test: AXI (Unseen family entirely)
    # We will test both baseline and constrained agent on the test set for fair evaluation
    test_bugs = [b for b in bugs if b["bug_id"] == "fifo_b4" or b["family"] == "axi"]
    
    for bug in test_bugs:
        for seed in range(1, 51):
            # Run Baseline on test set for metric comparison
            b_agent = BaselineAgent(simulator, waveform, search, logger, seed=seed, budget=6)
            b_outcome = b_agent.run(bug["bug_id"], bug["family"], bug)
            print(f"TEST Baseline - Bug: {bug['bug_id']} - Seed {seed}: Outcome = {b_outcome}")
            
            # Run Constrained on test set
            c_agent = ConstrainedAgent(simulator, waveform, search, logger, constraints, seed=seed, budget=6)
            c_outcome = c_agent.run(bug["bug_id"], bug["family"], bug)
            print(f"TEST Constrained - Bug: {bug['bug_id']} - Seed {seed}: Outcome = {c_outcome}")

if __name__ == "__main__":
    main()
