# Variable-latency summary

This directory contains the small tracked summary for the Phase 4.3 variable-latency and incomplete-evidence audit. Raw VCDs, benchmark manifests, predictions, plots, and reports remain outside the tracked package.

## Scope and provenance

- **Scope:** 75 held-out target rows across five hardware families, including 10 `CLASS_I_INCOMPLETE_EVIDENCE` rows.
- **Compared paths:** static 4-cycle L2 validation and adaptive-boundary L2 validation.
- **Audited source rows:** `results/transaction_semantic_certs/variable_latency_stress/processed/scored_variable_latency_evaluation.csv`.
- **Audited reports:** `results/transaction_semantic_certs/variable_latency_stress/reports/phase4_3_variable_latency_report.md` and `results/transaction_semantic_certs/variable_latency_stress/reports/phase4_3A_safety_cost_audit.md`.
- **Status:** Historical artifact. The 75-row CSV was inspected and the summary metrics were recomputed during the second pass; the full benchmark was not rerun.

The adaptive result supports a narrower safety claim in this benchmark: it reduced false reuse and rejected all 10 incomplete cases conservatively. Static and adaptive positive transfer were equal at 77.5%, so this data does not demonstrate an adaptive recall improvement.

## Metric boundaries

Precision and false reuse rate are calculated only over `PASS` reuse decisions. Positive transfer is the fraction of designated `expected_decision == PASS` rows with a matching accepted reuse. Incomplete-case rejection is reported separately as a count, not folded into bug resolution.
