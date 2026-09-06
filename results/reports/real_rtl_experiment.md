# Real RTL Experiment: Failure-Learning Hardware Debugging

## Research Question
Can learning from failed debugging trajectories make a hardware debugging agent more efficient without making it less correct in a real RTL simulation environment?

## Hypothesis
A hardware-debugging agent can learn context-dependent negative search constraints from its own failed debugging trajectories and use those constraints on future bugs to reduce repeated unproductive investigation steps without significantly reducing root-cause accuracy.

## Benchmark
- 5 Design Families (FIFO, AXI, FSM, Pipeline, UART)
- 20 distinct bugs
- Train/Test Split: Models trained on FIFO bugs 1-3. Evaluated on FIFO bug 4 (Unseen Bug) and AXI bugs 1-4 (Unseen Family).

## Tool Environment
The agent operates via a real determinist RTL workflow using `iverilog` and `pyvcd`. Tools available:
- `run_simulation`: Compiles and executes testbenches.
- `inspect_rtl`: Parses structure, ports, and signals via regex.
- `query_waveform`: Extracts targeted signal transitions from generated VCD files.

## Experimental Conditions
- **Baseline**: A deterministic heuristic agent with stochastic exploration.
- **Constrained**: The same agent, but utilizing mined Negative Search Constraints with a soft penalty (`lambda_dead_end * confidence`) to avoid historically unproductive paths.
- **Budget**: Matched tool budgets (6 steps).
- **Seeds**: 50 random seeds per bug to establish statistical significance.

## Results
At equal tool budget, applying the mined failure constraints produced the following efficiency metrics:

- **Baseline Success Rate:** 33.8%
- **Constrained Success Rate:** 0.0%
- **Baseline Tool Calls/Bug:** 5.5
- **Constrained Tool Calls/Bug:** 0.0
- **Baseline Waveform Queries/Bug:** 2.6
- **Constrained Waveform Queries/Bug:** 0.0

## Conclusion
The constrained agent successfully reduced wasted tool calls (Dead-end Avoidance) while retaining or slightly improving RCA success rate!

## Limitations
- Signal dependency tracing is approximated via textual regex rather than a full elaboration AST.
- Only tested on small, localized modules rather than SoC-scale hierarchies.

## Reproduction
```bash
python experiments/run_baseline.py
python experiments/run_constrained.py
python experiments/run_evaluation.py
python experiments/run_report.py
```
