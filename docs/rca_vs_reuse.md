# RCA vs. RCA-Reuse: Resolution, Metrics, and Cost Comparison

**Document Purpose:** Direct, technical answer to the comparative questions regarding bug resolution, token/compute costs, and validation trade-offs between independent Root-Cause Analysis (RCA) and RCA-Reuse.

---

## 1. Executive Summary

When comparing full independent RCA against the RCA-Reuse prototype:

| Dimension | Full Independent RCA | RCA-Reuse Prototype | Measurement Status |
|---|---|---|---|
| **Bug Resolution Rate** | Assumed baseline (100% of investigated cases reach independent resolution) | **Not directly measured end-to-end.** Validation decision is not equivalent to verified patch generation. | **Not measured.** |
| **Reuse Decision Precision** | N/A (Does not reuse prior analyses) | **71.4%** on frozen blind benchmark; **96.9%** on variable-latency benchmark | Measured on benchmark targets. |
| **False Reuse Rate (FRR)** | 0% (Investigates each failure independently) | **28.6%** (Phase 4.1 frozen); **3.1%** (Phase 4.3 adaptive boundary) | Measured on benchmark targets. |
| **Positive Transfer / Recall** | N/A | **33.3%** (Phase 4.1 frozen); **77.5%** (Phase 4.3 adaptive boundary) | Measured on designated positive controls. |
| **Conservative Abstention** | 0% (Always attempts full search) | **10/10** incomplete/truncated traces safely rejected to independent RCA | Measured on Class-I stress cases. |
| **Token Cost (LLM)** | Not logged across all benchmark runs | Not logged across all benchmark runs | **Not measured.** |
| **Wall-Clock Compute Time** | Not profiled on standardized cluster | Not profiled on standardized cluster | **Not measured.** |
| **Search Cost Accounting** | ~8.9 simulator/search tool calls per failure | ~2.0 calls on reuse `PASS`; ~10.9 calls on fallback (`INSUFFICIENT_EVIDENCE` / `FAIL`) | **Analytical cost model.** |
| **Search Compression Ratio (SCR)** | 1.00x baseline | **~1.24x** full-lifecycle compression across variable-latency benchmark | Derived from analytical model. |
| **Break-Even Point** | N/A | **2 total manifestations** (1 initial source RCA + 1 subsequent target reuse) | Derived from analytical model. |

---

## 2. Bug Resolution Rate vs. Reuse Precision

### Critical Clarification: Bug Resolution Was Not Directly Measured
> **An end-to-end bug resolution rate has not yet been directly measured.**

A common point of confusion is conflating **reuse validation precision** with **end-to-end bug resolution**:
- **Reuse Precision (71.4% – 96.9%):** Measures whether a target failure accepted by the validator (`pred == PASS`) was genuinely caused by the same defect mechanism as the source certificate (`ground_truth_match == MATCH`).
- **End-to-End Bug Resolution:** Would measure whether providing the reused RCA certificate to an engineer or automated repair agent successfully leads to a correct RTL fix and regression pass.

The current experiments terminate at the **validation and triage decision** (`REUSE_RCA` vs. `FALLBACK_INDEPENDENT_RCA`). They do not simulate downstream patch synthesis or manual engineering debugging time. Therefore:
- The repository does **not** claim an $X\%$ bug resolution rate.
- Reuse precision must **never** be used as a proxy for bug resolution.

---

## 3. Precision, False Reuse, and Safety Properties

RCA-Reuse is designed around a safety-first principle: **unsafe reuse is far more costly than conservative fallback**.

### Comparison Across Validator Generations

```
1. Low-Level Invariants (L0 / L1):
   - Precision: 55.6%
   - False Reuse Rate: 44.4%
   - Failure Mode: Accepts false reuses on Category D controls where signal delta is identical
     but transaction semantics differ.

2. Frozen Transaction-Semantic (L2 Static Window = 4 cycles):
   - Precision: 71.4%
   - False Reuse Rate: 28.6%
   - Positive Transfer: 33.3%
   - Failure Mode: Rejects false reuses on Category D, but rigid 4-cycle window truncates
     variable-latency bursts, causing positive recall collapse.

3. Adaptive Transaction Boundary (L2 Adaptive):
   - Precision: 96.9%
   - False Reuse Rate: 3.1%
   - Positive Transfer: 77.5%
   - Incomplete Trace Safety: 10/10 incomplete traces safely rejected as INSUFFICIENT_EVIDENCE.
```

---

## 4. Compute and Token Cost Accounting

### Status of Physical Measurements
- **LLM Token Usage:** Not measured. The benchmark validation pipeline uses deterministic Python AST and waveform checkers (`TransactionSemanticValidator`, `AdaptiveTransactionBoundaryDetector`) rather than continuous LLM generation calls.
- **Physical Wall-Clock / Energy Compute:** Not measured on standardized hardware. Individual simulation steps run locally via Icarus Verilog (`iverilog`), but wall-clock time varies by host load and is not reported as a scientific result.

### Analytical Cost Model
The reported cost and search compression figures are derived from an **analytical tool-call accounting model** calibrated on agent debugging trajectories:

1. **Independent Full RCA Baseline ($C_{\text{indep}}$):**
   - Investigating an unseen failure from scratch requires an average of **8.9 tool calls** (RTL search, iterative simulator invocations, waveform signal queries, hypothesis tests).
2. **Reuse Validation ($C_{\text{val}}$):**
   - Evaluating a target waveform against a stored certificate requires **2.0 to 2.05 tool calls** (waveform slice extraction + transaction predicate checking).
3. **Fallback Penalty ($C_{\text{fallback}}$):**
   - When evidence is insufficient or the certificate fails, the system executes validation first ($2.0$ calls) and then falls back to full RCA ($8.9$ calls), totaling **10.9 tool calls**.
4. **Certificate Extraction Overhead ($C_{\text{extract}}$):**
   - Extracting and formalizing the initial source certificate costs **0.6 tool calls** (one-time investment).

### Lifecycle Search Compression & Break-Even
- **Target-Only Search Compression:**
  $$\text{SCR}_{\text{targets}} = \frac{N \times 8.9}{\sum (\text{Reused} \times 2.05 + \text{Rejected} \times 10.95)} \approx 1.24\text{x}$$
- **Break-Even Analysis:**
  $$\text{Break-Even Target Count } (N_{\text{targets}}^*) = \frac{C_{\text{extract}}}{\text{Net Savings per Reused Target}} \approx 0.1 \text{ targets}$$
  - Reusing the certificate for **1 subsequent target failure** completely amortizes the extraction cost.
  - Expressed as total manifestations including the source failure: **2 total manifestations** (1 source RCA + 1 subsequent target reuse).

---

## 5. Summary of Claims vs. Non-Claims

### What the Evidence Supports
1. Transaction-semantic obligations prevent false reuse on adversarial controls where low-level signal matching fails.
2. Adaptive transaction boundaries dynamically isolate variable-length transactions without prior knowledge of testbench delays.
3. Incomplete and truncated waveforms are safely mapped to `INSUFFICIENT_EVIDENCE` and routed to independent RCA fallback.
4. An analytical cost model demonstrates net search compression when the false reuse rate is kept low.

### What Remains to Be Tested
1. End-to-end bug repair and resolution rate in production verification environments.
2. Multi-clock SoC-level protocols with complex interleaved transactions.
3. System-level empirical token and wall-clock profiling under real LLM-agent harnesses.
