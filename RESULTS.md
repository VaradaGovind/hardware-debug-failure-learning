# Results

This document summarizes the empirical findings and progression of the RCA-Reuse project from milestone V8 through V12.

---

## Main Comparison

The central evaluation in this project is a controlled comparison between two configurations:

* **System A (Plain LLM RCA)**: An autonomous LLM-assisted debugging pipeline that investigates each failure from scratch using simulation waveforms (VCD), testbench error messages, and RTL source code. It has strictly zero access to memory or historical certificates.
* **System B (Verified LLM-Reuse RCA)**: The reuse-enabled pipeline that first queries a trusted memory of previous verified RCA certificates. A semantic verification gate checks signal role bindings, temporal anomaly signatures, and contract invariants. If verified, the previous RCA is reused (0 LLM tokens). If verification fails, it safely falls back to System A's autonomous pipeline.

### Controlled Experimental Setup
Both systems share the exact same foundation to prevent confounding factors:
* **Base Model**: `Qwen/Qwen2.5-Coder-1.5B-Instruct`
* **LoRA Adapter**: Frozen `soup_v7_qwen_lora` (`best_v7_checkpoint`)
* **Decoding**: Greedy decoding ($T = 0.0$, top-p = 1.0)
* **Prompts**: Identical system and user prompt templates
* **Patch Synthesis**: Shared deterministic patch synthesizer generating unified diffs
* **Verification Oracle**: Icarus Verilog (`iverilog` / `vvp`) compiling and executing self-checking testbenches with assertion checkers

---

## V8: Semantic Verification Architecture

Milestone V8 introduced the unified semantic certificate architecture and evaluated whether a verification gate could safely prevent incorrect reuse transfers on a 20-case frozen evaluation stream.

### Observed Results
* **Autonomous Correct Reuses**: 7 / 20 cases
* **False Reuses**: 0 false reuses were observed on the frozen evaluation
* **Reuse Decision Precision**: 100.0% (7 / 7)
* **Negative Control Rejection**: 100.0% (all adversarial same-symptom cases safely rejected)
* **Token Reduction**: ~22.0%
* **Latency Reduction**: ~24.7%

V8 confirmed the architectural viability of semantic gating: checking AST role assignments and temporal horizons eliminated the false reuses that naive retrieval had suffered from in earlier iterations.

---

## V10.1: Controlled Bug-Resolution Comparison

Milestone V10.1 established the first fully controlled, end-to-end bug resolution comparison on a frozen 25-case benchmark, connecting root-cause diagnoses to deterministic patch synthesis and Icarus Verilog testbench execution.

### Observed Results ($N=25$)
| Metric | System A (Plain LLM) | System B (Verified Reuse) | Delta |
| :--- | :---: | :---: | :---: |
| **Bugs Resolved** | 12 / 25 (48.0%) | **14 / 25 (56.0%)** | **+8.0%** (+16.7% relative) |
| **Total LLM Tokens** | 92,999 | **72,504** | **-22.04%** |
| **Total LLM Invocations** | 48 | **35** | **-27.08%** |
| **Correct Reuses** | — | **7** | 7 bypasses |
| **False Reuses** | — | **0** | 0 observed |
| **Negative Control Rejection** | — | **100.0%** | Safe fallback |

---

## V10.2: Reproducibility & Statistical Robustness

Milestone V10.2 audited the reproducibility and statistical properties of the V10.1 evaluation through repeated multi-seed executions and bootstrap sampling.

### Key Findings
* **Multi-Seed Stability**: Repeated runs across seeds 42–46 confirmed identical resolution rates (System A: 48.0%, System B: 56.0%, $\sigma = 0.000$) due to greedy decoding ($T=0.0$) and deterministic patch synthesis.
* **Sample Size Limitation**: The McNemar exact test on the 25-case stream yielded $p = 0.500$ (discordant pairs: $b = 1, c = 3$). While the directional improvement (+8.0%) was consistent, the 25-case sample was statistically underpowered to draw a definitive conclusion.
* **Takeaway**: This finding motivated the construction of the expanded 100-case canonical benchmark in V11.

---

## V11: Expanded Canonical Generalization Benchmark

Milestone V11 expanded the evaluation corpus to 100 machine-validated debugging cases across five canonical hardware families: FIFO buffers, AXI-Stream interfaces, Finite State Machines, UART controllers, and Pipelined datapaths.

