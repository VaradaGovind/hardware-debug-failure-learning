import os
import json
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.simulator import VerilogSimulator
from src.tools.waveform import WaveformTool
from src.tools.rtl_search import RTLSearchTool
from src.trajectory.logger import TrajectoryLogger
from src.agent.baseline_agent import BaselineAgent

def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    log_dir = os.path.join(base_dir, "results", "raw", "credit_subset")
    rtl_dir = os.path.join(base_dir, "rtl")
    meta_file = os.path.join(base_dir, "datasets", "metadata", "bugs.json")
    
    os.makedirs(log_dir, exist_ok=True)
    
    # Clean previous runs
    for f in os.listdir(log_dir):
        os.remove(os.path.join(log_dir, f))
        
    logger = TrajectoryLogger(log_dir)
    simulator = VerilogSimulator(rtl_dir)
    waveform = WaveformTool()
    search = RTLSearchTool(rtl_dir)
    
    with open(meta_file, "r") as f:
        bugs = json.load(f)
        
    subset_bugs = [
        "fifo_b1", "fifo_b2",
        "axi_b1", "axi_b2",
        "fsm_b1", "fsm_b2",
        "pipe_b1", "pipe_b2",
        "uart_b1", "uart_b2"
    ]
    
    selected_bugs = [b for b in bugs if b["bug_id"] in subset_bugs]
    
    manifest = []
    
    print("Generating 50 successful trajectories...")
    for bug in selected_bugs:
        print(f"Generating for {bug['bug_id']}...")
        success_count = 0
        seed = 0
        
        while success_count < 5 and seed < 200:
            seed += 1
            agent = BaselineAgent(simulator, waveform, search, logger, seed=seed, budget=6)
            outcome = agent.run(bug["bug_id"], bug["family"], bug)
            
            # The logger just wrote a summary. We need to check if it was SUCCESS.
            # TrajectoryLogger automatically writes to log_dir.
            # But wait, it doesn't return the run_id easily unless we parse it.
            # Oh, BaselineAgent run() returns outcome, but we need the run_id.
            # We can grab the latest summary file from log_dir
            if outcome == "SUCCESS":
                success_count += 1
                # Find the most recently modified summary
                summary_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith("_summary.json")]
                latest_summary = max(summary_files, key=os.path.getmtime)
                with open(latest_summary, "r") as f:
                    summ = json.load(f)
                    
                manifest.append({
                    "run_id": summ["run_id"],
                    "bug_id": bug["bug_id"],
                    "family": bug["family"],
                    "seed": seed
                })
            else:
                # Delete the failed logs to keep directory clean
                try:
                    summary_files = [f for f in os.listdir(log_dir) if f.endswith("_summary.json")]
                    if summary_files:
                        latest_summary = max([os.path.join(log_dir, f) for f in summary_files], key=os.path.getmtime)
                        run_id = os.path.basename(latest_summary).replace("_summary.json", "")
                        os.remove(latest_summary)
                        os.remove(os.path.join(log_dir, f"{run_id}.jsonl"))
                except Exception:
                    pass
                        
    out_dir = os.path.join(base_dir, "results", "processed")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "credit_subset_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Generated {len(manifest)} successful trajectories. Manifest saved.")

if __name__ == "__main__":
    main()
