# Experiment V10.2: Scientific Robustness, Reproducibility & Statistical Validation

**Evaluation Date**: September 6, 2026  
**Experiment Identifier**: `V10.2_ROBUSTNESS_AND_STATISTICAL_VALIDATION`  
**Base Model**: `Qwen/Qwen2.5-Coder-1.5B-Instruct`  
**LoRA Checkpoint**: `soup_v7_qwen_lora` (`best_v7_checkpoint`)  
**Evaluation Scope**: 5 Independent Repeated Runs, Paired Transitions, McNemar's Exact Test, 10,000-Resample Paired Bootstrap, 95% Wilson Score Intervals, Latency Profiling  

---

## 1. Research Question

> *Can the V10.1 observed improvement in bug resolution (+8.0% absolute) and reduction in LLM workload (-22.04% tokens) be independently reproduced across repeated evaluation passes, and is the improvement statistically defensible given the 25-case benchmark size?*

---

## 2. Experimental Design

Experiment V10.2 evaluates the reproducibility and statistical stability of the V10.1 findings using a **paired experimental design**:
* **Exact Benchmark Corpus**: The canonical 25-case stream ([`results/reports/v10_1_experiment_manifest.json`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/reports/v10_1_experiment_manifest.json)), comprising 5 digital design families (FIFO, AXI, FSM, UART, Pipeline).
* **Paired Evaluation**: For every individual bug arrival, both **System A (Plain LLM RCA - Zero Reuse)** and **System B (Verified LLM-Reuse RCA)** evaluate the identical buggy RTL, testbench failure snippet, and counterexample signal trace.
* **Exact Model & Prompts**: Both systems use the local 1.5B parameter model with deterministic greedy decoding ($T=0.0$).
* **Exact Simulation Oracle**: Both systems validate repair candidates against formal Verilog hardware assertions compiled and executed via Icarus Verilog (`iverilog` + `vvp`).
* **5 Repeated Independent Passes**: Executed across distinct seeds `[42, 43, 44, 45, 46]` to measure run-to-run variance, determinism, and case-level stability.

---

## 3. Reproducibility Results

Across all 5 independent evaluation passes, System A and System B exhibited complete run-to-run consistency.

| Run # | Seed | System A Resolved | System A Res Rate | System B Resolved | System B Res Rate | System A Tokens | System B Tokens | Token Savings (%) | False Reuses |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | 42 | 12 / 25 | 48.0% | 14 / 25 | 56.0% | 83,238 | 64,896 | 22.04% | 0 |
| **2** | 43 | 12 / 25 | 48.0% | 14 / 25 | 56.0% | 83,238 | 64,896 | 22.04% | 0 |
| **3** | 44 | 12 / 25 | 48.0% | 14 / 25 | 56.0% | 83,238 | 64,896 | 22.04% | 0 |
| **4** | 45 | 12 / 25 | 48.0% | 14 / 25 | 56.0% | 83,238 | 64,896 | 22.04% | 0 |
| **5** | 46 | 12 / 25 | 48.0% | 14 / 25 | 56.0% | 83,238 | 64,896 | 22.04% | 0 |
| **Mean** | — | **12.0 / 25** | **48.0%** | **14.0 / 25** | **56.0%** | **83,238.0** | **64,896.0** | **22.04%** | **0** |
| **Std** | — | 0.0 | 0.0% | 0.0 | 0.0% | 0.0 | 0.0 | 0.0% | 0.0 |

---

## 4. Determinism Audit

* **Classification**: **Category A — Fully Deterministic**
* **Case-Level Disagreement Rate**: 0.0% (0 disagreements across 5 runs $\times$ 25 cases = 125 case comparisons per system).
* **Resolution Variance**: $\sigma^2 = 0.0$ for both System A and System B.
* **Token & Call Accounting Variance**: $\sigma^2 = 0.0$.
* **Audit Conclusion**: Because greedy decoding ($T=0.0$) and machine-checked Icarus Verilog assertion testbenches were employed, the entire end-to-end evaluation pipeline is bitwise reproducible and behaviorally deterministic.

---

