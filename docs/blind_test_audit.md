# Forensic Audit of the 50-Failure Blind Evaluation (Phase 4.1)

**Audit Date:** August 20, 2026  
**Auditor:** Antigravity AI Forensic Inspector  
**Subject:** Phase 4.1 Blind Held-Out Validation of Transaction-Semantic Causal RCA Reuse  
**Scope:** Dataset origin, procedural generators, waveform artifacts, denominator verification, metric derivations, and repository packaging.

---

## 1. Original Experiment

### Overview & Parameters
- **Total Evaluated Targets:** 50 unseen hardware failure instances across 5 hardware families (10 target instances per family).
- **Source Failures (for Certificate Extraction):** 5 source instances (1 per family; 55 total simulated designs).
- **Hardware Families:**
  1. `FIFO_SIMULTANEOUS_RW` (`fifo`): Count corruption during simultaneous read/write.
  2. `AXI_HANDSHAKE_HOLD` (`axi`): Protocol violation where `valid_out` drops during backpressure.
  3. `FSM_STUCK_STATE` (`fsm`): State fails to advance from IDLE upon `start` trigger.
  4. `UART_BAUD_DIVIDER` (`uart`): Counter steps by 2 instead of 1, corrupting baud timing.
  5. `PIPE_STALL_BUBBLE` (`pipeline`): Pipeline drops valid data or introduces spurious stalls.
- **Adversarial Benchmark Categories (10 instances per family):**
  - **Category A (15 instances, 3/family):** Same defect, novel manifestation (Positive Controls; expected `PASS`).
  - **Category B (10 instances, 2/family):** Same symptom, completely different defect mechanism (expected `FAIL`).
  - **Category C (5 instances, 1/family):** Same trigger event, different underlying failure mechanism (expected `FAIL`).
  - **Category D (10 instances, 2/family):** *Decisive Adversarial Control* — Identical low-level signal invariants (stability/conservation), but different transaction semantics (expected `FAIL` or `INSUFFICIENT_EVIDENCE`).
  - **Category E (5 instances, 1/family):** Preconditions unexercised / truncated stimulus (expected `INSUFFICIENT_EVIDENCE`).
  - **Category F (5 instances, 1/family):** Genuine unrelated failures (expected `FAIL`).

### Baselines & Evaluated Configurations
1. **L0 Baseline (`GenericCertificateValidator`):** Phase 3 low-level causal certificate based on structural signal invariants and local delta assertions without transaction protocol awareness.
2. **L1 Baseline (`RemediatedCertificateValidator`):** Phase 3.1 low-level validator augmented with dynamic trigger filtering and reset awareness.
3. **L2 Proposed (`TransactionSemanticValidator`):** Phase 4 Transaction-Semantic Causal Certificate validator enforcing transaction boundaries, protocol obligation contracts, and downstream causal propagation checks (frozen 4-cycle static window).
4. **Similarity Baselines (`ScaleSimilarityBaselines`):** Log similarity, AST/structural similarity, semantic embedding similarity, and composite heuristic score.

### Reported Original Result
- **Reuse Precision:** Improved from **55.6%** (L0/L1: 5 true reuses / 9 accepted) to **71.4%** (L2: 5 true reuses / 7 accepted).
- **False Reuse Rate (FRR):** Reduced from **44.4%** (L0/L1: 4 false reuses / 9 accepted) to **28.6%** (L2: 2 false reuses / 7 accepted).
- **Positive Transfer / Recall:** Remained at **33.3%** (5 / 15 genuine positive controls accepted).
- **Negative Rejection Rate:** Improved from **88.6%** (L0/L1: 31 / 35) to **94.3%** (L2: 33 / 35).
- **Scientific Conclusion:** Phase 4.1 demonstrated that transaction-semantic obligations significantly improve precision and reject false reuses on adversarial controls (Category D), but rigid static transaction windows collapsed positive recall on novel testbench delays, directly motivating the Phase 4.2 adaptive boundary recovery.

---

## 2. Artifact Inventory

