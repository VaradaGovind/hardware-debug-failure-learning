# Frozen 25-Case Benchmark Integrity Verification

**Audit Date:** September 3, 2026  
**Auditor:** Google DeepMind Advanced Agentic Coding Pair  
**Standard:** Strict Verification Pass (Byte-for-byte SHA256 integrity, zero label shift, zero file missingness)  
**Canonical Stream Definition File:** `experiments/run_rca_vs_reuse_controlled_comparison.py`  
**Git History Status:** 100% Immutable (Single commit: `9976985ce76635833c60370cf81af6356828d4b4`, August 31, 2026)  
**File Hash:** `bd65cd7b4a9f18a2ae044458315ea05537559e21191560946d4a2d8d85f2066d` (15,625 bytes)  

---

## 1. Executive Summary

The frozen 25-case sequential arrival benchmark represents the invariant ground truth against which all RCA models (V4, V5, V6, V7) and reuse architectures (V5, V7, V8) are evaluated.

This audit independently verifies that:
1. **Zero Drift**: The canonical generator script `experiments/run_rca_vs_reuse_controlled_comparison.py` has never been altered since its initial commit.
2. **Complete Asset Availability**: All 25 Verilog design files (`rtl/designs/*.v`) and all 25 Verilog testbench files (`rtl/testbenches/*_tb.v`) exist on disk, compile cleanly via Icarus Verilog (`iverilog`), and execute to completion via `vvp`.
3. **Exact Label Fidelity**: Ground truth target signals, design families, defect mechanism labels, and match/mismatch annotations match their historical specifications with 100% fidelity.

---

## 2. Benchmark Case Inventory & Checksums

| Index | Target ID | Family | Match Type | Ground Truth Signal | Defect Mechanism | Design SHA256 (Prefix) | Testbench SHA256 (Prefix) |
|:---:|---|:---:|:---:|:---:|---|:---:|:---:|
| 1 | `heldout_fifo_src` | fifo | MATCH | `count` | FIFO_SIMULTANEOUS_RW | `4a4d2cfd4fd7` | `cf1255bfcb87` |
| 2 | `fifo_vl_a1` | fifo | MATCH | `count` | FIFO_SIMULTANEOUS_RW | `4a4d2cfd4fd7` | `ba61614f2a0d` |
| 3 | `fifo_vl_b1` | fifo | MATCH | `count` | FIFO_SIMULTANEOUS_RW | `4a4d2cfd4fd7` | `adc3dbd736a5` |
| 4 | `fifo_vl_f1` | fifo | MISMATCH | `write_ptr` | FIFO_PTR_OVERFLOW | `29ea54b93a20` | `fa605ae220b1` |
| 5 | `fifo_vl_i2` | fifo | MISMATCH | `count` | FIFO_SIMULTANEOUS_RW | `9ab1c9559db5` | `35cbc4974e48` |
| 6 | `heldout_axi_src` | axi | MATCH | `valid_out` | AXI_HANDSHAKE_HOLD | `aff1177d8a43` | `3d751a01df65` |
| 7 | `axi_vl_a1` | axi | MATCH | `valid_out` | AXI_HANDSHAKE_HOLD | `aff1177d8a43` | `4629d9969bc8` |
| 8 | `axi_vl_b1` | axi | MATCH | `valid_out` | AXI_HANDSHAKE_HOLD | `aff1177d8a43` | `eb940d5a225e` |
| 9 | `axi_vl_f1` | axi | MISMATCH | `ready_out` | AXI_EARLY_READY | `fe9a5e9287f0` | `7325aa2e63fa` |
| 10 | `axi_vl_i2` | axi | MISMATCH | `valid_out` | AXI_HANDSHAKE_HOLD | `fe9a5e9287f0` | `69de57c6fded` |
| 11 | `heldout_fsm_src` | fsm | MATCH | `state` | FSM_STUCK_STATE | `6d039679f63d` | `1cdfed0b7a04` |
| 12 | `fsm_vl_a1` | fsm | MATCH | `state` | FSM_STUCK_STATE | `6d039679f63d` | `00dbf8c044e9` |
| 13 | `fsm_vl_b1` | fsm | MATCH | `state` | FSM_STUCK_STATE | `6d039679f63d` | `248a565fbd1d` |
| 14 | `fsm_vl_f1` | fsm | MISMATCH | `done` | FSM_OUTPUT_TIMING | `30a329abebf2` | `da6ce26aa168` |
| 15 | `fsm_vl_i2` | fsm | MISMATCH | `state` | FSM_STUCK_STATE | `6d039679f63d` | `87778ff884dd` |
| 16 | `heldout_uart_src` | uart | MATCH | `cnt` | UART_BAUD_DIVIDER | `0b7512ba6822` | `3c907174de7e` |
| 17 | `uart_vl_a1` | uart | MATCH | `cnt` | UART_BAUD_DIVIDER | `0b7512ba6822` | `e5667e6dcc9a` |
| 18 | `uart_vl_b1` | uart | MATCH | `cnt` | UART_BAUD_DIVIDER | `0b7512ba6822` | `c42ab99a5ad2` |
| 19 | `uart_vl_f1` | uart | MISMATCH | `tx` | UART_STOP_BIT_GEN | `017f70ab9c85` | `3bc288afbc52` |
| 20 | `uart_vl_i2` | uart | MISMATCH | `cnt` | UART_BAUD_DIVIDER | `80247c4e13cc` | `0252f0dda529` |
| 21 | `heldout_pipe_src` | pipeline | MATCH | `v1` | PIPE_STALL_BUBBLE | `39a2ab2b5372` | `7a94efc67853` |
| 22 | `pipeline_vl_a1` | pipeline | MATCH | `v1` | PIPE_STALL_BUBBLE | `39a2ab2b5372` | `7f6a50fd3d3c` |
| 23 | `pipeline_vl_b1` | pipeline | MATCH | `v1` | PIPE_STALL_BUBBLE | `39a2ab2b5372` | `2baf1b48e4dc` |
| 24 | `pipeline_vl_f1` | pipeline | MISMATCH | `d1` | PIPE_FORWARD_HAZARD | `e5e8d7d6fac9` | `8144435b7780` |
| 25 | `pipeline_vl_i2` | pipeline | MISMATCH | `v1` | PIPE_STALL_BUBBLE | `fa686b7df404` | `71379b0cc99f` |

---

## 3. Structural & Semantic Balance

* **Total Manifestations**: 25
* **Hardware Families**: 5 (FIFO, AXI, FSM, UART, Pipeline) — exactly 5 cases per family.
* **Source Manifestations**: 5 (1 per family).
* **Target Arrivals**: 20 (4 per family).
  * **Positive Targets (MATCH)**: 10 (2 per family) — representing variable-latency, stall, or transaction variations of the identical defect mechanism.
  * **Adversarial Negative Targets (MISMATCH)**: 5 (1 per family) — exhibiting identical observable failure symptoms (e.g. "Data Mismatch", "Timeout") but originating from completely different internal defect mechanisms.
  * **Incomplete Trace Targets (MISMATCH)**: 5 (1 per family) — truncated waveforms simulating incomplete simulation runs or premature timeouts.

---

## 4. Verification Conclusion

* **Missing Files**: 0 / 50 (25 designs, 25 testbenches verified present).
* **Simulation Compilation Rate**: 100% (25/25 compile and execute).
* **Hash Divergence**: 0% (All files match historical checksums).
* **Verdict**: **VERIFIED — FROZEN BENCHMARK INTACT & UNALTERED**.
