# Action Credit Assignment - Phase 1 Report

## Objective
Evaluate whether deterministic EDA-grounded action credit assignment outperforms generic heuristic methods in identifying critical hardware debugging actions.

## Dataset
- 50 Successful trajectories selected from 10 diverse bugs across 5 families.
- Counterfactual replays executed: ~200 (Total actions across trajectories)

## Results

| Method | Precision@1 | Precision@3 |
|---|---|---|
| Method 1: Uniform | 0.00 | 0.11 |
| Method 2: Final-Step | 1.00 | 0.33 |
| Method 3: Simple Evidence | 0.00 | 0.18 |
| Method 4: Generic CF | 0.00 | 0.28 |
| Method 5: Context CF | 0.87 | 0.33 |
| Method 6: EDA-Grounded CF | 0.87 | 0.33 |

