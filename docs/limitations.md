# RCA-Reuse Limitations and Research Boundaries

The current results do not establish universal RCA reuse. They provide empirical evidence from bounded experiments on a finite set of generated RTL families, protocols, and controlled failure manifestations.

---

## 1. End-to-End Bug Resolution vs. Reuse Validation
- **Direct Resolution Unmeasured:** End-to-end bug resolution has not yet been directly compared against full RCA.
- **Scope of Validation:** The current pipeline terminates at the triage decision (`REUSE_RCA` vs. `FALLBACK_INDEPENDENT_RCA`). It evaluates whether the causal certificate matches the target trace, but does not simulate patch generation, RTL editing, or regression closure.
- **Metric Separation:** Reuse precision must not be conflated with or reported as a bug resolution rate.

## 2. Hardware Family and Benchmark Scope
- **Limited Coverage:** Current evaluation is strictly limited to five controlled RTL hardware families: FIFO, AXI, FSM, UART, and PIPELINE (controlled research fixtures).
- **Benchmark Scope:** Stimulus sequences and testbenches are controlled research fixtures designed for adversarial validation, not industrial-scale SoC regression suites.
- **Bug-Class Dependence:** Bug-class dependence has not yet been systematically characterized across complex microarchitectural bugs (e.g., speculative execution side channels, multi-master cache coherence races).

## 3. Boundary Inference and Protocol Specificity
- **Safety over Recall:** Adaptive transaction boundaries improve safety and evidence sufficiency in the current experiments (rejecting 10/10 incomplete traces and reducing false reuse to 3.1%), but do not yet demonstrate improved positive recall over fixed-window controls.
- **Heuristic Boundaries:** Boundary recovery relies on observable transitions, handshakes, and quiescence. Ambiguous handshakes, overlapping pipelined transactions, and asynchronous clock crossings can obscure transaction boundaries.
- **Extractor Mismatches:** The prototype's certificate extractor can select mismatched context templates (e.g., selecting FIFO stream context for UART dividers), leading to conservative `INSUFFICIENT_EVIDENCE` fallback.

## 4. Scalability and System Integration
- **SoC-Level Scalability Untested:** Multi-block integration, multi-clock domains, hierarchy crossing, and long-running emulation traces remain unvalidated.
- **Trace Window Size:** Evaluated traces range from 10 to 100 cycles. Industrial verification traces spanning millions of cycles will require hierarchical transaction filtering.

## 5. Token and Compute Cost Accounting
- **Analytical Model vs. Physical Measurement:** Full token/compute measurements are based on an analytical tool-call cost model calibrated on debugging trajectories, not continuous LLM token logging or physical energy/wall-clock measurement.
- **License and Infrastructure Overhead:** Simulation costs do not account for proprietary EDA simulator licenses, compilation servers, or compute cluster queuing times.

## 6. Reproducibility and Data Packaging
- **Historical Benchmark Boundary:** The complete original 50-case blind test is treated as a historical experiment rather than a freshly reproducible benchmark from a clean checkout, because raw multi-megabyte VCD waveforms and simulator binaries are intentionally gitignored, and the historical Phase 4.1 artifact contains 19 PRECHECK rows.
- **Minimal Clean Reproduction:** A clean repository clone reproduces the core code, unit tests, and the self-contained RTL smoke pipeline (`scripts/run_rtl_smoke.py`).

## 7. Prototype Boundary
- **Not a Universal Replacement:** RCA-Reuse is not a universal replacement for root-cause analysis. It is an upstream triage filter designed to bypass expensive redundant search only when strict transaction and causal obligations are met, safely falling back to full RCA whenever evidence is ambiguous.

---

## 8. Summary of Open Research Questions
1. How does RCA-Reuse perform when paired with automated LLM bug-fixing agents on real-world open-source RTL bugs (e.g., OpenTitan, RISC-V cores)?
2. Can protocol-aware boundary detectors handle multi-channel interleaved protocols (e.g., AXI4 burst transactions, PCIe, TileLink) without manual signal annotations?
3. What is the empirical token and latency speedup when integrated into interactive developer debugging loops?
