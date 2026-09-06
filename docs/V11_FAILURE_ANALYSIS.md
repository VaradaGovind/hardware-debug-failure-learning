# V11 Failure Forensics & Post-Mortem Analysis

**Experiment Identifier**: `V11_BENCHMARK_EXPANSION_AND_GENERALIZATION`  
**Dataset Size**: $N = 100$ independent hardware debugging failure cases  
**Scope**: In-Depth Forensic Analysis of Discordant Cases, Failed Diagnoses, and Ablation Regressions  

---

## 1. Executive Failure & Transition Overview

Across the 100 benchmark cases:
* **Concordant Resolution Pairs ($92$ cases)**:
  * **Both Resolved (40 cases)**: Standard bugs where both the 1.5B model and verified reuse succeeded.
  * **Neither Resolved (52 cases)**: Difficult cases including all 30 Category C negative/incomplete stress tests and 22 challenging Category A/B cases where both systems failed.
* **Discordant Pairs ($8$ cases)**:
  * **System A Only Resolved ($b = 0$ cases)**: System B never underperformed System A. Zero regressions detected.
  * **System B Only Resolved ($c = 8$ cases)**: Cases where the 1.5B model failed but verified reuse succeeded.
* **Safety & False Reuse Analysis**:
  * **System B (Verified)**: 0 false reuses across all 100 cases (100% precision). 30/30 negative stress tests safely rejected (100% negative rejection rate).
  * **Ablation B (Unverified)**: 15 false reuses on adversarial negatives, collapsing precision to 82.4%.

---

## 2. In-Depth Analysis of System B Wins ($c = 8$ Discordant Cases)

### Group 1: Renamed Signal Localization Failures (Category A, 5 Cases)
* **Cases**: `v11_fifo_ren_occupancy`, `v11_fifo_ren_level`, `v11_fsm_ren_currst`, `v11_fsm_ren_seqstate`, `v11_uart_ren_bauddiv`.
* **Hardware Families**: FIFO (2), FSM (2), UART (1).
* **Defect Class**: Core simultaneous R/W, sequence deadlock, and baud accumulator drift where primary state/counter nets were renamed (`count` $\to$ `occupancy`/`fifo_level`; `state` $\to$ `curr_state`/`seq_state`; `cnt` $\to$ `baud_div`).
* **System A Behavior**: The 1.5B model exhibited prompt sensitivity to non-standard signal names. Instead of identifying `occupancy` or `curr_state`, it hallucinated that external interface wires (`write_en`, `in_bit`, `tx_pin`) were defective and attempted to patch input ports, resulting in syntax errors or simulation assertion failures.
* **System B Behavior**: Semantic verification checked the structural AST and trace invariants, correctly identifying that `occupancy` matched the behavior of `count` from trusted memory. The reused diagnosis correctly targeted the renamed net, allowing `V11PatchSynthesizer` to synthesize the fix. Simulation assertions passed.

### Group 2: Structural Refactoring Failures (Category B, 3 Cases)
* **Cases**: `v11_fifo_str_splitalways`, `v11_axi_str_skidbuffer`, `v11_pipe_str_splitdatapath`.
* **Hardware Families**: FIFO (1), AXI (1), Pipeline (1).
* **Defect Class**: Separated control/datapath always-blocks, elastic skid buffer handshakes, and decoupled hazard control logic.
* **System A Behavior**: The 1.5B model failed to trace multi-block dependencies across decomposed always-blocks, repeatedly misdiagnosing datapath registers instead of the control gating condition.
* **System B Behavior**: The AST-level invariant verifier recognized the underlying sequential update invariant despite the split block structure. It supplied the verified diagnosis, enabling successful repair and assertion satisfaction.

---

## 3. Analysis of Unresolved Cases (52 Cases)

The 52 unresolved cases break down into two distinct groups:

### A. Category C Negative Stress Controls (30 Cases)
* **15 Adversarial Negatives**: Designs exhibiting superficial lexical similarity to canonical sources, but whose underlying defects are distinct (e.g., pointer overflow `write_ptr` wrap, reset polarity inversion, framing bit truncation, credit underflow).
* **15 Incomplete-Trace Negatives**: Truncated simulation traces ending before the critical failure cycle, or omitted internal nets.
* **Why Neither System Resolved**:
  * System B's semantic verification gate correctly detected causal divergence or lack of observability, rejecting reuse and falling back to System A.
  * In fallback, the 1.5B LLM was unable to resolve these difficult corner-case bugs from scratch under tight context.
  * **Critical Confirmation**: These 30 cases were designed as safety stress tests. Failure to resolve them via reuse is the **correct and safe behavior**.

### B. Complex Structural & Timing Mismatches (22 Cases)
* **Cases**: 8 Category A cases + 14 Category B cases.
* **Root Causes**:
  * Multi-clock domain crossing wrappers (`v11_fifo_str_twoport`, `v11_uart_str_dualclock`).
  * One-hot state encoding requiring multi-bit transition patches (`v11_fsm_str_onehot`).
  * Elastic ring pipelines with distributed token backpressure (`v11_pipe_str_elasticring`).
* **Why Verification Rejected Reuse**:
  * The semantic verification gate enforces strict invariant checks. When AST graph edit distance or causal waveforms deviate beyond $p < 0.85$, reuse is prudently aborted.
  * In fallback, the 1.5B model lacked the reasoning depth to synthesize multi-line structural rewrites.

---

## 4. Post-Mortem of Ablation B Regressions (The Cost of Unverified Reuse)

In the unverified reuse ablation:
* **False Reuses Accepted**: 15 cases (all 15 Category C adversarial negatives).
* **Mechanism of Regression**:
  * For example, in `v11_fifo_neg_adv_ptrovf`, the true bug was a pointer wrap in `write_ptr`. Naive family-level reuse blindly applied the `count` simultaneous R/W patch.
  * The synthesized patch modified `count` while leaving `write_ptr` broken. In simulation, FIFO memory was overwritten and corrupted, causing fatal assertion failures.
* **Conclusion**: Semantic verification is non-negotiable for autonomous hardware repair. It prevented 15 destructive patches that naive reuse would have applied.
