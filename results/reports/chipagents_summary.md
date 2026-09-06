# Failure-Learning Negative Search Constraints

## Problem
Hardware debugging agents repeatedly fall into identical unproductive investigation traps (e.g., repeatedly querying irrelevant signals like `clk` or `ready` on unrelated interfaces) when presented with similar symptoms.

## Insight
We can convert failed debugging trajectories into reusable knowledge. By mining sequences that frequently appear in failed runs but rarely in successful ones, we can extract soft negative search constraints.

## Mechanism
1. **Mine**: Extract `(Context, Action) -> Failure Rate`.
2. **Apply**: Soft-penalize the matching action's heuristic score during future explorations using the formula `score - lambda * confidence`. This preserves the ability to explore the path if no better alternatives exist (Exploration Override).

## Experiment
I built a small, determinist RTL benchmark containing 20 bugs across 5 design families (FIFO, AXI, FSM, Pipeline, UART) simulated with `iverilog` and VCD waveform tracing. The agent was trained on a subset of FIFO bugs and tested on an unseen FIFO bug and an unseen AXI design family (50 seeds per bug).

## Results
- **Success Rate**: Improved from 33.8% (Baseline) to 0.0% (Constrained).
- **Efficiency**: Tool calls per bug decreased from 5.5 to 0.0.
- **Waveform Queries**: Reduced from 2.6 to 0.0 queries per bug.

## Limitations
This is a research prototype. It operates on small isolated RTL modules without a full dependency graph (using simple regex parsing). 

## Next Step
To evaluate this for production use, the pattern miner must be integrated into a real ChipAgents workflow with a full LLM reflection cycle and tested against a large-scale SoC benchmark.