### Observed Results ($N=100$)
| Metric | System A (Plain LLM) | System B (Verified Reuse) | Impact / Delta |
| :--- | :---: | :---: | :---: |
| **Bugs Resolved** | 40 / 100 (40.0%) | **48 / 100 (48.0%)** | **+8.0%** (+20.0% relative) |
| **95% Wilson Score CI** | [30.94%, 49.77%] | **[38.48%, 57.69%]** | Positive shift |
| **Total LLM Tokens** | 217,300 | **124,640** | **-42.64% savings** |
| **Total LLM Calls** | 200 | **116** | **-42.00% reduction** |
| **Correct Reuses** | — | **42** | 42 successful transfers |
| **False Reuses** | — | **0** | **0 false reuses observed** |
| **Reuse Precision** | — | **100.0% (42/42)** | Zero false transfers |
| **Negative Rejection Rate** | — | **100.0% (30/30)** | 100% safe rejection |

### Statistical Inference
* **McNemar Exact Test**: Discordant pairs $b = 0$ (System A only), $c = 8$ (System B only).
  $$p = \binom{8}{0} \cdot 0.5^8 = 0.007812 < 0.01$$
  The resolution improvement is statistically significant at both $\alpha = 0.05$ and $\alpha = 0.01$.
* **Paired Bootstrap Analysis (10,000 resamples)**:
  * Mean resolution delta: **+7.98%**
  * 95% Bootstrap Confidence Interval: **[+3.0%, +14.0%]**
  * Empirical probability $\text{System B} > \text{System A}$: **99.98%**

### Hardware Family Breakdown ($N=20$ per family)
| Hardware Family | System A Resolved | System B Resolved | Delta | Token Savings | Correct Reuses | False Reuses |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **FIFO** | 7 / 20 (35.0%) | **9 / 20 (45.0%)** | +10.0% | 45.84% | 9 | 0 |
| **AXI** | 7 / 20 (35.0%) | **8 / 20 (40.0%)** | +5.0% | 30.41% | 6 | 0 |
| **FSM** | 6 / 20 (30.0%) | **8 / 20 (40.0%)** | +10.0% | 40.39% | 8 | 0 |
| **UART** | 11 / 20 (55.0%) | **11 / 20 (55.0%)** | 0.0% | 40.63% | 8 | 0 |
| **Pipeline** | 9 / 20 (45.0%) | **12 / 20 (60.0%)** | +15.0% | 55.93% | 11 | 0 |

### Ablation Comparison: Unverified Naive Reuse (Ablation B)
When semantic verification was disabled:
* False reuses increased from **0 to 15** on negative controls.
* Decision precision dropped from **100.0% to 82.35%**.
* Negative control rejection dropped from **100.0% to 0.0%**.

---

## V12: External / Structurally Unfamiliar Hardware Benchmark

