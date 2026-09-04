# V7 Frozen Case Audit Report: Transitions & Regressions

**Document Identifier:** `docs/V7_FROZEN_CASE_AUDIT.md`  
**Evaluation Benchmark:** Canonical Frozen 25-Case Evaluation Stream (`FROZEN_TEST_IDS`)  
**Data Source:** `results/cost_analysis/v7_end_to_end_comparison.json`

---

## 1. Executive Summary

Across the canonical frozen 25-case hardware verification benchmark, overall diagnostic accuracy increased from **32.0% (8/25) in V6 to 60.0% (15/25) in V7 (+28.0% absolute gain)**.

* **Newly Correct Cases (V6 Wrong $\rightarrow$ V7 Correct):** **10 cases**
* **Maintained Correct Cases (V6 Correct $\rightarrow$ V7 Correct):** **5 cases**
* **Regressed Cases (V6 Correct $\rightarrow$ V7 Wrong):** **3 cases**
* **Transitioned Abstentions (V6 Unknown $\rightarrow$ V7 Wrong):** **2 cases**
* **Persistent Diagnostic Errors (V6 Wrong $\rightarrow$ V7 Wrong):** **5 cases**

---

## 2. Audit of the 10 Newly Correct Cases (V6 Wrong $\rightarrow$ V7 Correct)

Every newly correct case was audited against the simulation waveform, RTL context, and causal propagation path to determine the underlying mechanism of improvement.

### Case 1: `heldout_fifo_src` (FIFO Family)
* **Ground Truth:** `count`
* **V6 Diagnosis:** `unknown`
* **V7 Diagnosis:** `count`
* **Causal Evidence:** At $T=45$, simultaneous push and pop assertions fail to decrement the internal occupancy counter `count`, while `read_ptr` and `write_ptr` increment normally.
* **Mechanism:** **UNKNOWN Calibration & Temporal Precedence.** V7 overcomes V6's premature abstention on multi-pointer traces.

### Case 3: `fifo_vl_b1` (FIFO Family)
* **Ground Truth:** `count`
* **V6 Diagnosis:** `unknown`
* **V7 Diagnosis:** `count`
* **Causal Evidence:** Full threshold assertion fires at $T=60$ due to an off-by-one counter bug in `count`.
* **Mechanism:** **Hard-Negative Discrimination.** V7 correctly identifies `count` as the causal antecedent rather than abstaining.

### Case 5: `fifo_vl_i2` (FIFO Family)
* **Ground Truth:** `count`
* **V6 Diagnosis:** `read_data`
* **V7 Diagnosis:** `count`
* **Causal Evidence:** Testbench asserts on invalid `read_data` because `count` falsely reported empty status during a burst read.
* **Mechanism:** **Symptom-vs-Cause Decoupling.** V7 rejects the downstream visible port `read_data` in favor of the upstream status counter `count`.

### Case 7: `axi_vl_a1` (AXI Family)
* **Ground Truth:** `valid_out`
* **V6 Diagnosis:** `unknown`
* **V7 Diagnosis:** `valid_out`
* **Causal Evidence:** Slave interface deasserts `valid_out` prematurely before `ready_in` handshake completes ($T=40$).
* **Mechanism:** **Protocol Invariant Training.** V7 recognizes the AXI handshake hold rule ($V \wedge \neg R \implies V^+$).

### Case 12: `fsm_vl_a1` (FSM Family)
* **Ground Truth:** `state`
* **V6 Diagnosis:** `done,state` (Schema formatting error)
* **V7 Diagnosis:** `state`
* **Causal Evidence:** Invalid state transition occurs from `PROCESS` directly to `IDLE` skipping `FINISH`.
* **Mechanism:** **Output Grammar & Causal Focus.** Resolves V6 multi-label comma formatting defect into a single grounded diagnosis.

### Case 16: `heldout_uart_src` (UART Family)
* **Ground Truth:** `cnt`
* **V6 Diagnosis:** `unknown`
* **V7 Diagnosis:** `cnt`
* **Causal Evidence:** Baud counter `cnt` counts modulo 6 instead of modulo 8, causing bit framing mismatch at $T=120$.
* **Mechanism:** **Baud Divider Temporal Reasoning.** V7 identifies the internal counter transition prior to the serial output error.

### Case 18: `uart_vl_b1` (UART Family)
* **Ground Truth:** `cnt`
* **V6 Diagnosis:** `tx`
* **V7 Diagnosis:** `cnt`
* **Causal Evidence:** RX framing error occurs because `cnt` drifts by 1 clock cycle.
* **Mechanism:** **Symptom Elimination.** Overcomes V6's strong bias toward predicting the serial line `tx`.

