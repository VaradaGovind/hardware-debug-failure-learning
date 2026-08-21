# Blind-test summary

This directory contains the small tracked summary for the Phase 4.1 held-out comparison. It does not contain raw waveforms, predictions, benchmark manifests, or generated reports.

## Scope and provenance

- **Scope:** 50 held-out target rows across five hardware families: FIFO, AXI, FSM, UART, and PIPELINE; 10 rows per family.
- **Inference path:** `experiments/run_phase4_1_blind_validation.py` uses low-level, remediated, and transaction-semantic validators, then scores predictions after inference.
- **Audited source rows:** `results/transaction_semantic_certs/blind_validation/processed/scored_heldout_evaluation.csv`.
- **Audited report:** `results/transaction_semantic_certs/blind_validation/reports/phase4_1_blind_validation_report.md`.
- **Status:** Historical artifact. The CSV and report were inspected and the summary metrics were recomputed from the 50 rows during the second pass; the full benchmark was not rerun.

The historical CSV contains 19 transaction-semantic rows whose reason is `VCD waveform not found` (10 PIPELINE, 7 FIFO, 2 AXI). Therefore these values are traceable historical outputs, not a claim that this checkout currently reproduces 50 fresh simulations. The missing-trace cases are retained in the denominator and are relevant to the reported conservative behavior.

## Metric boundaries

`summary.csv` separates reuse precision, false reuse rate, and positive transfer/recall. The positive-transfer value is not bug-resolution rate, and the benchmark does not measure whether an engineer ultimately fixed the RTL bug.

The exact row-level calculation is: among rows with `pred_l0` or `pred_l2 == PASS`, a true reuse is a `ground_truth_match == MATCH`; precision is true reuse divided by all reuse decisions; false reuse rate is false reuse divided by all reuse decisions; positive transfer is true reuse divided by designated `expected_decision == PASS` rows.
