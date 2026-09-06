# V12 External Corpus Selection & Benchmark Specification

**Evaluation Date**: September 6, 2026  
**Experiment Identifier**: `V12_EXTERNAL_CORPUS_VALIDATION`  
**Base Architecture**: `Qwen/Qwen2.5-Coder-1.5B-Instruct` + `soup_v7_qwen_lora` (`best_v7_checkpoint`), $T=0.0$  
**Evaluation Scope**: Real-World & External Hardware Corpus (OpenCores, CirFix ASPLOS '22, and Realistic Hardware IP)  

---

## 1. Executive Motivation & Context

In Experiments V10.1, V10.2, and V11, the RCA-Reuse architecture was evaluated on a synthetic benchmark organized around five canonical hardware families: FIFO, AXI, FSM, UART, and Pipeline. While Experiment V11 established statistical significance ($N=100$, McNemar $p = 0.007812 < 0.01$), the synthetic benchmark possesses structural regularities that may artificially favor reuse.

The primary objective of Experiment V12 is to evaluate whether verified LLM-RCA reuse generalizes to **unfamiliar, realistic, and external hardware RTL** that was never designed around the RCA-Reuse project.

---

## 2. External Corpus Selection Criteria

To ensure genuine real-world validity, the selected external corpus satisfies the following mandatory criteria:
1. **Provenance & Availability**: Sourced from peer-reviewed hardware benchmarks (CirFix ASPLOS '22 artifact `hammad-a/verilog_repair`) and established open-source hardware repositories (OpenCores, standard EDA IP).
2. **Open-Source Licensing**: Permissive or standard open-source licenses (MIT, BSD, Apache-2.0, LGPL).
3. **Structural Disconnection**: Must NOT be derived from or share module templates with the existing V10/V11 FIFO, AXI, FSM, UART, or Pipeline designs.
4. **Deterministic Simulation**: All designs and testbenches must compile and simulate deterministically with Icarus Verilog (`iverilog` + `vvp`) without proprietary simulator dependencies.
5. **Ground-Truth Machine Verification**: Every bug must be reproducibly detectable (FAIL pre-repair) and verifiable (PASS post-repair).

---

## 3. Selected Hardware Domains & Designs

The V12 benchmark comprises **30 high-fidelity cases** partitioned symmetrically across 5 realistic hardware domains (6 cases per domain):

```
                        V12 EXTERNAL BENCHMARK DOMAINS (30 Cases)
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │ 5 Realistic Hardware Domains: 6 Cases Each (3 Pos + 1 Structural + 2 Negatives) │
  └─────────────────────────────────────────────────────────────────────────────────┘
         │               │                │               │               │
         ▼               ▼                ▼               ▼               ▼
    [ Memory ]      [ Bus/Serial ]  [ Interconnect ]   [ DMA/Ctrl ]    [ Crypto/Arith ]
   SDRAM / Cache     I2C / SPI       Arbiter Token/     Scatter-Gather   SHA-3 Padder /
    Controllers     Controllers         Priority          DMA / PIC        Divider
```

### Domain 1: Memory Controllers (`v12_mem_*`, 6 cases)
* **Primary IP**: ISSI IS42S16160G-7 SDRAM Controller (`sdram_controller`) and Direct-Mapped / Set-Associative L1 Cache Controller (`cache_controller_l1`).
* **RTL Characteristics**: Multi-state SDRAM command sequencers (INIT, PRECHARGE, ACTIVATE, CAS read/write latency), refresh period timers, row/column/bank address multiplexing, cache tag comparisons, and dirty line writebacks.
* **Bug Scope**: Refresh counter slip, bank address decoding error, precharge timing violation, cache tag hit logic corruption.

### Domain 2: Bus & Interface Controllers (`v12_bus_*`, 6 cases)
* **Primary IP**: WISHBONE compliant I2C Master Bit Controller (`i2c_master_bit_ctrl`, Richard Herveille / OpenCores) and SPI Bus Interface Controller (`spi_master_fifo`).
* **RTL Characteristics**: SCL/SDA tri-state open-drain bus drives, clock stretching detection, start/stop condition generation, multi-phase CPOL/CPHA clock generation, and shift register framing.
* **Bug Scope**: SCL clock stretching lockup, start bit setup timing violation, SPI CPOL phase inversion, shift register overflow.

### Domain 3: Interconnect & Arbitration Logic (`v12_arb_*`, 6 cases)
* **Primary IP**: Rotating Token Round-Robin Arbiter (`arbiter_round_robin`) and 4-Channel Fixed/Rotating Priority Arbiter (`arbiter_priority`).
* **RTL Characteristics**: Fair multi-master request arbitration, rotating priority masks, single-cycle grant locks, and starvation avoidance circuits.
* **Bug Scope**: Mask generation wrap bug, grant lock holding under request drop, starvation of low-priority client, unmasked simultaneous grant glitch.

### Domain 4: DMA & Peripheral Control (`v12_dma_*`, 6 cases)
* **Primary IP**: Scatter-Gather DMA Controller (`dma_controller_sg`) and Programmable Priority Interrupt Controller (`interrupt_controller_pic`).
* **RTL Characteristics**: Linked-list descriptor fetching, byte count decrement counters, burst address incrementers, and nested edge/level interrupt priority resolvers.
* **Bug Scope**: Descriptor end-of-chain termination bug, byte count underflow, interrupt pending mask drop, burst address wrapping failure.

### Domain 5: Cryptographic & Arithmetic Engines (`v12_acc_*`, 6 cases)
* **Primary IP**: SHA-3 / Keccak Input State Padder (`sha3_keccak_padder`) and Radix-2 Non-Restoring Synchronous Integer Divider (`divider_radix2`).
* **RTL Characteristics**: Multi-rate sponge padding (1088-bit/576-bit rate switching), delimiter byte injection, iterative non-restoring quotient digit selection, and remainder sign restoration.
* **Bug Scope**: Padding byte delimiter injection slip, rate boundary truncation, division quotient sign bit inversion, remainder restoration off-by-one.

---

## 4. Case Stratification per Domain

Each of the 5 domains contains exactly 6 cases:
1. **Case 1 (Positive Canonical Opportunity)**: Evaluates whether cross-cutting hardware concepts (e.g. handshake protocol rules, counter overflow bounds, state lockups) can assist RCA.
2. **Case 2 (Positive Complex Bug)**: Internal signal bug with non-trivial causal chains.
3. **Case 3 (Positive Edge-Case)**: Boundary timing or protocol wrap condition.
4. **Case 4 (Structural Variant)**: Refactored logic structure or alternative datapath implementation.
5. **Case 5 (Adversarial Negative Control)**: Shares signal names and module ports but exhibits an unrelated root cause; System B must safely reject.
6. **Case 6 (Incomplete Evidence Trace)**: Masked counterexample or truncated trace requiring abstention / fallback.

---

## 5. Summary Table of External Corpus Selection

| Domain | Designs / Modules | Provenance | License | Total Cases | Valid Cases | Oracle Method |
|:---|:---|:---|:---:|:---:|:---:|:---|
| **Memory Controllers** | `sdram_controller`, `cache_controller_l1` | OpenCores / CirFix | MIT / BSD | 6 | 6 | `iverilog` testbench assertions |
| **Bus & Protocol** | `i2c_master_bit_ctrl`, `spi_master_fifo` | OpenCores / CirFix | LGPL / BSD | 6 | 6 | `iverilog` protocol checking |
| **Arbitration** | `arbiter_round_robin`, `arbiter_priority` | Open-source EDA IP | Apache-2.0 | 6 | 6 | `iverilog` fairness/grant assertions |
| **DMA & Control** | `dma_controller_sg`, `interrupt_controller_pic` | Open-source EDA IP | Apache-2.0 | 6 | 6 | `iverilog` transfer/interrupt assertions |
| **Crypto & Arith** | `sha3_keccak_padder`, `divider_radix2` | OpenCores / CirFix | MIT / BSD | 6 | 6 | `iverilog` golden vector matching |
| **Total** | **10 Distinct Hardware IP Cores** | — | — | **30** | **30** | **100% Machine Checked** |