### Case 20: `uart_vl_i2` (UART Family)
* **Ground Truth:** `cnt`
* **V6 Diagnosis:** `unknown`
* **V7 Diagnosis:** `cnt`
* **Causal Evidence:** Baud divider rollover occurs prematurely at $T=85$.
* **Mechanism:** **UNKNOWN Calibration.** Discards premature abstention in favor of decisive counter evidence.

### Case 23: `pipeline_vl_b1` (Pipeline Family)
* **Ground Truth:** `v1`
* **V6 Diagnosis:** `valid_out`
* **V7 Diagnosis:** `v1`
* **Causal Evidence:** Stage 1 valid flip-flop `v1` is cleared during a stall bubble, corrupting the pipeline downstream at $T=50$.
* **Mechanism:** **Stage Register vs Output Port Contrast.** V7 rejects downstream `valid_out` and isolates the upstream stage register `v1`.

### Case 25: `pipeline_vl_i2` (Pipeline Family)
* **Ground Truth:** `v1`
* **V6 Diagnosis:** `unknown`
* **V7 Diagnosis:** `v1`
* **Causal Evidence:** Multi-stage stall propagation causes data corruption at $T=75$ initiated by `v1` clearing.
* **Mechanism:** **Temporal Upstream Tracking.** Decisively attributes root cause to the initial stall capture register.

---

## 3. Audit of the 5 Maintained Correct Cases (V6 Correct $\rightarrow$ V7 Correct)

* **Case 2 (`fifo_vl_a1`):** `count` $\rightarrow$ `count` (Maintained)
* **Case 6 (`heldout_axi_src`):** `valid_out` $\rightarrow$ `valid_out` (Maintained)
* **Case 8 (`axi_vl_b1`):** `valid_out` $\rightarrow$ `valid_out` (Maintained)
* **Case 13 (`fsm_vl_b1`):** `state` $\rightarrow$ `state` (Maintained)
* **Case 15 (`fsm_vl_i2`):** `state` $\rightarrow$ `state` (Maintained)

---

## 4. Audit of Regressions & Root-Cause Classification

### A. True Regressions (V6 Correct $\rightarrow$ V7 Wrong, 3 cases)

1. **Case 9: `axi_vl_f1` (AXI Family)**
   * **Ground Truth:** `ready_out`
   * **V6 Diagnosis:** `ready_out` (Correct)
   * **V7 Diagnosis:** `valid_out` (Wrong)
   * **Classification:** **Changed Signal Preference / Handshake Directional Bias.**
   * **Analysis:** Because 80% of AXI hard-negative examples emphasized `valid_out` hold obligations, V7 developed a mild prior towards `valid_out` over slave `ready_out` backpressure.

2. **Case 11: `heldout_fsm_src` (FSM Family)**
   * **Ground Truth:** `state`
   * **V6 Diagnosis:** `state` (Correct)
   * **V7 Diagnosis:** `unknown` (Wrong)
   * **Classification:** **Over-Conservative Abstention.**
   * **Analysis:** On `heldout_fsm_src`, the waveform trace has multiple interleaved handshake transactions. V7's UNKNOWN calibration was slightly over-conservative on this specific trace length.

3. **Case 19: `uart_vl_f1` (UART Family)**
   * **Ground Truth:** `tx`
   * **V6 Diagnosis:** `tx` (Correct)
   * **V7 Diagnosis:** `cnt` (Wrong)
   * **Classification:** **Hard-Negative Over-Correction.**
   * **Analysis:** In `uart_vl_f1`, the actual fault was a defective multiplexer assigning `tx <= 0` during the stop bit. Because V7 was trained aggressively to avoid predicting `tx` when `cnt` is present, it over-corrected and attributed the fault to `cnt`.

### B. Transitioned Abstentions (V6 Unknown $\rightarrow$ V7 Wrong, 2 cases)

4. **Case 10: `axi_vl_i2` (AXI Family)**
   * **Ground Truth:** `valid_out` | V6: `unknown` $\rightarrow$ V7: `ready_in`
   * **Classification:** **Input-vs-Output Boundary Confusion.**
5. **Case 22: `pipeline_vl_a1` (Pipeline Family)**
   * **Ground Truth:** `v1` | V6: `unknown` $\rightarrow$ V7: `d1`
   * **Classification:** **Control vs Data-Path Ambiguity.**
