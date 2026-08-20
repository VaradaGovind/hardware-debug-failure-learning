# Results and generated artifacts

This directory contains local experiment outputs such as reports, processed tables, plots, certificates, raw trajectories, and audit manifests.

Generated results are intentionally excluded from the initial Git commit by the repository `.gitignore`. In particular, do not commit raw logs, JSONL trajectories, VCD waveforms, simulator binaries, held-out ground truth, or large generated plots without first checking ownership, sensitivity, and redistribution permission.

The local reports that informed the packaging documentation include:

- `transaction_semantic_certs/blind_validation/reports/phase4_1_blind_validation_report.md`
- `transaction_semantic_certs/adaptive_boundary/reports/phase4_1_vs_phase4_2_scientific_audit.md`
- `transaction_semantic_certs/variable_latency_stress/reports/phase4_3_variable_latency_report.md`
- `transaction_semantic_certs/variable_latency_stress/reports/phase4_3A_safety_cost_audit.md`
- `transaction_semantic_certs/variable_latency_stress/cost_consistency_audit/reports/phase4_3B_cost_consistency_audit.md`

The experiment runners and audits regenerate their own outputs under `results/`. The most relevant commands are documented in the root [README](../README.md). Some runners require local benchmark files and `iverilog`/`vvp`.

The cost reports distinguish one subsequent reuse target from two total manifestations: `N_targets* = 1` versus `N* = 2` when the source failure is included. The root documentation uses the latter lifecycle convention.
