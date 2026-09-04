# V7.1 Baseline: Frozen Metrics & Artifact Registry

**Experiment:** V7.1 — Reuse Bottleneck Analysis  
**Project:** Hardware Failure Debugging & Knowledge Reuse  
**Evaluation Stream:** Canonical Frozen 25-Case Evaluation Stream (`get_controlled_comparison_stream`)  
**Safety Gate:** V5 Deterministic Source RCA Verifier & Adaptive L2 Validator  
**Status:** FROZEN & IMMUTABLE  

---

## 1. Executive Summary

This document establishes the official frozen baseline for Experiment **V7.1**. 

Experiment V7 produced a substantial advancement in root-cause analysis (RCA) model capability:
* Validation diagnostic accuracy rose from **41.7% to 76.6% (+34.9%)**.
* Agentic tool-assisted diagnostic accuracy on the frozen 25-case stream rose from **32.0% to 60.0% (+28.0%)**.
* Hallucinatory wrong-signal rate plummeted from **58.3% to 23.0% (-35.3%)**.
* Hard-negative discrimination increased from **46.3% to 72.7% (+26.4%)**.

However, this model-level breakthrough did **not** translate into higher autonomous reuse:
* Trusted certificates generated: **4 (V6) $\rightarrow$ 4 (V7)**.
* Correct reuses: **4 (V6) $\rightarrow$ 3 (V7)** (-1 net reuse).
* False reuses: **0 (V6) $\rightarrow$ 0 (V7)** (100% precision maintained).
* Expensive full RCA investigations avoided: **4 (V6) $\rightarrow$ 3 (V7)**.
* Full RCA investigations executed: **21 (V6) $\rightarrow$ 22 (V7)**.

All V7 checkpoints, datasets, evaluation streams, and safety gates are strictly frozen. This document logs their immutable artifacts and metric baselines.

---

## 2. Immutable Artifact Registry

The following paths represent the exact frozen assets used for the V7.1 investigation:

| Asset Category | Canonical Filepath / Identifier | Description |
|---|---|---|
| **V7 Model Checkpoint** | `~/.cache/rca-reuse/v7/checkpoints/soup_v7_qwen_lora/best_v7_checkpoint` | Best V7 fine-tuned LoRA adapter on Qwen2.5-Coder-1.5B-Instruct |
| **V6 Model Checkpoint** | `~/.cache/rca-reuse/v6/checkpoints/soup_qwen_rca_lora/best_v6_checkpoint` | Prior V6 baseline LoRA adapter on Qwen2.5-Coder-1.5B-Instruct |
| **V7 Validation Dataset** | `~/.cache/rca-reuse/v7/datasets/rca_val_v7.json` | 235-case canonical evaluation dataset with hard negatives and UNKNOWN cases |
| **V7 Frozen Evaluation Results** | `results/cost_analysis/v7_end_to_end_comparison.json` | Comprehensive machine-readable execution log of 25-case frozen stream |
| **V7 Case Transitions** | `results/cost_analysis/v7_end_to_end_comparison.csv` | CSV transition matrix tracking all 25 case diagnoses and correctness |
| **V6 Frozen Evaluation Results** | `results/cost_analysis/v6_end_to_end_comparison.json` | Baseline V6 evaluation on identical 25-case frozen stream |
| **V6 Case Transitions** | `results/cost_analysis/v6_end_to_end_comparison.csv` | CSV transition matrix for V6 baseline |
| **V7 Source Certificate Log** | `results/cost_analysis/v7_end_to_end_comparison.json` (`v7_records[0, 5, 10, 15, 20]`) | Verifier decisions, explanations, and trust states for all 5 source cases |
| **Safety Gate Architecture** | `src/reuse/source_rca_verifier.py`, `src/reuse/certificate_store.py` | V5 multi-layer deterministic trust verifier and adaptive L2 validator |

---

## 3. Upstream Model Quality Metrics (V6 vs V7)

Evaluated on the 235-case canonical validation dataset (`rca_val_v7.json`):

| Diagnostic Metric | V6 Baseline | V7 (Current) | Absolute Delta | Relative Gain |
|---|:---:|:---:|:---:|:---:|
| **Overall Diagnostic Accuracy** | 41.7% (98/235) | **76.6% (180/235)** | **+34.9%** | **+83.7%** |
| **Grounded Rate** | 40.0% (94/235) | **76.2% (179/235)** | **+36.2%** | **+90.5%** |
| **Wrong-Signal Rate (Hallucinations)** | 58.3% (137/235) | **23.0% (54/235)** | **-35.3%** | **-60.5%** |
| **Abstention Rate (UNKNOWN)** | 10.2% (24/235) | **5.5% (13/235)** | **-4.7%** | **-46.1%** |
| **Invalid Output Rate** | 0.0% (0/235) | **0.4% (1/235)** | +0.4% | N/A |
| **Hard-Negative Discrimination** | 46.3% (31/67) | **72.7% (48/66)** | **+26.4%** | **+57.0%** |
| **UNKNOWN Classification Accuracy** | 14.8% (4/27) | **55.6% (15/27)** | **+40.8%** | **+275.7%** |
| **Positive RCA Accuracy** | 44.7% (63/141) | **82.3% (117/142)** | **+37.6%** | **+84.1%** |

