# Benchmark Provenance & Realism Specification

**Evaluation Focus**: Scientific Origin, Construction Methodology, and Realism Audit for Benchmarks V11 and V12  
**Target Release**: RCA-Reuse V12.1  

---

## 1. Executive Statement of Provenance

A common failure mode in AI-for-hardware evaluation is the conflation of synthetic benchmarks with authentic historical defect corpora. Scientific credibility requires absolute transparency regarding what a benchmark represents, how it was constructed, and what claims it can legitimately support.

### What These Benchmarks Are:
* **Machine-Validated Debugging Instances**: Both benchmarks consist of fully compilable, deterministically simulatable Verilog designs paired with self-checking testbenches where assertion failures detect bugs pre-repair and certify correctness post-repair in Icarus Verilog.
* **Structurally Realistic Hardware IP Patterns**: The designs model authentic Register-Transfer Level (RTL) patterns, timing contracts, and control logic derived from established open-source hardware cores and peer-reviewed repair benchmarks (OpenCores, CirFix ASPLOS '22 artifacts, open-source EDA IP).
* **Controlled Evaluation Streams**: Cases are partitioned systematically into positive reuse opportunities, structural variants, adversarial same-symptom negative controls, and incomplete trace controls.

### What These Benchmarks Are Not:
* **Untouched Historical Issue-Tracker Extractions**: These cases are **not** raw, unedited Git commits scraped directly from commercial issue trackers. While modeled after real-world defect patterns (e.g., refresh counter slip, I2C clock-stretching lockup, DMA descriptor end-of-list bugs), the bug instances and testbenches were constructed, adapted, and standardized to ensure reproducible, single-file deterministic simulation under open-source tools.
* **Proof of Universal Cross-Family Generalization**: While demonstrating transfer across distinct parameterized implementations and structurally novel IP cores, these benchmarks do not claim that a verified certificate learned on a 4-channel arbiter will automatically repair an out-of-order superscalar CPU.

---

## 2. Milestone V11: Canonical Generalization Corpus ($N=100$)

### Benchmark Construction
The V11 benchmark was constructed by `scripts/build_v11_benchmark.py` to evaluate generalization across five canonical hardware families fundamental to digital design:

1. **FIFO Buffers (`fifo`)**: Synchronous and asynchronous FIFOs, circular ring buffers, Gray code pointer synchronization, and high/low watermarks.
2. **AXI-Stream Protocols (`axi`)**: Decoupled ready/valid handshakes, multi-beat bursts, backpressure propagation, and split-transfer stages.
3. **Finite State Machines (`fsm`)**: Mealy and Moore state sequencers, one-hot encoders, hierarchical state transitions, and timeout recovery logic.
4. **UART Controllers (`uart`)**: Configurable baud rate prescalers, fractional dividers, frame synchronization, and TX/RX shift buffers.
5. **Pipelined Datapaths (`pipeline`)**: Multi-stage execution pipelines, register retiming, hazard stall logic, and elastic skid buffers.

### Corpus Stratification
The 100 cases are structured across three strictly controlled categories:
* **Category A: In-Family Variations ($40\%$ / 40 cases)**: Parameter variations (e.g., changing FIFO depth from 8 to 64, adjusting datapath width, altering prescaler divisors) testing transfer across structural variants.
* **Category B: Structural Cross-Variant Cases ($30\%$ / 30 cases)**: Reimplemented logic structures (e.g., Gray code vs. binary pointers, multi-stage vs. single-stage handshakes).
* **Category C: Negative Stress Controls ($30\%$ / 30 cases)**: 15 adversarial negative controls (identical failure symptom caused by an unrelated signal) and 15 incomplete trace controls. System B must safely reject all 30.

---

## 3. Milestone V12: External / Realistic Hardware Corpus ($N=30$)

### Benchmark Construction & Origin
The V12 benchmark was constructed by `scripts/build_v12_external_benchmark.py` to test whether verified reuse holds on **unfamiliar, realistic, and external hardware RTL** that was never designed around the initial RCA-Reuse project.

The 30 cases are partitioned symmetrically across five unfamiliar functional domains (6 cases each), derived from authentic open-source IP cores:

| Domain | Representative Upstream IP Core | Provenance Reference | Open-Source License | Bug Types Modeled |
| :--- | :--- | :--- | :---: | :--- |
| **1. Memory Controllers** | ISSI IS42S16160G-7 SDRAM Controller (`sdram_controller`), L1 Cache Controller (`cache_controller_l1`) | OpenCores / CirFix ASPLOS '22 artifact | MIT / BSD | Refresh starvation under busy cycles, cache tag hit logic corruption, bank address decoding error. |
| **2. Bus Protocols** | WISHBONE compliant I2C Master Bit Controller (`i2c_master_bit_ctrl`), SPI Master Interface (`spi_master_fifo`) | Richard Herveille / OpenCores; CirFix artifact | LGPL / BSD | SCL clock stretching lockup, start bit setup timing violation, SPI CPOL phase inversion. |
| **3. Interconnect & Arbitration** | Rotating Token Round-Robin Arbiter (`arbiter_round_robin`), 4-Channel Priority Arbiter (`arbiter_priority`) | Open-source EDA IP | Apache-2.0 | Mask generation wrap bug, starvation under burst requests, unmasked simultaneous grant glitch. |
| **4. DMA & Peripheral Control** | Scatter-Gather DMA Controller (`dma_controller_sg`), Programmable Priority Interrupt Controller (`interrupt_controller_pic`) | Open-source EDA IP | Apache-2.0 | Descriptor end-of-chain termination failure, byte count underflow, nested priority drop. |
| **5. Crypto & Arithmetic** | SHA-3 / Keccak Input State Padder (`sha3_keccak_padder`), Radix-2 Non-Restoring Divider (`divider_radix2`) | OpenCores / CirFix ASPLOS '22 artifact | MIT / BSD | Delimiter byte padding slip, rate boundary truncation, quotient sign bit inversion. |

### Domain Partitioning per Case
Each domain contains exactly 6 cases:
* **Case 1 (Positive Opportunity)**: Cross-cutting protocol rules (e.g., handshake stall, counter rollover bounds).
* **Case 2 (Positive Complex Bug)**: Internal signal defect with non-trivial causal chains.
* **Case 3 (Positive Edge Case)**: Boundary timing or protocol wrap condition.
* **Case 4 (Structural Variant)**: Refactored logic structure or alternative datapath implementation.
* **Case 5 (Adversarial Negative Control)**: Shares signal names and port signatures but exhibits an unrelated root cause; System B must safely reject.
* **Case 6 (Incomplete Evidence Trace)**: Truncated trace requiring abstention and fallback.

---

## 4. Lexical & Structural Novelty Analysis

To verify that V12 presents genuine structural divergence rather than trivial signal renaming:

```bash
python scripts/calculate_novelty_metrics.py
```

* **Historical Unique Identifiers (V7–V11)**: 187
* **V12 Unique Identifiers**: 94
* **Novel Identifiers in V12**: **80 (85.1%)**
* **Shared Primitive Identifiers**: 14 (standard Verilog primitives: `clk`, `rst_n`, `count`, `data`, `valid`, `ready`, etc.)
* **Jaccard Token Similarity**: **0.0524** (representing **94.8% lexical divergence**)

### Scientific Boundaries of Lexical Metrics
* **What Lexical Novelty Demonstrates**: It proves that V12 was not synthesized by simple lexical substitution of historical circuits. The circuits introduce novel state machines, multi-phase bus protocols, and cryptographic rate padding logic.
* **What Lexical Novelty Does Not Prove**: Lexical divergence does not mathematically prove complete topological independence. Standard digital circuits inevitably share foundational constructs (synchronous clock edges, active-low resets, and finite state machine state-variable registers).

---

## 5. Ground-Truth Machine Verification

Every bug in both benchmarks is machine-certified through physical simulation:
1. **Pre-repair check**: Running the buggy circuit against its self-checking testbench in Icarus Verilog results in an exit code $\neq 0$ or triggered assertion failure (`$fatal` / `$error`).
2. **Post-repair check**: Applying the ground-truth patch results in clean compilation (exit code 0), zero assertion triggers across all clock cycles, and the explicit emission of `"TEST PASSED"`.
3. **Certification Report**: Recorded in `results/reports/v11_benchmark_validation.json` (100/100 valid) and `results/reports/v12_external_benchmark_validation.json` (30/30 valid).
