# Final Master Evolution Comparison: V4 through V8

**Audit Date:** September 3, 2026  
**Auditor:** Google DeepMind Advanced Agentic Coding Pair  
**Scope:** Architectural and empirical progression across V4, V5, V6, V7, V7.1, and V8.  
**Strict Reporting Rule:** Metrics are strictly partitioned between **Validation Split Evaluation** and the **Frozen 25-Case Agentic Stream** to prevent evaluation set contamination.  

---

## 1. Executive Summary

The RCA-Reuse project evolved through three distinct evolutionary phases:
1. **Safety Foundation (V4 $\rightarrow$ V5)**: Introducing deterministic verification gates (`SourceRCAVerifier`) that eliminated certificate poisoning and reduced unsafe reuses from 60% to 0%.
2. **Model Diagnostic Leap (V5 $\rightarrow$ V6 $\rightarrow$ V7)**: Advancing from un-tuned local proxies (32% benchmark accuracy) to contrastive, quality-hardened LoRA fine-tuning (76.6% validation accuracy, 60% frozen benchmark accuracy).
3. **Systems & Knowledge Architecture (V7 $\rightarrow$ V7.1 $\rightarrow$ V8)**: Diagnosing that downstream schema and ingestion bottlenecks limited reuse, then implementing unified semantic certificates, modular protocol adapters, and deterministic ingestion to jump valid reuse from 3 to 7 cases (+133%).

---

## 2. Model Diagnostic Quality Evolution (Standalone RCA, No Reuse)

*Evaluated on independent validation splits and the standalone baseline pass of the frozen 25-case stream:*

| Milestone | Base Model & Training Paradigm | Validation Dataset Size | Validation Diagnostic Accuracy | Validation Grounded Rate | Wrong-Signal Hallucination Rate | Hard-Negative Discrimination | Agentic 25-Case Baseline Accuracy | Source Case Diagnosis (Out of 5) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **V4** | Qwen2.5-Coder-1.5B (Zero-Shot Agentic) | — | — | — | >65% | <35% | 20.0% (5/25) | 1 / 5 (20.0%) |
| **V5** | Qwen2.5-Coder-1.5B + Safety Verifier | — | — | — | >60% | ~40% | 28.0% (7/25) | 2 / 5 (40.0%) |
| **V6** | Soup V6 LoRA (330 Canonical Examples) | 66 cases | 41.7% (25/66) | 37.9% | 58.3% | 46.3% | 32.0% (8/25) | 2 / 5 (40.0%) |
| **V7** | Soup V7 LoRA (1,170 Quality-Hardened Examples) | 235 cases | **76.6% (180/235)** | **76.2%** | **23.0%** | **72.7%** | **60.0% (15/25)** | **3 / 5 (60.0%)** |
| **V7.1**| Soup V7 LoRA (Frozen Model Audit) | 235 cases | 76.6% | 76.2% | 23.0% | 72.7% | 60.0% (15/25) | 3 / 5 (60.0%) |
| **V8** | Soup V7 LoRA (Frozen Model Architecture) | 235 cases | 76.6% | 76.2% | 23.0% | 72.7% | 60.0% (15/25) | **4 / 5 (80.0%)**\* |

*\*Note: In V8, source memory ingestion deterministically preserved the valid baseline diagnosis for AXI, unlocking 4/5 verified source cases.*

---

## 3. Autonomous Reuse Quality Evolution (Frozen 25-Case Stream)

*Evaluated across the 20 target arrivals following the 5 source manifestations:*

| Milestone | Trusted Source Certs | Reuses Applied | Successful Reuses | Unsafe Reuses | Reuse Precision | Positive Transfer Rate | Negative Rejection Rate | RCA Invocations Avoided | Full RCA Fallbacks Required |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **V4 (Unprotected)** | 5 / 5 | 10 / 20 | 4 / 20 | 6 / 20 | 40.0% | 40.0% | 40.0% | 10 | 15 |
| **V5 (Safety Gate)** | 2 / 5 | 2 / 20 | 2 / 20 | **0 / 20** | **100.0%** | 20.0% | **100.0%** | 2 | 23 |
| **V6 (First SFT)** | 4 / 5 | 4 / 20 | 4 / 20 | **0 / 20** | **100.0%** | 40.0% | **100.0%** | 4 | 21 |
| **V7 (Better Model)** | 4 / 5 | 3 / 20 | 3 / 20 | **0 / 20** | **100.0%** | 30.0% | **100.0%** | 3 | 22 |
| **V7.1 (Audit)** | 4 / 5 | 3 / 20 | 3 / 20 | **0 / 20** | **100.0%** | 30.0% | **100.0%** | 3 | 22 |
| **V8 (Semantic Reuse)**| **5 / 5** | **7 / 20** | **7 / 20** | **0 / 20** | **100.0%** | **70.0%** | **100.0%** | **7** | **18** |

### Key Insight:
* In V7, model accuracy jumped from 32% to 60%, but reuse dropped from 4 to 3 because downstream serialization starved AXI and extractor schemas dropped UART.
* In V8, keeping the model frozen and fixing downstream schemas jumped reuse from **3 to 7 (+133%)** with **0 false reuses**.

---

## 4. Systems Efficiency & Resource Reduction

*Computed relative to running standalone agentic RCA on all 25 manifestations:*

| Milestone | Baseline Total LLM Tokens | Reuse Pipeline LLM Tokens | Token Savings | Baseline LLM Calls | Reuse LLM Calls | Call Savings | Baseline Wall Clock (s) | Reuse Wall Clock (s) | Latency Reduction |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **V6** | 77,167 | 69,750 | 9.6% | 56 | 50 | 10.7% | 2,522 s | 2,194 s | 13.0% |
| **V7** | 83,238 | 66,921 | 19.6% | 48 | 41 | 14.6% | 680 s | 604 s | 11.3% |
| **V8** | 83,238 | **64,907** | **22.0%** | 48 | **33** | **31.3%** | 680 s | **512 s** | **24.7%** |

---

## 5. Architectural Milestone Synthesis

```
   V4: Zero-Shot Direct Prompting (Unsafe, 60% Hallucinations on Targets)
       │
       ▼
   V5: Deterministic Trust Gate (SourceRCAVerifier -> 0 Unsafe Reuses)
       │
       ▼
   V6: First SFT LoRA Fine-Tuning (41.7% Val Accuracy, 4 Reuses)
       │
       ▼
   V7: Contrastive GPU LoRA (76.6% Val Accuracy, 60% Benchmark, Bottleneck Discovered)
       │
       ▼
   V7.1: Systems Audit (Bottleneck Shifted to Downstream Serialization & Schemas)
       │
       ▼
   V8: Unified Semantic Certificates + Deterministic Ingestion (7 Reuses, 70% Transfer, 0 False Reuses)
```