---

## 4. End-to-End Frozen 25-Case Benchmark Metrics (V6 + V5 vs V7 + V5)

Evaluated across the 25-case stream (5 source cases + 20 downstream target arrivals):

| Pipeline Metric | System A (V6 + V5 Safety) | System B (V7 + V5 Safety) | Delta (V6 $\rightarrow$ V7) |
|---|:---:|:---:|:---:|
| **Total Failure Manifestations** | 25 | 25 | 0 |
| **Source Cases** | 5 | 5 | 0 |
| **Target Arrivals** | 20 | 20 | 0 |
| **Independent Baseline Correct Count** | 8 / 25 (32.0%) | **15 / 25 (60.0%)** | **+7 cases (+28.0%)** |
| **Reuse Pipeline Correct Count** | 7 / 25 (28.0%) | **14 / 25 (56.0%)** | **+7 cases (+28.0%)** |
| **Source RCA Accuracy (Baseline)** | 2 / 5 (40.0%) | **3 / 5 (60.0%)** | **+1 case (+20.0%)** |
| **Trusted Certificates Generated** | 4 | 4 | 0 |
| **Reuse Attempts** | 20 | 20 | 0 |
| **Total Reuses Applied** | 4 | 3 | **-1 reuse (-25.0%)** |
| **Successful (Correct) Reuses** | 4 | 3 | **-1 reuse (-25.0%)** |
| **Unsafe (False) Reuses** | **0** | **0** | **0 (Zero Tolerance Maintained)** |
| **Reuse Precision** | **100.0%** | **100.0%** | 0.0% |
| **False Reuse Rate** | **0.0%** | **0.0%** | 0.0% |
| **Positive Transfer Rate** | 40.0% (4/10 positive targets) | 30.0% (3/10 positive targets) | -10.0% |
| **Negative Rejection Rate** | **100.0% (10/10 negatives)** | **100.0% (10/10 negatives)** | 0.0% |
| **RCA Invocations Avoided** | 4 | 3 | **-1 avoided (-25.0%)** |
| **Full RCA Invocations Required** | 21 | 22 | +1 invocation |
| **Fallback Rate** | 80.0% (16/20) | 85.0% (17/20) | +5.0% |

---

## 5. Compute, Operations, and Latency Baselines

| Efficiency Metric | V6 + V5 Reuse | V7 + V5 Reuse | Delta |
|---|:---:|:---:|:---:|
| **Baseline LLM Tokens** | 77,167 | 83,238 | +6,071 (+7.9%) |
| **Reuse Pipeline LLM Tokens** | 69,750 | 66,921 | **-2,829 (-4.1%)** |
| **Token Reduction via Reuse** | 9.6% | **19.6%** | **+10.0% efficiency gain** |
| **Baseline LLM Calls** | 56 | 48 | -8 calls (-14.3%) |
| **Reuse Pipeline LLM Calls** | 50 | 41 | -9 calls (-18.0%) |
| **LLM Call Reduction via Reuse** | 10.7% | **14.6%** | **+3.9% efficiency gain** |
| **Baseline Wall-Clock (Total ms)** | 2,522,620 ms (~42.0 min) | 680,277 ms (~11.3 min) | **-73.0% speedup** |
| **Reuse Pipeline Wall-Clock (Total ms)** | 2,194,232 ms (~36.6 min) | 603,707 ms (~10.1 min) | **-72.5% speedup** |
| **Latency Reduction via Reuse** | 13.0% | 11.3% | -1.7% |

---

## 6. Baseline Anomaly Summary

The baseline numbers expose three critical system behaviors that define the V7.1 investigation:

1. **The Disconnect**: Upstream RCA accuracy grew by **+28.0%**, but autonomous reuse fell from **4 to 3**.
2. **The Source Asymmetry**: V7 produced **3 correct source diagnoses** vs V6's **2**, yet produced the exact same number of trusted certificates (**4**) and fewer reuses.
3. **The Absolute Safety Invariant**: Across both V6 and V7, the V5 safety architecture permitted **zero unsafe reuses** (100% precision, 0 false positives across 10 adversarial/incomplete targets).

These frozen metrics establish the quantitative starting line for V7.1.
