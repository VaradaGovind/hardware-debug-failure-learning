# Cost-analysis summary

This directory contains the tracked summary of the Phase 4.3 cost audit. Values are modeled tool-call equivalents, not wall-clock time, energy, or monetary cost.

## Scope and provenance

- **Audited row-level cost table:** `results/transaction_semantic_certs/variable_latency_stress/processed/end_to_end_cost_audit.csv`.
- **Full-lifecycle clarification:** `results/transaction_semantic_certs/variable_latency_stress/cost_consistency_audit/reports/phase4_3B_cost_consistency_audit.md` and `results/transaction_semantic_certs/variable_latency_stress/cost_consistency_audit/processed/break_even_reconstruction.csv`.
- **Producing code:** `scripts/run_phase4_3a_safety_cost_audit.py` and `scripts/run_phase4_3b_cost_consistency_audit.py`.
- **Status:** Historical artifact. The existing processed tables and formulas were checked read-only; the cost audit scripts were not rerun.

## Cost-model distinction

The 1.244291x SCR in `summary.csv` is the independent target-only cost divided by the adaptive target-validation-plus-fallback cost for the 75-target table. The cost-consistency audit separately adds the one-time source RCA and certificate extraction and clarifies break-even as **1 subsequent target**, or **2 total manifestations** when the source failure is counted. These are different denominators, not contradictory measurements.

The model uses 8.9 calls for independent/fallback RCA, 2.05 calls for adaptive validation, and 0.6 calls for certificate extraction. It does not claim a measured bug-resolution rate.
