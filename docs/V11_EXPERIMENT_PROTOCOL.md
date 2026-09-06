# V11 Experiment Protocol (Pre-Registration)

**Registration Date**: September 6, 2026  
**Experiment Identifier**: `V11_BENCHMARK_EXPANSION_AND_GENERALIZATION`  
**Protocol Status**: **PRE-REGISTERED (LOCKED PRIOR TO EXECUTION)**  
**Target Sample Size**: $N = 100$ independent hardware debugging cases  

---

## 1. Research Question & Objective

Does verified LLM-RCA reuse continue to provide bug-resolution and LLM-efficiency benefits on a substantially larger ($N=100$) and genuinely independent benchmark across multiple hardware families and structural variations?

---

## 2. Pre-Registered Hypotheses

* **Primary Hypothesis ($H_1$)**:
  $$\text{Resolution Rate}(B) \ge \text{Resolution Rate}(A) \quad \text{AND} \quad \frac{\text{Tokens}(A) - \text{Tokens}(B)}{\text{Tokens}(A)} \ge 0.20$$
  Verified RCA reuse will maintain or improve end-to-end hardware bug resolution while reducing LLM token consumption by at least 20% compared to plain LLM RCA.

* **Safety Invariant Hypothesis ($H_2$)**:
  $$\text{False Reuses}(B) = 0 \quad \text{AND} \quad \text{Negative Rejection Rate}(B) = 1.00$$
  System B's multi-stage semantic verification gate will safely reject 100% of negative controls (adversarial and incomplete-trace cases), yielding zero false reuses and 100% precision.

* **Statistical Power Hypothesis ($H_3$)**:
  With an expanded sample size of $N=100$, paired statistical analysis will achieve sufficient statistical resolution to test whether observed resolution gains are statistically distinguishable from chance at $\alpha = 0.05$.

---

## 3. Metrics Pre-Specification

### Primary Metrics
1. **Bug Resolution Rate ($R$)**: Proportion of cases where the synthesized patch compiles cleanly and passes all formal Verilog assertions under Icarus Verilog (`iverilog` + `vvp`).
   - Formula: $R_A = \frac{\text{Resolved}_A}{N}, \quad R_B = \frac{\text{Resolved}_B}{N}$.
2. **LLM Token Consumption**: Total prompt and generation tokens charged across the benchmark.
   - Requirement: Accepted reuses MUST record strictly 0 LLM tokens.
3. **LLM Inference Call Count**: Total multi-turn tool interaction calls made to the model.
   - Requirement: Accepted reuses MUST record strictly 0 LLM calls.

### Secondary Metrics
1. **RCA Diagnostic Accuracy**: Correct localization of the defective net/register.
2. **Correct Reuse Count**: Number of positive targets correctly diagnosed via verified reuse.
3. **False Reuse Count**: Reuses accepted on invalid or adversarial targets.
4. **Reuse Precision**: $\frac{\text{Correct Reuses}}{\text{Reuses Applied}}$ (Target: $100.0\%$).
5. **Negative Rejection Rate**: $\frac{\text{Safe Rejections}}{\text{Total Negative Targets}}$ (Target: $100.0\%$).
6. **Investigation Avoidance Rate**: $\frac{\text{Avoided Investigations}}{N}$.
7. **Wall-Clock Latency**: Total end-to-end wall-clock time partitioned into LLM inference, semantic verification, patch synthesis, and simulation.

---

## 4. Pre-Registered Statistical Methods

All primary statistical tests are pre-defined as follows:

1. **Paired Contingency Transition Analysis ($2 \times 2$)**:
   Construct the transition table:
   - $a = \text{both resolved}$
   - $b = \text{System A only}$
   - $c = \text{System B only}$
   - $d = \text{neither resolved}$

2. **McNemar's Exact Test**:
   - Tests $H_0: p_b = p_c$.
   - Test statistic: Exact two-sided binomial test on discordant pairs ($n_{\text{disc}} = b + c$) under $p=0.5$:
     $$p = 2 \times \sum_{k=0}^{\min(b, c)} \binom{b+c}{k} (0.5)^{b+c}$$
   - Pre-specified significance threshold: $\alpha = 0.05$.

3. **Paired Bootstrap Resampling**:
   - Exactly 10,000 resamples with replacement of the $N=100$ paired cases.
   - Metrics computed per resample: $\Delta = R_B - R_A$, token savings percentage.
   - Report: Mean delta, median delta, 95% percentile confidence interval $[P_{2.5}, P_{97.5}]$, $P(B > A)$, and $P(B \ge A)$.

4. **Wilson Score Confidence Intervals**:
   - 95% Wilson score confidence intervals computed for $R_A$, $R_B$, reuse precision, and negative rejection rate.

5. **Effect Size Reporting**:
   - Absolute Risk Difference ($R_B - R_A$).
   - Relative Improvement ($\frac{R_B - R_A}{R_A} \times 100\%$).
   - Token Reduction Percentage ($\frac{\text{Tokens}_A - \text{Tokens}_B}{\text{Tokens}_A} \times 100\%$).

---

## 5. Subgroup & Generalization Strata

Results will be disaggregated along two pre-registered axes:
1. **By Hardware Family**: FIFO, AXI, FSM, UART, Pipeline (20 cases each).
2. **By Benchmark Category**:
   - Category A: In-Family Generalization (40 cases).
   - Category B: Structural Generalization (30 cases).
   - Category C: Negative and Safety Stress Tests (30 cases).

Any analysis not specified above will be explicitly flagged as **Exploratory Post-Hoc Analysis**.
