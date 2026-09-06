# V12 Structural Novelty Audit

## 1. Executive Summary

This document provides a formal, quantitative, and architectural audit of the structural and lexical novelty of the **V12 External Realistic Hardware Benchmark** relative to all previous iterations of the RCA-Reuse project (V7, V8, V10.1, V10.2, and V11).

The V12 benchmark was developed to rigorously address the core scientific challenge:
> *"Does verified RCA reuse retain its resolution and efficiency benefits on a new, structurally unfamiliar, more realistic hardware corpus that was NOT designed around the RCA-Reuse benchmark?"*

The audit confirms:
- **Lexical Novelty**: **85.1%** of RTL identifiers in V12 are completely novel compared to the entire historical corpus (V7–V11). Jaccard identifier similarity is **0.0524**, demonstrating over 94% lexical divergence.
- **Architectural Novelty**: All 10 baseline designs originate from authentic open-source IP cores (OpenCores, CirFix ASPLOS '22 benchmarks, open-source EDA repositories), spanning 5 previously unseen functional hardware domains.
- **Bug-Mechanism Novelty**: The injected bug mechanisms represent real-world hardware failure modes (refresh counter underflows, I2C clock stretching protocol violations, linked-list descriptor termination bugs, and cryptographic sponge padding rate truncations) rather than synthetic off-by-one counter flips.

---

## 2. Quantitative Lexical Divergence Metrics

An automated lexical scanner parsed all Verilog source files across historical benchmarks (`rtl/designs/`, `rtl/v10/`, `rtl/v11/`) and compared them against the V12 benchmark (`rtl/v12/`), stripping comments, metadata, and standard Verilog reserved keywords.

| Metric | Historical Corpus (V7–V11) | V12 External Benchmark | Combined / Divergence |
| :--- | :--- | :--- | :--- |
| **Analyzed Verilog Files** | 318 | 30 | 348 |
| **Unique Signal/State Identifiers** | 187 | 94 | 267 |
| **Novel Identifiers in V12** | — | **80** | **85.1% Novel** |
| **Shared / Overlapping Identifiers**| — | 14 | 14.9% |
| **Jaccard Token Similarity** | — | — | **0.0524 (94.8% Divergence)** |

### Shared Identifiers (14 total)
The only overlapping identifiers between historical benchmarks and V12 are generic Verilog primitives and standard control signals:
`count`, `counter`, `data`, `data_out`, `full`, `grant`, `next_state`, `ptr`, `req`, `state`, `valid`, `read`, `write`, `we`.

### Domain-Specific Novel Identifiers (80 total)
Sample novel identifiers unique to V12:
- **Memory Controllers**: `REFRESH_PERIOD`, `cas_timer`, `bank_addr`, `col_mask`, `precharge_timer`, `tag_hit`, `tag_array`, `line_valid`, `row_addr_reg`.
- **Bus & Protocol Controllers**: `ack_rec`, `scl_stretch`, `scl_oen`, `cpol_cpha`, `bit_phase`, `sample_pulse`, `start_cond`, `stop_cond`.
- **Interconnect & Arbitration**: `comb_grant`, `chan_prio`, `token_rotate`, `starve_cnt`, `lock_grant`, `last_grant`, `req_masked`.
- **DMA Controllers**: `byte_count`, `desc_eol`, `dma_state`, `burst_addr`, `link_ptr`, `irq_mask`, `pic_irr`, `pic_isr`.
- **Crypto & Arithmetic**: `delim_byte`, `byte_pad_cnt`, `pad_rate_limit`, `keccak_absorb`, `rem_restore`, `quot_sign`, `partial_rem`.

---

## 3. Structural & Architectural Comparison

The architectural topology of V12 represents a significant step forward in realism compared to the canonical designs in V7–V11.

```
+-----------------------------------------------------------------------------------+
| Historical Benchmark Topology (V7-V11)                                            |
|   Canonical FIFO / Simple AXI / Generic 3-State FSM / 3-Stage Linear Pipeline     |
|   [Flattened 1-2 state machines, direct single-cycle datapath transitions]        |
+-----------------------------------------------------------------------------------+
                                         VS
+-----------------------------------------------------------------------------------+
| V12 External Benchmark Topology                                                   |
|   - Multi-phase protocols (I2C SCL stretching, dynamic ACK window tracking)       |
|   - Hierarchical controller state logic (SDRAM precharge/activate/refresh timers) |
|   - Linked-list traversal logic (Scatter-Gather DMA descriptor end-of-list)       |
|   - Rotating priority masks (Fair round-robin arbitration with starvation guard)  |
|   - Sponge construction state machines (Keccak SHA-3 delimited rate padding)      |
+-----------------------------------------------------------------------------------+
```

### Key Structural Differences:

1. **State Space Complexity**:
   - Historical benchmarks used linear state sequences ($S_0 \to S_1 \to S_2$) with deterministic single-signal transitions.
   - V12 designs feature multi-dimensional state spaces where state transitions are governed by orthogonal timers (e.g. `cas_timer`, `precharge_timer`), protocol bus snooping (`scl_stretch`), and external descriptor chaining (`desc_eol`).

2. **Control vs Datapath Coupling**:
   - Historical benchmarks featured localized control logic tightly coupled to single registers.
   - V12 designs decouple control from datapath: DMA engine updates internal transfer byte counts, increments buffer pointers, and handles burst boundary wrapping across address pages simultaneously.

3. **Multi-Cycle Synchronization**:
   - V12 incorporates asynchronous handshake boundaries, clock stretching, and multi-cycle arithmetic (non-restoring radix-2 division with quotient sign inversion).

---

## 4. Hardware Domain Breakdown & Real-World Provenance

| Domain | Representative IP | Provenance / Upstream Core | Architectural Realism Features |
| :--- | :--- | :--- | :--- |
| **1. Memory Controllers** | `sdram_controller`, `cache_controller_l1` | CirFix ASPLOS '22 / OpenCores | Auto-refresh timing timers, multi-bank row/column address interleaving, cache tag tag-hit match logic, write-back dirty bit tracking. |
| **2. Bus Protocols** | `i2c_master_bit_ctrl`, `spi_master_fifo` | CirFix ASPLOS '22 / OpenCores | Open-drain SCL clock stretching, sub-cycle ACK sampling windows, multi-mode CPOL/CPHA phase alignment, start/stop setup margins. |
| **3. Interconnect & Arbitration** | `arbiter_round_robin`, `arbiter_priority` | Open-Source EDA IP Library | Rotating token masks to avoid lowest-index starvation, priority override lockup avoidance, combinational lookahead grant generation. |
| **4. DMA & Peripheral Control** | `dma_controller_sg`, `interrupt_controller_pic` | OpenCores DMA / OpenPIC | Scatter-gather linked-list pointer traversal, burst address wrap-around on 1KB boundaries, interrupt priority masking and nesting. |
| **5. Crypto & Arithmetic** | `sha3_keccak_padder`, `divider_radix2` | OpenCores SHA-3 / Verilog Arithmetic Lib | Sponge function multi-rate padding (1088-bit block delimitation), non-restoring divider remainder restoration and signed quotient adjustment. |

---

## 5. Bug-Mechanism Novelty

Unlike synthetic benchmarks where bugs are generated by randomly mutating single operators, every V12 bug reflects a documented failure mode in hardware design:

1. **`v12_mem_sdram_refresh` (Refresh Counter Underflow)**:
   - *Failure Mechanism*: SDRAM periodic refresh interval counter reloads `REFRESH_PERIOD - 2` instead of `REFRESH_PERIOD - 1`, causing refresh frequency drift and memory cell discharge during long read bursts.
2. **`v12_bus_i2c_stretch` (Clock Stretch Deadlock)**:
   - *Failure Mechanism*: Bit-level I2C controller fails to release `scl_oen` when an external slave holds `scl` low, leading to infinite bus hold and bus deadlock.
3. **`v12_bus_i2c_ackphase` (Sub-Cycle ACK Sampling Overwrite)**:
   - *Failure Mechanism*: Master samples `ack_rec` continuously rather than only during the qualified `sample_pulse` window, causing the ACK bit to be overwritten when the slave releases the open-drain bus.
4. **`v12_arb_rr_mask` (Arbiter Starvation via Stale Mask)**:
   - *Failure Mechanism*: Round-robin arbiter updates the higher-priority request mask with the raw request vector rather than the rotated mask, starving master 0 under heavy load.
5. **`v12_dma_desc_term` (Scatter-Gather Chain Early Termination)**:
   - *Failure Mechanism*: DMA controller evaluates end-of-list descriptor flag before verifying transfer byte count reaches zero, terminating prematurely on multi-block transfers.
6. **`v12_acc_sha3_pad_delim` (Keccak Sponge Delimiter Byte Placement)**:
   - *Failure Mechanism*: Keccak padding logic inserts NIST `0x06` delimiter byte at bit offset 0 instead of byte boundary, corrupting cryptographic digest calculation.

---

## 6. Structural Controls for Evaluation Integrity

To evaluate whether System B's verification gate functions correctly on unfamiliar hardware, the V12 benchmark includes 10 rigorous negative control cases (33.3% of the corpus):

1. **Adversarial Negative Controls (5 cases)**:
   - Possess high syntactic and superficial similarity to historical bugs (e.g. identical signal names, similar counter logic), but differing root causes and assertion constraints.
   - *Target System Behavior*: Plain LLM or Naive Reuse is tricked into false reuse; System B's semantic verification gate MUST reject reuse and fall back to scratch reasoning.
2. **Incomplete Evidence Negative Controls (5 cases)**:
   - Missing assertion telemetry, truncated waveforms, or ambiguous symptom signatures.
   - *Target System Behavior*: Unverified systems make unsafe hallucinatory repairs; System B's verification gate MUST detect insufficient evidence and trigger safe fallback.

---

## 7. Conclusion

The V12 External Realistic Hardware Benchmark fulfills all requirements for external validity:
- Zero overlap with V7 training data.
- Zero inclusion in trusted RCA memory.
- >85% lexical divergence.
- Authentic open-source hardware architectures.
- Rigorous physical simulation oracle with 100% pre-fail and post-pass determinism.
