# Experiment V10 Baseline: Frozen V8 Operational Metrics & Scientific Reference State

**Document Identifier:** `docs/V10_BASELINE.md`  
**Date:** September 3, 2026  
**Status:** FROZEN & IMMUTABLE  
**Baseline Model:** `Qwen/Qwen2.5-Coder-1.5B-Instruct` + Soup V7 LoRA Adapter (`soup_v7_qwen_lora`)  
**Data Reference Source:** `results/cost_analysis/v8_end_to_end_comparison.json`  
**Downstream Reuse Stack:** V8 Unified Semantic Certificate, Modular Protocol Adapters, Deterministic Ingestion Manager, Evidence-Aware Adaptive Settlement Engine, Semantic Role Normalizer  
**Safety Invariant:** V5 Deterministic Multi-Layer Safety Gate (`SourceRCAVerifier` & `TransactionSemanticValidator`)  

---

## 1. Executive Summary

This document establishes the official frozen operational baseline for **Experiment V10 (Clean Topology-Generalized Agentic RCA Preparation and Controlled SFT Study)**.

Experiment V8 remains the frozen operational standard for the project. Experiment V9 demonstrated that Agentic SFT could flip a targeted source diagnosis (`heldout_pipe_src` from `d1` to `v1`), but an in-depth audit revealed:
1. **Catalog Leakage**: `heldout_pipe_src` RTL was byte-identical to `pipeline_a1.v`, `pipeline_a2.v`, `pipeline_a3.v` present in the training set.
2. **Generalization Failure**: 0/5 on unseen pipeline topologies (4-stage pipelines, skid buffers, aliased names).
3. **Multi-Turn Schema Fragility**: 16% invalid output rate, degrading autonomous reuses from 7/20 to 4/20 and stream accuracy from 68% to 44%.

Therefore, V9 is classified as a negative/diagnostic milestone, and V8 is re-affirmed as the immutable operational baseline.

---

## 2. Frozen V8 Operational Metrics

The table below records the verified operational metrics of the V8 system operating on the canonical frozen 25-case stream:

| Metric Category | Baseline Independent RCA (Control A) | V8 Unified Semantic Reuse (Control B) | V8 Operational Status |
|---|:---:|:---:|:---:|
| **Total Stream Cases** | 25 | 25 | Canonical 25-case frozen benchmark |
| **Source Cases Evaluated** | 5 | 5 | 1 per hardware family |
| **Target Cases Evaluated** | 20 | 20 | 10 positive + 5 adversarial + 5 truncated |
| **Overall Stream Diagnostic Accuracy** | 60.0% (15/25) | **68.0% (17/25)** | **+13.3% relative improvement** |
| **Source RCA Accuracy** | 80.0% (4/5) | **80.0% (4/5)** | FIFO, AXI, FSM, UART correct; Pipe failed (`d1` vs `v1`) |
| **Trusted Source Certificates** | 4 / 5 (80.0%) | **5 / 5 (100.0%)** | 100% trusted certificate extraction |
| **Autonomous Reuses Applied** | 3 / 20 (15.0%) | **7 / 20 (35.0%)** | **+133.3% increase in reuse applications** |
| **Correct Autonomous Reuses** | 3 / 20 (15.0%) | **7 / 20 (35.0%)** | **+133.3% increase in correct reuses** |
| **Unsafe Autonomous Reuses** | **0 / 20 (0.0%)** | **0 / 20 (0.0%)** | **0 false reuses observed on frozen benchmark** |
| **Reuse Precision** | **100.0% (3/3)** | **100.0% (7/7)** | **100.0% precision preserved** |
| **Positive Transfer Rate (Recall)** | 30.0% (3/10) | **70.0% (7/10)** | 7 of 10 positive targets successfully reused |
| **Negative Target Rejection Rate** | **100.0% (10/10)** | **100.0% (10/10)** | 100.0% rejection of non-reusable cases |
| **RCA Investigations Avoided** | 3 | **7** | 7 full agentic investigations saved |
| **Full RCA Invocations Required** | 22 | **18** | Replaced by deterministic memory reuse |
| **Target Fallback Rate** | 85.0% (17/20) | **65.0% (13/20)** | 13 fallback investigations required |
| **Total LLM Tokens Consumed** | 83,238 | **64,896** | **22.0% token reduction** |
| **Total LLM Invocations** | 48 | **35** | **27.1% call reduction** |
| **Total Wall-Clock Latency** | 680,277 ms | **512,519 ms** | **24.7% wall-clock latency reduction** |

---

## 3. Case-Level Operational State on Frozen 25-Case Stream

