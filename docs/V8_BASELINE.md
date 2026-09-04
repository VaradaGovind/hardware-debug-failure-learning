# V8 Baseline: Frozen V7 Metrics & System State

**Experiment:** V8 — Unified Semantic Certificate Architecture & Robust Memory Ingestion  
**Status:** FROZEN & IMMUTABLE  
**Baseline Model:** Qwen2.5-Coder-1.5B-Instruct + Soup V7 LoRA Adapter (`soup_v7_qwen_lora`)  
**Safety Baseline:** V5 Deterministic Trust Gate (`SourceRCAVerifier`)  

---

## 1. Executive Summary

This document establishes the official frozen baseline for Experiment **V8**. 

All V7 model weights, LoRA adapters, evaluation datasets, and existing V5/V7 evaluation artifacts remain strictly immutable. Experiment V8 will modify only the downstream certificate representation, protocol modularity, memory ingestion robustness, and adaptive observation settlement.

---

## 2. Frozen Baseline Metrics (V7 + V5 Safety Architecture)

The following metrics represent the exact operational performance of the V7 model coupled with the V5 safety architecture prior to the introduction of the V8 unified semantic certificate:

| Operational Metric Category | Measured Baseline Value | Context / Data Source |
|---|:---:|---|
| **Validation Diagnostic Accuracy** | **76.6% (180/235)** | Canonical 235-case split (`rca_val_v7.json`) |
| **Grounded Diagnostic Rate** | **76.2% (179/235)** | Canonical 235-case split |
| **Wrong-Signal Hallucination Rate** | **23.0% (54/235)** | Canonical 235-case split |
| **Hard-Negative Accuracy** | **72.7% (48/66)** | Canonical 235-case split |
| **Agentic RCA Accuracy (25-Case Stream)** | **60.0% (15/25)** | Frozen benchmark (`v7_end_to_end_comparison.json`) |
| **Source RCA Accuracy (Baseline)** | **60.0% (3/5)** | Frozen benchmark (`heldout_fifo_src`, `heldout_axi_src`, `heldout_uart_src`) |
| **Source RCA Accuracy (Reuse Branch)** | **60.0% (3/5)** | Frozen benchmark (`heldout_fifo_src`, `heldout_fsm_src`, `heldout_uart_src`) |
| **Trusted Source Certificates** | **4 / 5 (80.0%)** | FIFO, FSM, UART, Pipeline |
| **Autonomous Reuses Applied** | **3 / 20 (15.0%)** | `fifo_vl_b1`, `fsm_vl_a1`, `fsm_vl_b1` |
| **Correct Autonomous Reuses** | **3 / 20 (15.0%)** | 100% precision on applied reuses |
| **Unsafe Autonomous Reuses** | **0 / 20 (0.0%)** | **0 false reuses observed** on frozen benchmark |
| **Reuse Precision** | **100.0%** | Zero false positive transfer |
| **Negative Rejection Rate** | **100.0% (10/10)** | All 5 adversarial negatives + 5 incomplete traces rejected |
| **RCA Investigations Avoided** | **3** | Replaced by autonomous certificate reuse |
| **Full RCA Investigations Required** | **22** | 5 sources + 17 fallback targets |
| **Fallback Rate** | **85.0% (17/20)** | Target arrivals requiring independent fallback RCA |
| **LLM Token Reduction via Reuse** | **19.6%** | 83,238 (Baseline) vs 66,921 (Reuse Pipeline) |
| **LLM Call Reduction via Reuse** | **14.6%** | 48 (Baseline) vs 41 (Reuse Pipeline) |
| **Wall-Clock Latency Reduction** | **11.3%** | 680,277 ms (Baseline) vs 603,707 ms (Reuse Pipeline) |

---

## 3. Targeted Failure Modes to Resolve in V8

The V7.1 investigation demonstrated that the reuse bottleneck is concentrated in downstream serialization, schema, and observation mechanisms. V8 targets the following specific failure mechanisms:

1. **Stochastic Source Ingestion Glitch (AXI)**:
   * *Baseline Failure:* `heldout_axi_src` diagnosed `valid_out` correctly in baseline, but suffered `INVALID_OUTPUT` on a second pass, causing verifier rejection and losing 2 valid reuses (`axi_vl_a1`, `axi_vl_b1`).
   * *V8 Target:* Deterministic source memory ingestion with explicit failure status handling.

2. **UART Extractor Fallthrough Bug**:
   * *Baseline Failure:* `heldout_uart_src` produced a trusted certificate for prescaler `cnt`, but `TransactionCertificateExtractor` defaulted UART to `FIFO_STREAM`, causing context rejection on all UART targets.
   * *V8 Target:* Native `UartProtocolAdapter` modeling baud dividers and framing contracts.

3. **Literal Signal Name Brittleness**:
   * *Baseline Failure:* Certificates bind directly to literal strings (`count`, `valid_out`), failing on equivalent signals (`fifo_count`, `tx_valid`).
   * *V8 Target:* Semantic role normalization (`HardwareRole`).

4. **Variable-Latency Truncation**:
   * *Baseline Failure:* `fifo_vl_a1` failed validation because the fixed observation window closed before downstream read settlement finished.
   * *V8 Target:* Evidence-aware adaptive settlement with explicit budget termination.

5. **Safety Preservation**:
   * *Requirement:* All 10 non-reusable negative targets must remain 100% rejected, maintaining 0 false reuses.