## 5. Bug Resolution Analysis

### A. Paired Contingency Transition Matrix
Each of the 25 cases was evaluated by both systems. The resulting $2 \times 2$ contingency matrix is:

```
                          System B (Verified Reuse)
                          Resolved          Failed
System A        Resolved    a = 12           b = 0
(Plain LLM)     Failed      c = 2            d = 11
```

* **Concordant Pairs ($a + d = 23$ cases, 92.0%)**:
  * $a = 12$ cases resolved by both systems.
  * $d = 11$ cases failed by both systems.
* **Discordant Pairs ($b + c = 2$ cases, 8.0%)**:
  * $b = 0$ cases: Cases where System A resolved but System B failed (System A never outperformed System B).
  * $c = 2$ cases: Cases where System A failed but System B resolved (`target_pos2_fsm` and `target_pos2_uart`).

### B. McNemar's Exact Test
* **Null Hypothesis ($H_0$)**: Marginal resolution probabilities are equal ($p_b = p_c$).
* **Discordant Sample Size**: $n_{\text{disc}} = b + c = 2$.
* **Exact Two-Sided Binomial $p$-value**:
  $$p = 2 \times \sum_{k=0}^{\min(0, 2)} \binom{2}{k} (0.5)^2 = 2 \times (0.25) = \mathbf{0.5000}$$
* **Scientific Interpretation**: At $\alpha = 0.05$, $p = 0.5000 > 0.05$. The observed difference is **NOT statistically significant**. Because only 2 cases were discordant out of 25, the sample size is underpowered to reject $H_0$ despite System B winning both discordant cases ($2 \text{ vs } 0$).

### C. Paired Bootstrap Analysis (10,000 Resamples)
Sampling the 25 paired case outcomes with replacement across 10,000 iterations yielded:
* **Mean Delta Resolution ($\Delta = R_B - R_A$)**: **+7.96%** (+0.0796)
* **Median Delta Resolution**: **+8.00%** (+0.0800)
* **Standard Error of Delta**: $5.41\%$
* **95% Bootstrap Percentile Confidence Interval**: **$[0.00\%, +20.00\%]$**
* **$P(\text{System B} > \text{System A})$**: **87.47%**
* **$P(\text{System B} \ge \text{System A})$**: **100.00%** (0% of bootstrap samples favored System A)

### D. 95% Wilson Score Confidence Intervals
Computing Wilson score intervals for binomial proportions ($n=25$):
* **System A Resolution Rate**: $\hat{p} = 0.4800$ (12/25) $\implies$ **95% Wilson CI: $[30.03\%, 66.50\%]$**
* **System B Resolution Rate**: $\hat{p} = 0.5600$ (14/25) $\implies$ **95% Wilson CI: $[37.07\%, 73.33\%]$**

> **Statistical Note**: The 95% Wilson confidence intervals substantially overlap ($[30.0\%, 66.5\%]$ vs. $[37.1\%, 73.3\%]$). This confirms that claiming statistically significant superiority from the 25-case sample alone would be scientifically invalid.

---

## 6. Token Efficiency Analysis

| Metric | Repeated Run Value | Bootstrap 95% Confidence Interval |
|:---|:---:|:---:|
| **System A Mean Tokens** | 83,238 tokens | [72,150, 94,620] |
| **System B Mean Tokens** | 64,896 tokens | [53,880, 76,210] |
| **Total Token Savings** | **18,342 tokens** | [6,500, 31,400] |
| **Percentage Reduction** | **22.04%** | **[8.47%, 39.27%]** |

### Per-Case Token Classification (25 Cases)
1. **Zero-Token Reuses (7 cases, 28.0%)**: `fifo_vl_a1`, `axi_vl_a1`, `axi_vl_b1`, `fsm_vl_a1`, `fsm_vl_b1`, `uart_vl_a1`, `uart_vl_b1`. All 7 passed verification, charged 0 LLM prompt tokens, and charged 0 completion tokens.
2. **Rejected Reuse & Full Fallback (13 cases, 52.0%)**: All 10 negative controls plus 3 missed positive opportunities. These cases fell back to the System A LLM pipeline and consumed normal tokens.
3. **Source Reference Ingestions (5 cases, 20.0%)**: Established source baselines, consuming identical tokens in both systems.
4. **Token Overhead Cases (0 cases, 0.0%)**: No case incurred redundant tokens beyond standard fallback.

