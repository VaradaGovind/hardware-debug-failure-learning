# Phase 3: Scientific Audit Report

## Hypothesis
Failed trajectories can produce useful negative search knowledge that generalizes across bug contexts without significantly harming root-cause accuracy.

## Experimental Design
- **Dataset**: 30 diverse bugs across 5 hardware families (FIFO, AXI, FSM, Pipeline, UART).
- **Adversarial Setup**: Each family contains 1 bug whose root cause directly overlaps with a historically unproductive pattern from the other bugs.
- **Evaluation Split**: Trained on 4 FIFO bugs. Tested on unseen FIFO bugs and unseen families.

## Results: Main Baselines & Ablations

```text
             agent  success  tool_calls  false_pruning  exploration_overrides
          baseline 0.266667    5.513333       0.000000                    0.0
     context_aware 0.253846    5.530769       0.138462                    0.0
global_constrained 0.284615    5.507692       0.138462                    0.0
          neg_only 0.246154    5.569231       0.138462                    0.0
          pos_only 0.261538    5.530769       0.000000                    0.0
            random 0.200000    5.630769       1.669231                    0.0
```

### Analysis
- **Baseline**: Static heuristic agent (no repeated queries).
- **Random**: Randomly generated negative constraints.
- **Global**: Learned negative constraints applied unconditionally.
- **Context-Aware**: Learned negative constraints applied conditionally based on design family and symptom.
- **pos_only**: Ablation using only successful runs.
- **neg_only**: Ablation using only failed runs.

### Adversarial Safety
The `false_pruning` metric tracks how many times the agent suppressed an action that was actually the ground-truth root cause. The `exploration_overrides` tracks how often the agent recovered from a trap by exhausting its budget and forcibly exploring a penalized action.

## Conclusion
(Automatically computed based on results)
