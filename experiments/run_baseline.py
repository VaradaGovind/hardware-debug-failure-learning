import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.simulator import VerilogSimulator
from src.tools.waveform import WaveformTool
from src.tools.rtl_search import RTLSearchTool
from src.trajectory.logger import TrajectoryLogger
from src.agent.baseline_agent import BaselineAgent

def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    log_dir = os.path.join(base_dir, "results", "raw")
    rtl_dir = os.path.join(base_dir, "rtl")
    meta_file = os.path.join(base_dir, "datasets", "metadata", "bugs.json")
    
    logger = TrajectoryLogger(log_dir)
    simulator = VerilogSimulator(rtl_dir)
    waveform = WaveformTool()
    search = RTLSearchTool(rtl_dir)
    
    with open(meta_file, "r") as f:
        bugs = json.load(f)
        
    # Split A: Train on Bug 1, 2, 3. Test on Bug 4
    # For now, let's just run the baseline on the train set (to generate constraints)
    train_bugs = [b for b in bugs if b["family"] == "fifo" and b["bug_id"] != "fifo_b4"]
    
    for bug in train_bugs:
        # Run 5 seeds per bug to build trajectories
        for seed in range(1, 51):
            # Reset agent state for each run
            agent = BaselineAgent(simulator, waveform, search, logger, seed=seed, budget=6)
            outcome = agent.run(bug["bug_id"], bug["family"], bug)
            print(f"Baseline - Bug: {bug['bug_id']} - Seed {seed}: Outcome = {outcome}")
        
if __name__ == "__main__":
    main()
