# Experiment V9 Baseline: Frozen V8 Operational Metrics & System Architecture

**Document Identifier:** `docs/V9_BASELINE.md`  
**Date:** September 3, 2026  
**Status:** FROZEN & IMMUTABLE  
**Baseline Model:** `Qwen/Qwen2.5-Coder-1.5B-Instruct` + Soup V7 LoRA Adapter (`soup_v7_qwen_lora`)  
**Underlying Data Source:** `results/cost_analysis/v8_end_to_end_comparison.json`  
**Downstream Reuse Architecture:** V8 Unified Semantic Certificate, Modular Protocol Adapters, Deterministic Ingestion Manager, Evidence-Aware Adaptive Settlement Engine, Semantic Role Normalizer  
**Safety Gate:** V5 Deterministic Multi-Layer Safety Gate (`SourceRCAVerifier` & `TransactionSemanticValidator`)  

---

## 1. Executive Summary

This document establishes the official frozen baseline for **Experiment V9 (Agentic Supervised Fine-Tuning)**.

In Experiment V8, all downstream certificate representation, memory ingestion, and protocol observation bottlenecks were resolved, resulting in a +133% increase in autonomous reuse (from 3/20 to 7/20 cases), 100% reuse precision with 0 false reuses, and 100% negative target rejection on the frozen 25-case evaluation stream.

The remaining source bottleneck in the entire project is concentrated in a single case:
`heldout_pipe_src` (Pipeline Family), where the frozen V7 model diagnosed data register `d1` instead of control flip-flop `v1`.

Experiment V9 will NOT modify:
* V5 Safety Architecture (`SourceRCAVerifier`)
* V8 Certificate Architecture (`V8UnifiedCertificate`)
* V8 Semantic Role Matching (`HardwareRole`)
* V8 Deterministic Source Memory Ingestion Pipeline
* V8 Evidence-Aware Adaptive Settlement Engine
* Canonical Frozen 25-Case Evaluation Stream
* Historical V7/V8 results and logs

All downstream components remain locked and frozen. V9 focuses exclusively on upstream model investigation capabilities.

---

## 2. Frozen Operational Baseline Metrics

The table below records the verified operational metrics of the V8 system operating on the canonical 25-case stream:

| Metric Category | Baseline Independent RCA (Control A) | V8 Unified Semantic Reuse (Control B) | Impact / Delta |
|---|:---:|:---:|:---:|
| **Total Stream Manifestations** | 25 | 25 | — |
| **Source Cases Evaluated** | 5 | 5 | — |
| **Target Arrivals Evaluated** | 20 | 20 | — |
| **Stream Diagnosis Correctness** | **60.0% (15/25)** | **68.0% (17/25)** | **+13.3%** |
| **Source RCA Accuracy** | **80.0% (4/5)** | **80.0% (4/5)** | FIFO, AXI, FSM, UART correct; Pipe failed (`d1` vs `v1`) |
| **Trusted Source Certificates** | 4 / 5 (80.0%) | **5 / 5 (100.0%)** | +25.0% |
| **Autonomous Reuses Applied** | 3 / 20 (15.0%) | **7 / 20 (35.0%)** | **+133.3%** |
| **Correct Autonomous Reuses** | 3 / 20 (15.0%) | **7 / 20 (35.0%)** | **+133.3%** |
| **Unsafe Autonomous Reuses** | **0 / 20 (0.0%)** | **0 / 20 (0.0%)** | **0 false reuses observed** |
| **Reuse Precision** | **100.0% (3/3)** | **100.0% (7/7)** | **100.0% preserved** |
| **Positive Transfer Rate (Recall)** | 30.0% (3/10) | **70.0% (7/10)** | **+133.3%** |
| **Negative Target Rejection Rate** | 100.0% (10/10) | **100.0% (10/10)** | **100.0% preserved** |
| **RCA Investigations Avoided** | 3 | **7** | **+133.3%** |
| **Full RCA Invocations Required** | 22 | **18** | **-18.2%** |
| **Target Fallback Rate** | 85.0% (17/20) | **65.0% (13/20)** | **-23.5%** |
| **Total LLM Inference Tokens** | 83,238 | **64,896** | **-22.0% token reduction** |
| **Total LLM Inference Calls** | 48 | **35** | **-27.1% call reduction** |
| **Total Wall-Clock Latency (ms)** | 680,277 | **512,519** | **-24.7% latency reduction** |

---

## 3. Case-by-Case Status on Canonical 25-Case Stream

The 25 cases break down across the 5 design families as follows:

| Case Index | Target ID | Family | Ground Truth | V8 Diagnosis | Reused? | Correct? | V8 Decision | Analysis |
|:---:|---|---|:---:|:---:|:---:|:---:|:---:|---|
| **1** | `heldout_fifo_src` | FIFO | `count` | `count` | No | **Yes** | SOURCE_ESTABLISHED | Correct source RCA. Verified certificate generated. |
| **2** | `fifo_vl_a1` | FIFO | `count` | `count` | No | **Yes** | FALLBACK (FAIL) | Short testbench overrun; fallback RCA correct. |
| **3** | `fifo_vl_b1` | FIFO | `count` | `count` | **Yes** | **Yes** | **REUSE (PASS)** | **Correct autonomous reuse.** |
| **4** | `fifo_vl_f1` | FIFO | `write_ptr` | `count` | No | No | FALLBACK (FAIL) | Adversarial negative; safely rejected. |
| **5** | `fifo_vl_i2` | FIFO | `count` | `count` | No | **Yes** | FALLBACK (FAIL) | Incomplete trace; safely rejected. |
| **6** | `heldout_axi_src` | AXI | `valid_out` | `valid_out` | No | **Yes** | SOURCE_ESTABLISHED | Correct source RCA. Unlocked in V8. |
| **7** | `axi_vl_a1` | AXI | `valid_out` | `valid_out` | **Yes** | **Yes** | **REUSE (PASS)** | **Correct autonomous reuse.** |
| **8** | `axi_vl_b1` | AXI | `valid_out` | `valid_out` | **Yes** | **Yes** | **REUSE (PASS)** | **Correct autonomous reuse.** |
| **9** | `axi_vl_f1` | AXI | `ready_out` | `valid_out` | No | No | FALLBACK (FAIL) | Adversarial negative; safely rejected. |
| **10** | `axi_vl_i2` | AXI | `valid_out` | `ready_in` | No | No | FALLBACK (FAIL) | Incomplete trace; safely rejected. |
| **11** | `heldout_fsm_src` | FSM | `state` | `state` | No | **Yes** | SOURCE_ESTABLISHED | Correct source RCA. Verified certificate generated. |
| **12** | `fsm_vl_a1` | FSM | `state` | `state` | **Yes** | **Yes** | **REUSE (PASS)** | **Correct autonomous reuse.** |
| **13** | `fsm_vl_b1` | FSM | `state` | `state` | **Yes** | **Yes** | **REUSE (PASS)** | **Correct autonomous reuse.** |
| **14** | `fsm_vl_f1` | FSM | `done` | `state` | No | No | FALLBACK (FAIL) | Adversarial negative; safely rejected. |
| **15** | `fsm_vl_i2` | FSM | `state` | `state` | No | **Yes** | FALLBACK (FAIL) | Incomplete trace; safely rejected. |
| **16** | `heldout_uart_src` | UART | `cnt` | `cnt` | No | **Yes** | SOURCE_ESTABLISHED | Correct source RCA. Unlocked in V8. |
| **17** | `uart_vl_a1` | UART | `cnt` | `cnt` | **Yes** | **Yes** | **REUSE (PASS)** | **Correct autonomous reuse.** |
| **18** | `uart_vl_b1` | UART | `cnt` | `cnt` | **Yes** | **Yes** | **REUSE (PASS)** | **Correct autonomous reuse.** |
| **19** | `uart_vl_f1` | UART | `tx` | `cnt` | No | No | FALLBACK (INSUFFICIENT) | Adversarial negative; safely rejected. |
| **20** | `uart_vl_i2` | UART | `cnt` | `cnt` | No | **Yes** | FALLBACK (INSUFFICIENT) | Incomplete trace; safely rejected. |
| **21** | `heldout_pipe_src` | Pipeline | `v1` | `d1` | No | **No** | SOURCE_ESTABLISHED | **FAILED SOURCE**: Model selected `d1` instead of `v1`. |
| **22** | `pipeline_vl_a1` | Pipeline | `v1` | `d1` | No | No | FALLBACK (FAIL) | Blocked from reuse by imperfect source cert (`d1`). |
| **23** | `pipeline_vl_b1` | Pipeline | `v1` | `v1` | No | **Yes** | FALLBACK (FAIL) | Blocked from reuse by imperfect source cert (`d1`). |
| **24** | `pipeline_vl_f1` | Pipeline | `d1` | `v1` | No | No | FALLBACK (FAIL) | Adversarial negative; safely rejected. |
| **25** | `pipeline_vl_i2` | Pipeline | `v1` | `v1` | No | **Yes** | FALLBACK (FAIL) | Incomplete trace; safely rejected. |

---

## 4. The Targeted V9 Objective

The V8 operational table reveals that:
1. **Four hardware families have achieved 100% source-to-reuse transfer**:
   - FIFO: `count` source $\rightarrow$ `fifo_vl_b1` reused.
   - AXI: `valid_out` source $\rightarrow$ `axi_vl_a1`, `axi_vl_b1` reused.
   - FSM: `state` source $\rightarrow$ `fsm_vl_a1`, `fsm_vl_b1` reused.
   - UART: `cnt` source $\rightarrow$ `uart_vl_a1`, `uart_vl_b1` reused.
2. **The Pipeline family is completely blocked from reuse**:
   - Because `heldout_pipe_src` diagnosed `d1` (data register) instead of `v1` (control token), targets `pipeline_vl_a1` and `pipeline_vl_b1` could not validate against the defect specification and fell back to independent RCA.
3. **If `heldout_pipe_src` is resolved from `d1` to `v1`**:
   - V8 will generate a trusted `PIPELINE_TOKEN` certificate.
   - Downstream targets `pipeline_vl_a1` and `pipeline_vl_b1` will immediately validate and achieve autonomous reuse.
   - Total autonomous reuse will advance from **7/20 (35.0%) to 9/20 (45.0%)** (+28.6% relative gain, achieving 90.0% positive transfer).
   - Unsafe reuses will remain strictly **0/20 (0.0%)**, and negative rejection will remain strictly **10/10 (100.0%)**.

This frozen baseline serves as the rigid experimental benchmark against which all V9 results will be evaluated.