| Case Index | Case ID | Family | Ground Truth | V8 Diagnosis | Reused? | Correct? | V8 Decision | Operational Analysis |
|:---:|---|---|:---:|:---:|:---:|:---:|:---:|---|
| **1** | `heldout_fifo_src` | FIFO | `count` | `count` | No | **Yes** | SOURCE_ESTABLISHED | Correct source RCA. Ingested trusted certificate. |
| **2** | `fifo_vl_a1` | FIFO | `count` | `count` | No | **Yes** | FALLBACK (FAIL) | Short testbench overrun; fallback RCA correct. |
| **3** | `fifo_vl_b1` | FIFO | `count` | `count` | **Yes** | **Yes** | **REUSE (PASS)** | **Autonomous reuse successful.** |
| **4** | `fifo_vl_f1` | FIFO | `write_ptr` | `count` | No | No | FALLBACK (FAIL) | Adversarial negative; safely rejected. |
| **5** | `fifo_vl_i2` | FIFO | `count` | `count` | No | **Yes** | FALLBACK (FAIL) | Truncated trace; safely rejected. |
| **6** | `heldout_axi_src` | AXI | `valid_out` | `valid_out` | No | **Yes** | SOURCE_ESTABLISHED | Correct source RCA. Unlocked in V8. |
| **7** | `axi_vl_a1` | AXI | `valid_out` | `valid_out` | **Yes** | **Yes** | **REUSE (PASS)** | **Autonomous reuse successful.** |
| **8** | `axi_vl_b1` | AXI | `valid_out` | `valid_out` | **Yes** | **Yes** | **REUSE (PASS)** | **Autonomous reuse successful.** |
| **9** | `axi_vl_f1` | AXI | `ready_out` | `valid_out` | No | No | FALLBACK (FAIL) | Adversarial negative; safely rejected. |
| **10** | `axi_vl_i2` | AXI | `valid_out` | `ready_in` | No | No | FALLBACK (FAIL) | Truncated trace; safely rejected. |
| **11** | `heldout_fsm_src` | FSM | `state` | `state` | No | **Yes** | SOURCE_ESTABLISHED | Correct source RCA. Ingested trusted certificate. |
| **12** | `fsm_vl_a1` | FSM | `state` | `state` | **Yes** | **Yes** | **REUSE (PASS)** | **Autonomous reuse successful.** |
| **13** | `fsm_vl_b1` | FSM | `state` | `state` | **Yes** | **Yes** | **REUSE (PASS)** | **Autonomous reuse successful.** |
| **14** | `fsm_vl_f1` | FSM | `done` | `state` | No | No | FALLBACK (FAIL) | Adversarial negative; safely rejected. |
| **15** | `fsm_vl_i2` | FSM | `state` | `state` | No | **Yes** | FALLBACK (FAIL) | Truncated trace; safely rejected. |
| **16** | `heldout_uart_src` | UART | `cnt` | `cnt` | No | **Yes** | SOURCE_ESTABLISHED | Correct source RCA. Unlocked in V8. |
| **17** | `uart_vl_a1` | UART | `cnt` | `cnt` | **Yes** | **Yes** | **REUSE (PASS)** | **Autonomous reuse successful.** |
| **18** | `uart_vl_b1` | UART | `cnt` | `cnt` | **Yes** | **Yes** | **REUSE (PASS)** | **Autonomous reuse successful.** |
| **19** | `uart_vl_f1` | UART | `tx` | `cnt` | No | No | FALLBACK (INSUFFICIENT) | Adversarial negative; safely rejected. |
| **20** | `uart_vl_i2` | UART | `cnt` | `cnt` | No | **Yes** | FALLBACK (INSUFFICIENT) | Truncated trace; safely rejected. |
| **21** | `heldout_pipe_src` | Pipeline | `v1` | `d1` | No | **No** | SOURCE_ESTABLISHED | Model selected `d1` (data symptom) instead of `v1`. |
| **22** | `pipeline_vl_a1` | Pipeline | `v1` | `d1` | No | No | FALLBACK (FAIL) | Blocked from reuse by imperfect source cert (`d1`). |
| **23** | `pipeline_vl_b1` | Pipeline | `v1` | `v1` | No | **Yes** | FALLBACK (FAIL) | Blocked from reuse by imperfect source cert (`d1`). |
| **24** | `pipeline_vl_f1` | Pipeline | `d1` | `v1` | No | No | FALLBACK (FAIL) | Adversarial negative; safely rejected. |
| **25** | `pipeline_vl_i2` | Pipeline | `v1` | `v1` | No | **Yes** | FALLBACK (FAIL) | Truncated trace; safely rejected. |

---

## 4. Frozen Evaluation Directives for V10

1. **V8 Invariants are Absolute**:
   - Zero modifications to V8 certificate schemas, adapters, ingestion, settlement, or normalization rules.
   - Zero modifications to the frozen 25-case evaluation stream.
2. **Acceptance Criteria for V10**:
   - V10 is considered an improvement over V8 ONLY if:
     - It demonstrates improved diagnostic accuracy on genuinely **architecture-disjoint** validation suites.
     - It demonstrates non-zero transfer on genuinely **unseen hardware topologies** (Generalization Suite).
     - It preserves **0 false reuses observed on the frozen evaluation**.
     - It maintains **100% negative target rejection**.
     - It maintains robust schema generation (low invalid output rate).