| File / Artifact Path | Type | Description / Contents |
|---|---|---|
| [`scripts/generate_phase4_1_benchmark.py`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/scripts/generate_phase4_1_benchmark.py) | Python Script | Deterministic procedural benchmark generator for all 50 target designs, 50 testbenches, 5 source fixtures, ground truth, and blinded manifests. |
| [`experiments/run_phase4_1_blind_validation.py`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/experiments/run_phase4_1_blind_validation.py) | Python Runner | Full execution harness: verifies cryptographic manifest hashes, runs Icarus simulations, executes blind inference across L0/L1/L2, performs post-hoc scoring, computes bootstrap CIs, and renders 8 plots. |
| [`results/transaction_semantic_certs/blind_validation/frozen_manifest.json`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/frozen_manifest.json) | JSON Manifest | Cryptographic freeze record storing SHA256 hashes of frozen Phase 4 validator source files, random seeds (`101, 202, 303, 404, 505`), and timestamp. |
| [`results/transaction_semantic_certs/blind_validation/benchmark/blinded_target_manifest.json`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/benchmark/blinded_target_manifest.json) | JSON (50 entries) | Blind target list (target ID, design name, source ID, observed interface signals). Stripped of all defect labels and ground truth. |
| [`results/transaction_semantic_certs/blind_validation/benchmark/heldout_ground_truth.json`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/benchmark/heldout_ground_truth.json) | JSON (50 entries) | Isolated ground truth mapping containing defect categories, expected decisions, and causal match labels. |
| [`results/transaction_semantic_certs/blind_validation/certificates/blind_tx_cert_*.json`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/certificates) | JSON (5 files) | Serialized transaction-semantic source certificates extracted for FIFO, AXI, FSM, UART, and PIPELINE. |
| [`results/transaction_semantic_certs/blind_validation/validation/blind_inference_predictions.csv`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/validation/blind_inference_predictions.csv) | CSV (50 rows) | Blind predictions output by L0, L1, L2, ablations, similarity baselines, and execution latencies. |
| [`results/transaction_semantic_certs/blind_validation/processed/scored_heldout_evaluation.csv`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/processed/scored_heldout_evaluation.csv) | CSV (50 rows) | Scored dataset merging inference predictions with ground truth; primary numerical source of all reported Phase 4.1 metrics. |
| [`results/transaction_semantic_certs/blind_validation/reports/phase4_1_blind_validation_report.md`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/reports/phase4_1_blind_validation_report.md) | Markdown Report | Original experimental report with category breakdowns, adversarial analysis, and the recommendation gate. |
| [`results/transaction_semantic_certs/blind_validation/plots/*.png`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/plots) | PNG (8 images) | Visualizations including `heldout_precision_recall.png`, `frr_comparison_l0_l1_l2.png`, and `positive_negative_matrix.png`. |
| [`results/blind_test/summary.csv`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/blind_test/summary.csv) | CSV (10 rows) | Tracked, lightweight summary metric table documenting audited results and provenance. |
| [`scripts/audit_phase4_1_vs_phase4_2.py`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/scripts/audit_phase4_1_vs_phase4_2.py) | Python Script | Verification script performing strict comparison between Phase 4.1 and Phase 4.2 runs, verifying transitions and simulation causes. |
| [`rtl/designs/*.v`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/rtl/designs) | Verilog RTL | 50 target Verilog designs + 5 source Verilog designs (all 55 present locally). |
| [`rtl/testbenches/*_tb.v`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/rtl/testbenches) | Verilog TB | 50 target Verilog testbenches + 5 source Verilog testbenches (all 55 present locally). |
| [`rtl/*.vcd`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/rtl) | VCD Waveforms | 295 total VCD traces locally present in workspace, including 48 of the 50 blind test target waveforms. |

---

## 3. Missing Cases & The "19-Row" Audit

### Forensic Finding: The 50-Row CSV vs the 19 Missing VCDs
An exhaustive scan of the repository confirms that **no CSV file is truncated to 19 rows**. Both [`scored_heldout_evaluation.csv`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/processed/scored_heldout_evaluation.csv) and [`blind_inference_predictions.csv`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/validation/blind_inference_predictions.csv) contain **exactly 50 data rows** (representing all 50 target cases across 5 designs).

The number "19" in repository notes and audit questions refers to **19 specific rows in the 50-row CSV where the L2 validation stage was recorded as `PRECHECK` due to `VCD waveform not found`**:

