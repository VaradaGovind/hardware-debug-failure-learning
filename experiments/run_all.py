import os
import sys
import json
import shutil
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.simulator import VerilogSimulator
from src.tools.waveform import WaveformTool
from src.tools.rtl_search import RTLSearchTool
from src.trajectory.logger import TrajectoryLogger
from src.mining.pattern_miner import PatternMiner
from src.agent.constrained_agent import ConstrainedAgent
from src.agent.baseline_agent import BaselineAgent
from src.constraints.schema import NegativeConstraint
import uuid

def generate_random_constraints(num_constraints: int) -> list[NegativeConstraint]:
    random_constraints = []
    fake_targets = ["count", "full", "empty", "write_ptr", "read_ptr", "valid_in", "ready_out", "valid_out", "state", "start", "done", "v1", "d1", "tx"]
    for i in range(num_constraints):
        random_constraints.append(NegativeConstraint(
            constraint_id=f"NC_RAND_{uuid.uuid4().hex[:6]}",
            context={},
            pattern={"action": "query_waveform", "target_module": "top", "signals": random.choice(fake_targets)},
            effect="DEPRIORITIZE",
            confidence=0.8,
            support_count=10,
            false_positive_count=0,
            source_runs=[]
        ))
    return random_constraints

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
    
    # Clear logs once
    for f in os.listdir(log_dir):
        os.remove(os.path.join(log_dir, f))
        
    print("Gathering training trajectories...")
    for bug in train_bugs:
        for seed in range(1, 6): # Reduced to 5 to save time for this unified script
            agent = BaselineAgent(simulator, waveform, search, logger, seed=seed, budget=6)
            agent.run(bug["bug_id"], bug["family"], bug)
            
    print("Mining constraints...")
    miner = PatternMiner(log_dir)
    learned_constraints = miner.mine_constraints(source="both", confidence_threshold=0.8)
    random_constraints = generate_random_constraints(max(1, len(learned_constraints)))
    
    print("Mining Ablation constraints...")
    pos_constraints = miner.mine_constraints(source="positive")
    neg_constraints = miner.mine_constraints(source="negative")
    
    print(f"Mined {len(learned_constraints)} constraints.")
    
    print("Running Evaluation on Test Split...")
    for bug in test_bugs:
        print(f"Testing {bug['bug_id']}...")
        for seed in range(1, 6):
            # Baselines
            BaselineAgent(simulator, waveform, search, logger, seed=seed, budget=6).run(bug["bug_id"], bug["family"], bug)
            ConstrainedAgent(simulator, waveform, search, logger, random_constraints, seed=seed, budget=6, ignore_context=True).run(bug["bug_id"], bug["family"], bug, agent_name="random")
            ConstrainedAgent(simulator, waveform, search, logger, learned_constraints, seed=seed, budget=6, ignore_context=True).run(bug["bug_id"], bug["family"], bug, agent_name="global_constrained")
            ConstrainedAgent(simulator, waveform, search, logger, learned_constraints, seed=seed, budget=6, ignore_context=False).run(bug["bug_id"], bug["family"], bug, agent_name="context_aware")
            
            # Ablations
            ConstrainedAgent(simulator, waveform, search, logger, pos_constraints, seed=seed, budget=6, ignore_context=False).run(bug["bug_id"], bug["family"], bug, agent_name="pos_only")
            ConstrainedAgent(simulator, waveform, search, logger, neg_constraints, seed=seed, budget=6, ignore_context=False).run(bug["bug_id"], bug["family"], bug, agent_name="neg_only")
            
if __name__ == "__main__":
    main()