---

## 7. LLM Call Efficiency Analysis

* **System A Calls**: 48 calls (mean: 1.92 calls/case)
* **System B Calls**: 35 calls (mean: 1.40 calls/case)
* **Calls Saved**: **13 calls** (**27.08% reduction**)
* **Source of Savings**: The 13 saved calls derive entirely from the 7 verified reuse cases bypassing multi-turn agentic diagnostic reasoning loops (averaging ~1.86 calls per investigation avoided). Fallback cases executed the exact same number of turns as System A.

---

## 8. Safety & Negative Control Reproducibility

System B evaluated 10 negative control targets across all 5 runs:
* **5 Adversarial Negatives**: `fifo_vl_f1`, `axi_vl_f1`, `fsm_vl_f1`, `uart_vl_f1`, `pipeline_vl_f1`.
* **5 Incomplete-Trace Negatives**: `fifo_vl_i2`, `axi_vl_i2`, `fsm_vl_i2`, `uart_vl_i2`, `pipeline_vl_i2`.

### Negative Control Results

| Run # | Adversarial Negatives Evaluated | Safe Rejections | Incomplete Traces Evaluated | Safe Rejections | False Reuses Accepted | Negative Rejection Rate |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 5 | 5 | 5 | 5 | **0** | **100.0%** |
| 2 | 5 | 5 | 5 | 5 | **0** | **100.0%** |
| 3 | 5 | 5 | 5 | 5 | **0** | **100.0%** |
| 4 | 5 | 5 | 5 | 5 | **0** | **100.0%** |
| 5 | 5 | 5 | 5 | 5 | **0** | **100.0%** |

* **Zero False Reuse Invariant**: Across all 5 runs $\times$ 10 negative controls = 50 negative exposures, **0 false reuses were accepted**. The semantic verification gate safely rejected 100% of negative targets.

---

## 9. Latency and Computational Overhead

A critical question is whether token savings translate to wall-clock latency reduction or whether verification overhead dominates.

| Subsystem Component | System A Latency (ms) | System B Latency (ms) | Delta (ms) | Notes |
|:---|:---:|:---:|:---:|:---|
| **LLM Inference Time** | 680,277.0 ms | 512,512.5 ms | -167,764.5 ms | -24.7% wall-clock GPU inference time saved |
| **Memory Lookup & Retrieval** | 0.0 ms | 48.2 ms | +48.2 ms | Lightweight dictionary lookup |
| **Semantic Verification Gate** | 0.0 ms | 312.5 ms | +312.5 ms | AST & waveform invariant checks (~15.6 ms/target) |
| **Deterministic Patch Synthesis** | 16.5 ms | 16.8 ms | +0.3 ms | String replacement & regex synthesis |
| **Icarus Verilog Simulation** | 1,258.0 ms | 1,326.6 ms | +68.6 ms | Process compilation and VVP execution |
| **Total Wall-Clock Time** | **681,551.5 ms** | **514,216.6 ms** | **-167,334.9 ms** | **Net 24.5% wall-clock speedup** |

> **Finding**: Because local 1.5B LLM generation on GPU/CPU is orders of magnitude slower (~10–30 seconds per multi-turn call) than deterministic semantic verification (~15 ms per check), bypassing 7 full LLM investigations provided a **net wall-clock reduction of ~167 seconds (~24.5%)**. Verification overhead is negligible ($<0.1\%$ of total runtime).

---

## 10. Case-Level Analysis: Special Focus on Discordant Cases

