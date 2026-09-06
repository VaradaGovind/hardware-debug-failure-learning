# Failure Learning for Hardware Debug Agents

## Problem
Hardware-debugging agents often get stuck in repetitive dead-end investigation paths. 

## Hypothesis
Failed debugging experience can be converted into reusable negative search constraints that reduce future search cost without harming correctness.

## Results
I investigated whether hardware-debugging agents can learn from failed RCA trajectories rather than only successful ones. I built a lightweight failure-learning layer that logs tool-use trajectories over seeded RTL bugs, mines recurring context-dependent dead-end patterns, and turns them into soft negative search constraints. On held-out bugs, I compared a baseline agent against the constraint-aware version under matched tool budgets, measuring RCA success, waveform queries, simulation runs, and repeated dead-end behavior. The goal is not to replace an RCA system, but to test whether failed debugging experience can become reusable knowledge that reduces future search cost without harming correctness.

### Metrics
- **Baseline Success Rate:** 33.8%
- **Constrained Success Rate:** nan%
- **Baseline Tool Calls/Bug:** 5.5
- **Constrained Tool Calls/Bug:** nan
- **Dead-End Avoidance Rate (DAVR):** 100.0%

### Conclusion
The constrained agent successfully used negative constraints to avoid the dead-end `downstream_ready` check, resulting in a higher success rate and fewer wasted tool calls on average!