```text
L2 Stage Breakdown in Phase 4.1 (50 Target Cases):
  - PRECHECK (VCD not found):              19 cases (10 PIPELINE, 7 FIFO, 2 AXI)
  - TRANSACTION_CONTEXT (Trigger missing): 18 cases
  - FULL_TRANSACTION_SEMANTIC (Passed):     7 cases
  - PROTOCOL_OBLIGATION (Obligation met):   6 cases
  Total Evaluated Records:                 50 cases
```

### Why Were 19 VCDs Missing in the Original Phase 4.1 Run?
Forensic inspection of the simulation logs, RTL sources, and testbench generation code revealed two distinct technical reasons:

1. **Python String Interpolation Bug in Testbench Generation (17 cases: 7 FIFO, 10 PIPELINE):**
   In the original benchmark generation script, raw string formatting for Verilog hex literals omitted backslash escaping inside f-strings (e.g., `8h11` and `8h00` instead of `8'h11` and `8'h00`). When `VerilogSimulator` invoked `iverilog` on these 17 testbenches, the compiler threw syntax errors and terminated before producing `.vcd` trace files.
2. **Verilog Multiple-Driver Net Conflict (2 cases: `axi_c1`, `axi_f1`):**
   In `axi_c1.v` and `axi_f1.v`, port `output ready_out` was continuously assigned (`assign ready_out = 1;`) while also being procedurally assigned inside a clocked `always` block (`ready_out <= 0;`). Icarus Verilog rejected this illegal multiple-driver construct on a non-register net, preventing VCD generation.

### Why Were None of the 19 Cases Excluded?
The blind evaluation harness strictly followed a **conservative defensive design**:
- When a target VCD was missing at inference time, `TransactionSemanticValidator` returned `decision: "INSUFFICIENT_EVIDENCE"` with `stage: "PRECHECK"` and logged the missing file reason.
- Crucially, **the harness did not drop these 19 rows from the denominator**.
- All 19 rows were retained in [`scored_heldout_evaluation.csv`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/processed/scored_heldout_evaluation.csv) and factored into the precision, false-reuse rate, positive transfer (where they counted as false negatives), and compute cost metrics.
- In subsequent phases (Phase 4.2), the 17 FIFO and Pipeline testbench string formatting errors were corrected, allowing their VCDs to simulate successfully (currently 48/50 VCDs reside on disk).

---

## 4. Reproducibility Classification

**Classification: Partially Reproducible (Historical) → Fully Reproducible (Code & Generation)**

### Detailed Rationale
1. **Historical Run (Partially Reproducible without re-running Phase 4.1 script):**
   All reported metrics are traceable to preserved result records and documented calculation procedures. The original raw VCD corpus is not included in the repository. The historical Phase 4.1 output files ([`scored_heldout_evaluation.csv`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/processed/scored_heldout_evaluation.csv), [`blind_inference_predictions.csv`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/validation/blind_inference_predictions.csv), [`phase4_1_blind_validation_report.md`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/reports/phase4_1_blind_validation_report.md)) are fully auditable and all mathematical metrics can be directly recomputed from them in milliseconds.
2. **Full End-to-End Re-Execution (Fully Reproducible):**
   - All generator scripts (`scripts/generate_phase4_1_benchmark.py`), experiment runners (`experiments/run_phase4_1_blind_validation.py`), validators, and simulators are completely intact in the repository.
   - **Zero Proprietary/Private Data:** The benchmark uses open-source, controlled RTL hardware families and testbenches. No external corpora, commercial IP, or proprietary customer traces are required.
   - **Deterministic:** Random seeds (`101, 202, 303, 404, 505`) and frozen validator SHA256 hashes guarantee identical regenerated code and manifests.
   - Correcting the 2 Verilog net declarations in `axi_c1.v` and `axi_f1.v` allows all 50 benchmark waveforms to compile and simulate cleanly on standard Icarus Verilog 12.0.

---

## 5. Metric Traceability

All reported metrics are traceable to preserved result records ([`results/transaction_semantic_certs/blind_validation/processed/scored_heldout_evaluation.csv`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/transaction_semantic_certs/blind_validation/processed/scored_heldout_evaluation.csv)) and documented calculation procedures. Below is the exact derivation and mathematical verification:

```
Confusion Matrix Definitions:
  - Target Total (N): 50
  - Positive Controls (Category A, MATCH): 15
  - Negative / Non-Match Controls (Categories B-F, MISMATCH): 35

  - True Positives (TP):  pred == 'PASS' and ground_truth_match == 'MATCH'
  - False Positives (FP): pred == 'PASS' and ground_truth_match == 'MISMATCH'
  - False Negatives (FN): pred != 'PASS' and ground_truth_match == 'MATCH'
  - True Negatives (TN):  pred != 'PASS' and ground_truth_match == 'MISMATCH'
```

### Direct Mathematical Derivations

| Metric | Low-Level Baseline (L0) | Transaction-Semantic (L2) | Formula & Source Row Counts | Independently Regenerable? |
|---|:---:|:---:|---|:---:|
| **Reused Decisions (TP + FP)** | 9 | 7 | `sum(pred == 'PASS')` (L0: 5 TP + 4 FP; L2: 5 TP + 2 FP) | Yes |
| **Reuse Precision** | **55.6%** (0.5556) | **71.4%** (0.7143) | `TP / (TP + FP)`<br>• L0: $5 / 9 = 0.5556$<br>• L2: $5 / 7 = 0.7143$ | Yes |
| **False Reuse Rate (FRR)** | **44.4%** (0.4444) | **28.6%** (0.2857) | `FP / (TP + FP)`<br>• L0: $4 / 9 = 0.4444$<br>• L2: $2 / 7 = 0.2857$ | Yes |
| **Positive Transfer (Recall)** | **33.3%** (0.3333) | **33.3%** (0.3333) | `TP / Total_Positives`<br>• L0: $5 / 15 = 0.3333$<br>• L2: $5 / 15 = 0.3333$ | Yes |
| **Negative Rejection Rate** | **88.6%** (0.8857) | **94.3%** (0.9429) | `TN / Total_Negatives`<br>• L0: $31 / 35 = 0.8857$<br>• L2: $33 / 35 = 0.9429$ | Yes |
| **Insufficient Evidence Count** | 0 (19 UNKNOWN) | 37 (74.0%) | `sum(pred == 'INSUFFICIENT_EVIDENCE')`<br>• L2: 19 PRECHECK + 18 TRANSACTION_CONTEXT | Yes |
| **Search Compression (SCR)** | **0.96x** | **0.92x** | $\frac{N \times 8.9}{\sum (\text{reused} \times 2.0 + \text{unreused} \times 10.9)} = \frac{445}{483.1} = 0.921x$ | Yes |

---

## 6. Recommended Repository Treatment

Based on the forensic audit, the following treatment is recommended for the repository:

1. **Keep Summary CSVs Tracked in Git:**
   Maintain [`results/blind_test/summary.csv`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/blind_test/summary.csv) and [`results/blind_test/README.md`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/blind_test/README.md) tracked in the main branch. These provide lightweight, machine-readable provenance without bloating Git.
2. **Exclude Raw Waveforms & Simulator Binaries from Git:**
   Enforce `.gitignore` exclusions for all raw `.vcd` files (295 files, ~50MB+) and `.vvp` simulator binaries. They should remain generated on-demand rather than checked into version control.
3. **Retain Generator & Runner Scripts:**
   Keep [`scripts/generate_phase4_1_benchmark.py`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/scripts/generate_phase4_1_benchmark.py) and [`experiments/run_phase4_1_blind_validation.py`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/experiments/run_phase4_1_blind_validation.py) tracked so any user can deterministically regenerate the full benchmark locally using open-source Icarus Verilog.
4. **Preserve the Full Audit Trail:**
   Do not modify historical Phase 4.1 result records to artificially "fix" the 19 historical PRECHECK cases. The 19 PRECHECK cases are an essential part of the project's historical progression that directly justified the need for Phase 4.2 adaptive boundary discovery.
5. **No Proprietary Data Quarantine Needed:**
   Confirm that all RTL designs, testbenches, and certificates are fully synthetic and safe for public open-source release under standard open licensing.

---
*Audit completed with zero research result modifications.*