### Case 1: `target_pos2_fsm` (`heldout_fsm_src` / `fsm_vl_b1`)
* **Symptom**: Sequence detector FSM locks in state `S2` instead of advancing to `S3` on active input.
* **System A Failure**: The 1.5B LLM repeatedly hallucinated that the defect was in the asynchronous reset sensitivity list (`always @(posedge clk or posedge rst_n)`). It generated a redundant reset patch, leaving the state machine transition table defective. In simulation, assertion `assert (state == S3)` failed.
* **System B Success**: Queried trusted memory, matched the structural AST of the 4-state sequencer, verified signal trace alignment, and reused the transition diagnosis. Patch synthesis corrected the state assignment, passing all simulation assertions.
* **Stability**: System B resolved this case in 5 out of 5 runs; System A failed it in 5 out of 5 runs.

### Case 2: `target_pos2_uart` (`uart_vl_a1`)
* **Symptom**: UART TX baud divider drift causes receiver framing error on stop bit.
* **System A Failure**: The 1.5B LLM diagnosed the parity generator instead of the baud counter accumulator. The synthesized parity patch did not resolve the baud timing error.
* **System B Success**: Reused the verified baud counter rollover diagnosis from `source_uart`, adjusting the accumulator reset threshold. Simulation confirmed error-free transmission.
* **Stability**: System B resolved this case in 5 out of 5 runs; System A failed it in 5 out of 5 runs.

---

## 11. Threats to Validity

1. **Small Sample Size ($n=25$)**: The primary limitation of this study. While 25 deep hardware debugging cases provide rich diagnostic logs and full waveform traces, the small sample size yields high confidence interval widths ($\pm 18\%$) and prevents McNemar's test from reaching statistical significance ($p=0.50$).
2. **Hardware Family Clustering**: The benchmark spans 5 hardware families (5 cases per family). Defects within the same family share structural characteristics, meaning cases cannot be treated as completely independent and identically distributed (i.i.d.) random variables.
3. **Source/Target Construction Bias**: Target cases were engineered with realistic variations (signal renaming, extra pipeline stages, altered clock dividers). While representative of IP reuse in ASIC design, synthetic variations may present higher structural similarity than arbitrary open-source repositories.
4. **Deterministic Patch Synthesis Decoupling**: Bug resolution relies on deterministic patch synthesis. The +8.0% improvement reflects better root-cause signal localization fed into the synthesizer, not an improvement in LLM code generation capability.
5. **Statistical Power**: To achieve 80% statistical power ($\beta = 0.20$) at $\alpha = 0.05$ to detect an 8 percentage point difference ($48\% \to 56\%$) with discordant proportions $p_b = 0.00, p_c = 0.08$, a sample size of at least **$n \ge 185$ cases** would be required.

---

## 12. Scientific Interpretation

We explicitly separate **observed empirical outcomes** from **statistical confidence**:

* **Observed Results**:
  * System B resolved 14 bugs compared to System A's 12 bugs (+8.0% absolute, +16.7% relative).
  * System B reduced LLM token workload by 22.04% and inference calls by 27.08%.
  * System B achieved 100% precision with 0 false reuses across 50 negative control exposures.
  * All outcomes were 100% reproducible across 5 independent runs.
* **Statistical Evidence**:
  * McNemar's exact test yields $p = 0.5000$, which fails to reach statistical significance at $\alpha = 0.05$.
  * The 95% Wilson confidence intervals overlap substantially ($[30.0\%, 66.5\%]$ vs. $[37.1\%, 73.3\%]$).
  * The 10,000-resample bootstrap indicates an 87.5% posterior probability that System B is superior, with a 95% CI of $[0.0\%, 20.0\%]$.
* **Scientific Standard**:
  * We **do not claim** that verified reuse has been conclusively proven to improve bug resolution for all hardware designs.
  * We **do claim** that on this controlled benchmark, verified reuse consistently reduced LLM workload by >22% without a single false reuse, and demonstrated observable resolution superiority on two specific multi-cycle state/timing bugs where the small 1.5B LLM hallucinated.

---

## 13. Recommendation

**Selected Verdict**: **Option B**
> **"V10.1 result is reproducible but benchmark size prevents strong statistical conclusions."**

The V10.1 experiment is bitwise reproducible, deterministic, and safe. However, claims of generalizable statistical superiority must await evaluation on an expanded benchmark of $\ge 200$ hardware failure cases.
