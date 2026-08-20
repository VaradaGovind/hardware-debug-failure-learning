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
        
    train_bugs = [b for b in bugs if b["family"] == "fifo" and b["bug_id"] in ["fifo_b1", "fifo_b2", "fifo_b3", "fifo_b4"]]
    test_bugs = [b for b in bugs if b["bug_id"] not in ["fifo_b1", "fifo_b2", "fifo_b3", "fifo_b4"]]
    
    # Generate Training Trajectories for Ablations
    print("Gathering training trajectories...")
    for bug in train_bugs:
        for seed in range(1, 11):
            agent = BaselineAgent(simulator, waveform, search, logger, seed=seed, budget=6)
            agent.run(bug["bug_id"], bug["family"], bug)
            
    # Ablation 1: Positive-Only vs Negative-Only vs Both
    print("Mining Positive-Only constraints...")
    miner = PatternMiner(log_dir)
    pos_constraints = miner.mine_constraints(source="positive")
    neg_constraints = miner.mine_constraints(source="negative")
    both_constraints = miner.mine_constraints(source="both")
    
    print("Running Pos/Neg Ablation...")
    for bug in test_bugs:
        for seed in range(1, 3): # Reduced seeds for ablations to save time
            ConstrainedAgent(simulator, waveform, search, logger, pos_constraints, seed=seed, budget=6).run(bug["bug_id"], bug["family"], bug, agent_name="pos_only")
            ConstrainedAgent(simulator, waveform, search, logger, neg_constraints, seed=seed, budget=6).run(bug["bug_id"], bug["family"], bug, agent_name="neg_only")
            ConstrainedAgent(simulator, waveform, search, logger, both_constraints, seed=seed, budget=6).run(bug["bug_id"], bug["family"], bug, agent_name="both_pos_neg")
            
    # Ablation 2: Threshold Sweep
    print("Running Threshold Sweep...")
    for thresh in [0.5, 0.7, 0.95]:
        thresh_constraints = miner.mine_constraints(source="both", confidence_threshold=thresh)
        for bug in test_bugs:
            for seed in range(1, 3):
                ConstrainedAgent(simulator, waveform, search, logger, thresh_constraints, seed=seed, budget=6).run(bug["bug_id"], bug["family"], bug, agent_name=f"thresh_{thresh}")

if __name__ == "__main__":
    main()
