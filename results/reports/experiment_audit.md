# Experiment Audit

## Current Dataset
- **Number of bugs**: 20
- **Number of design families**: 5 (FIFO, AXI, FSM, Pipeline, UART)
- **Train/Test split**:
  - *Train*: `fifo_b1`, `fifo_b2`, `fifo_b3`
  - *Test*: `fifo_b4`, `axi_b1`, `axi_b2`, `axi_b3`, `axi_b4`
- **Trajectories**: 
  - *Training*: 3 bugs * 50 seeds = 150 trajectories.
  - *Test*: 5 bugs * 50 seeds = 250 trajectories (per baseline/constrained).

## Current Methods
- **Baseline Agent**: A deterministic, heuristic-driven agent that queries `simulator`, `rtl_search`, and `waveform`. It picks available queries stochastically, with weights inflated for irrelevant signals to simulate a "trap".
- **Constrained Agent**: Inherits from Baseline, but reads `constraints.json`. It subtracts `lambda * confidence` from the heuristic score of any action matching a learned pattern.
- **Constraint Generation**: `PatternMiner` parses JSONL logs, filters for actions that occur disproportionately in failed runs vs successful runs, and emits rules based on occurrence ratios.
- **Constraint Application**: Applied dynamically in `select_action` as a soft penalty.

## Current Metrics
- **Success Rate**: Binary outcome (found root cause vs didn't).
- **Tool Calls**: Total number of agent steps before success or budget exhausted.
- **Waveform Queries**: Subset of tool calls involving VCD extraction.
- **Dead-end Rate (DAVR)**: Reduction in tool calls.

## Potential Confounders & Leakage
1. **Benchmark-Specific Heuristics**: The baseline agent's action weights are artificially skewed: `weight = 1.5 if not root_cause else 1.0`. This guarantees the baseline will often fail, meaning the benchmark "supplies" the failure rather than simulating a genuine agent mistake. 
2. **Insufficient Bug Diversity**: The 4 variants per family only differ in one line. They share the same signals. If the miner learns "avoid querying `write_en`", it's basically learning a module-specific artifact, not a generalized debugging strategy.
3. **No "Adversarial" Check**: If the bug *was* actually related to `write_en`, the constraint would blind the agent. We haven't proven the agent can override the constraint (Exploration Override is coded as `max(0.01, score)`, but not rigorously tested on an adversarial bug).
4. **Lack of Baselines**: We only compare against a naive baseline, not against random constraints or static budget heuristics.
5. **Metric Incompleteness**: `simulations` count was missing in the evaluation script due to not being tracked properly in the CSV grouping.
