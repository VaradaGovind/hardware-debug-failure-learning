# V7 Dataset Scientific Audit Report

**Document Identifier:** `docs/V7_DATASET_AUDIT.md`  
**Dataset Version:** V7 Canonical Causal Discrimination Dataset  
**Target Storage Location:** `~/.cache/rca-reuse\v7\datasets\`  
**Generator Script:** `scripts/build_v7_canonical_dataset.py`  
**Audit Tool:** `scripts/audit_v7_dataset.py`  
**Metrics Summary:** `results/reports/v7_dataset_audit_metrics.json`

---

## 1. Executive Summary & Core Dataset Metrics

The V7 dataset was constructed to address small language model (1.5B) failure modes in hardware root-cause analysis—specifically downstream symptom selection, tightly-coupled register ambiguity, and uncalibrated abstention. 

* **Total Verified Samples:** **1,170**
* **Train Split:** **935 samples (79.9%)**
* **Validation Split:** **235 samples (20.1%)**
* **Target Window Adherence:** Successfully hits the target 800–1,200 sample window.
* **Automated Quality Gates:** 12/12 quality checks passed in generator and verified in pytest.

---

## 2. Category & Provenance Breakdown

Every sample in the V7 dataset is tagged with immutable source origin, generator provenance, and open-source license metadata.

### Methodological 4-Tier Breakdown

| Category | Samples | Proportion | Train Count | Val Count | Primary Function |
|---|:---:|:---:|:---:|:---:|---|
| **Category A: External / Open PR Bug Patterns** | **180** | **15.4%** | 142 | 38 | Real open-source PR bug taxonomy from HWE-bench, OpenCores, and VerilogEval. |
| **Category B: Simulation-Backed Synthetic Mutations** | **266** | **22.7%** | 214 | 52 | Positive causal root-cause pairs verified via `iverilog` waveform simulation. |
| **Category C: Hard-Negative Causal Discrimination** | **595** | **50.9%** | 474 | 121 | Multi-candidate audit pairs explicitly contrasting cause vs downstream symptom, passive input, or correlated internal. |
| **Category D: Calibrated UNKNOWN Controls** | **129** | **11.0%** | 105 | 24 | Truncated waveforms, unprobed internal nodes, and symmetric multi-channel ambiguities requiring abstention. |
| **Total** | **1,170** | **100.0%** | **935** | **235** | Complete V7 Canonical Corpus |

### Detailed Dataset Origin Distribution

| Source Identifier (`source_dataset`) | Total Count | Proportion | Train Split | Validation Split |
|---|:---:|:---:|:---:|:---:|
| `hard_negative_causal_discrimination` | 595 | 50.9% | 474 | 121 |
| `simulation_backed_variant_catalog` | 236 | 20.2% | 191 | 45 |
| `insufficient_evidence_control` | 129 | 11.0% | 105 | 24 |
| `hwe_bench_pattern` | 90 | 7.7% | 72 | 18 |
| `opencores_pr_pattern` | 45 | 3.8% | 36 | 9 |
| `verilog_eval_pattern` | 45 | 3.8% | 34 | 11 |
| `simulation_backed_bug_catalog` | 30 | 2.6% | 23 | 7 |

---

## 3. Hardware Design Family Distribution

The dataset spans five distinct hardware verification families with balanced representation:

| Hardware Family | Total Samples | Proportion | Train Count | Val Count | Key Verification Challenges |
|---|:---:|:---:|:---:|:---:|---|
| **Pipeline** | **297** | 25.4% | 228 | 69 | Multi-stage stall propagation, forwarding hazard bypass, flush token desynchronization. |
| **FIFO** | **285** | 24.4% | 222 | 63 | Pointer wrap-around, simultaneous read/write occupancy calculation, empty/full thresholding. |
| **UART** | **211** | 18.0% | 190 | 21 | Baud clock divider drift, stop bit framing errors, RX oversampling phase lock. |
| **AXI** | **210** | 17.9% | 168 | 42 | Handshake hold invariant violations, backpressure ready deadlock, burst beat counter bounds. |
| **FSM** | **167** | 14.3% | 127 | 40 | Deadlock states, illegal state transitions, one-hot encoding glitches, output strobe pulse timing. |

---

## 4. Structural Diversity & Multiplicity Analysis

### Unique Underlying RTL Codebases & Source Cases
* **Total Unique RTL Codebases:** **248 distinct architectures** (Train: 204, Val: 61).
* **Cross-Split RTL Code Sharing:** 17 common standard interface templates (27.9% of Val RTLs) share structural top-level scaffolding with different internal logic.
* **Total Unique Seed Bug Cases:** **446 unique bug scenarios** (Train: 356, Val: 90).
* **Cross-Split Seed Bug Overlap:** **0 cases (0.0% overlap)**. Every bug in validation is completely unseen during training.

### Derivation Multiplicity (Samples Derived per Underlying Bug)
Each seed bug pattern generates between 1 and 6 training/validation samples to construct multi-candidate causal pairs:
* **1 sample / bug (180 bug patterns):** Standalone positive RCA PR patterns (Category A).
* **2 samples / bug (33 bug patterns):** Positive RCA + 1 hard negative or UNKNOWN control.
* **3 samples / bug (67 bug patterns):** Positive RCA + symptom hard negative + passive input negative.
* **4 samples / bug (113 bug patterns):** Positive RCA + symptom negative + passive negative + correlated internal negative.
* **5 samples / bug (47 bug patterns):** Full multi-candidate suite + UNKNOWN ambiguous trace.
* **6 samples / bug (6 bug patterns):** Exhaustive multi-candidate suite across all candidate permutations.

### Hard-Negative Structural Sharing
* **100% of the 595 Hard Negatives** are derived directly from the **266 simulation-backed seed cases**.
* *Design Rationale:* Generating hard negatives from the exact same simulation runs as the positive RCA cases forces the model to evaluate the *causal chain* rather than relying on superficial token differences in the RTL context.

---

## 5. Quality Gate Verification

All 12 automated data quality gates passed with zero violations:
1. Schema & Field Completeness (100%)
2. Zero Duplicate Identifiers (100%)
3. Ground Truth Signal Validity (100%)
4. Provenance & License Tracking (100%)
5. Zero Leakage Against Frozen Test Set (100%)
6. Zero Ground Truth in Human Prompts (100%)
7. Causal Plausibility & Temporal Precedence (100%)
8. Target Signal Structural Grounding (100%)
9. Hard Negative Label Accuracy (100%)
10. UNKNOWN Abstention Consistency (100%)
11. Design Family Class Balance (100%)
12. Grouped Split Independence (100%)