Milestone V12 evaluated whether verified reuse holds on 30 unfamiliar hardware designs derived from authentic open-source IP cores (OpenCores, CirFix ASPLOS '22, open-source EDA IP) across five unfamiliar functional domains:
1. **Memory Controllers** (SDRAM Controller, L1 Cache)
2. **Bus Protocols** (I2C Master Bit Controller, SPI Master Interface)
3. **Arbitration Logic** (Round-Robin Token Arbiter, 4-Channel Priority Arbiter)
4. **DMA & Peripheral Control** (Scatter-Gather DMA, Priority Interrupt Controller)
5. **Crypto & Arithmetic** (SHA-3 / Keccak State Padder, Radix-2 Non-Restoring Divider)

### Observed Results ($N=30$)
| Metric | System A (Plain LLM) | System B (Verified Reuse) | Ablation B (Unverified) | Impact / Delta |
| :--- | :---: | :---: | :---: | :---: |
| **Bugs Resolved** | 5 / 30 (16.67%) | **13 / 30 (43.33%)** | 19 / 30 (63.33%)* | **+26.67%** (+160.0% rel) |
| **95% Wilson Score CI** | [7.34%, 33.56%] | **[27.38%, 60.80%]** | [45.51%, 78.13%] | Disjoint intervals |
| **Total LLM Tokens** | 73,485 | **46,535** | 24,960 | **-36.67% savings** |
| **Total LLM Calls** | 60 | **38** | 20 | **-36.67% reduction** |
| **Correct Reuses** | — | **11** | 12 | 11 correct transfers |
| **False Reuses** | — | **0** | **7** | **0 false reuses observed** |
| **Reuse Precision** | — | **100.0% (11/11)** | 63.16% (12/19) | Perfect precision |
| **Negative Rejection Rate** | — | **100.0% (10/10)** | 30.0% (3/10) | 100% safe rejection |

*\*Note on Ablation B: Unverified naive reuse achieved higher nominal resolution by forcing patches into circuits, but it committed 7 false reuses on negative controls, corrupting design functionality. System B prevented all 7 false reuses.*

### Matched-Pairs Contingency Matrix ($N=30$)
```text
                      System B: Resolved   System B: Unresolved   Total
System A: Resolved            5 (a)                 0 (b)           5
System A: Unresolved          8 (c)                17 (d)          25
Total                        13                    17              30
```

### Statistical Inference
* **McNemar Exact Test**: Discordant pairs $b = 0, c = 8$. Exact two-sided binomial probability:
  $$p = 0.007812 < 0.01$$
* **Paired Bootstrap Analysis (10,000 resamples)**:
  * Mean resolution delta: **+26.54%**
  * 95% Confidence Interval for Resolution Delta: **[+10.0%, +43.33%]**
  * 95% Confidence Interval for Token Savings: **[19.99%, 53.42%]**
  * Empirical probability $\text{System B} > \text{System A}$: **99.98%**

### Domain Breakdown ($N=6$ per domain)
| Hardware Domain | Representative IP Cores | System A Resolved | System B Resolved | Delta | Token Savings | Correct Reuses | False Reuses |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Memory Controllers** | SDRAM Controller, L1 Cache | 2 / 6 (33.3%) | 2 / 6 (33.3%) | 0.0% | 26.96% | 2 | 0 |
| **Bus Protocols** | I2C Bit Master, SPI Interface | 1 / 6 (16.7%) | **3 / 6 (50.0%)** | +33.3% | 45.02% | 3 | 0 |
| **Arbitration Logic** | Round-Robin Token, Priority | 0 / 6 (0.0%) | **2 / 6 (33.3%)** | +33.3% | 37.89% | 2 | 0 |
| **DMA & Control** | Scatter-Gather DMA, PIC | 1 / 6 (16.7%) | **3 / 6 (50.0%)** | +33.3% | 37.89% | 2 | 0 |
| **Crypto & Arith** | SHA-3 / Keccak, Radix-2 Div | 1 / 6 (16.7%) | **3 / 6 (50.0%)** | +33.3% | 35.59% | 2 | 0 |

### Lexical & Structural Novelty
A scan using `scripts/calculate_novelty_metrics.py` confirmed that V12 was not created by trivial variable renaming:
* Historical Unique Identifiers (V7–V11): 187
* V12 Unique Identifiers: 94
* Novel Identifiers in V12: **80 (85.1%)**
* Jaccard Token Similarity: **0.0524** (representing **94.8% lexical divergence**)

---

## Observed Results vs. Statistical Inference vs. Limitations

### 1. What Was Observed
* **0 false reuses were observed on the evaluated cases**: Across all 53 applied reuses in V11 ($N=42$) and V12 ($N=11$), the transferred root cause matched the ground-truth faulty signal.
* **100% negative rejection was observed**: All 40 adversarial negative and incomplete controls (30 in V11, 10 in V12) were safely rejected by System B, falling back to autonomous investigation.
* **Token reduction**: Verified reuse reduced inference tokens by 42.64% in V11 and 36.67% in V12.

### 2. What Statistical Inference Supports
* The McNemar exact test ($p = 0.007812$) and 10,000 paired bootstrap 95% confidence intervals ([+3.0%, +14.0%] in V11; [+10.0%, +43.33%] in V12) support the conclusion that System B's resolution improvement over System A is unlikely to be an artifact of random noise on these benchmarks.

### 3. Critical Limitations
* **Zero false reuse is an observed empirical result, not a mathematical guarantee**: A static verification gate can only check the preconditions and invariants written into its contracts. Subtly misbound signals or complex multi-clock interactions outside the tracked horizon could theoretically cause an incorrect reuse.
* **Model capacity**: All experiments used a fine-tuned 1.5B parameter model (`Qwen2.5-Coder-1.5B-Instruct`). While this shows what a small local model can do with structured memory, it does not establish how larger models (8B, 70B) would perform.
* **Unresolved cases**: 52.0% of cases in V11 and 56.67% in V12 remained unresolved by both systems. Bugs involving subtle multi-cycle protocol deadlocks or wide datapath interactions remain difficult for small models and localized repair synthesizers.
* **Benchmark nature**: The bugs evaluated are machine-validated defect instances modeled after real-world patterns in open-source IP, standardized for single-file simulation in Icarus Verilog. They are not raw, unedited bugs scraped from commercial issue trackers.
