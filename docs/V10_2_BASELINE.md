# Experiment V10.2: Baseline & Historical Experimental Record

**Date:** September 4, 2026  
**Status:** ACTIVE EXPERIMENTAL STUDY  
**Target:** Corrected Per-Turn Agentic SFT Formulation  
**Operational Invariant:** V8 remains the frozen operational baseline.

---

## 1. Frozen Operational Baseline (V8)

The V8 operational baseline is frozen and immutable:
- **Base Model**: `Qwen/Qwen2.5-Coder-1.5B-Instruct`
- **Adapter**: Soup V7 LoRA (`soup_v7_qwen_lora`)
- **Benchmark**: Canonical 25-Case Sequential Failure Stream
- **Diagnostic Accuracy**: **68.0% (17 / 25)**
- **Autonomous Knowledge Reuses**: **7 / 20 (+133% over V4/V5)**
- **Unsafe False Reuses**: **0 / 20 (100% precision)**
- **Negative Rejection Rate**: **10 / 10 (100.0%)**
- **Token Reduction**: **22.0%**
- **Latency Reduction**: **24.7%**
- **Architecture**: Unified Semantic Certificates (`V8UnifiedCertificate`), Protocol Registry, Deterministic Ingestion, Adaptive Settlement, V5 Formal Verification Gate.

---

## 2. Historical Negative Experiments (V9, V10, V10.1)

| Experiment | Configuration | Disjoint Validation Acc | Unseen Topology Gen | Frozen Stream Acc | Autonomous Reuses | Primary Failure Cause |
|---|---|---|---|---|---|---|
| **V8 Baseline** | Single-turn V7 + V8 reuse stack | 58.2% (53/91) | 0.0% (0/30) | **68.0%** (17/25) | **7 / 20** | Operational baseline. Fails on pipeline temporal reasoning (`d1` vs `v1`). |
| **V9 Diagnostic** | Monolithic Multi-turn SFT | 44.0% | 0.0% (0/5) | 40.0% (10/25) | 4 / 20 | Severe dataset contamination masked sequence truncation; 16% invalid output rate. |
| **V10 Model A** | Monolithic SFT (clean catalog) | 40.7% (37/91) | 0.0% (0/30) | 40.0% (10/25) | 4 / 20 | Monolithic 768-token truncation excised all `tool_call` actions from training target (0% tool supervision). |
| **V10 Model B** | Monolithic SFT + 70% hard negatives | 8.8% (8/91) | 0.0% (0/30) | 8.0% (2/25) | 0 / 20 | Severe negative-suppression bias caused by suffix-only truncation on 70% hard-negative dataset. |
| **V10.1 Forensics** | Forensic Audit of V10 | N/A | N/A | N/A | N/A | Proved mathematically that 100% of V10 multi-turn trajectories were truncated (`[:120] + [-648:]`), resulting in 0/988 tool-call actions surviving in training loss. |

---

## 3. The V10.2 Scientific Hypothesis

> **Per-turn / trajectory-segment Agentic SFT can teach tool-use and multi-step hardware debugging more reliably than monolithic truncated trajectory SFT.**

### Core Implementation Principles for V10.2:
1. **Decomposed Per-Turn Examples**:
   - **Type A (Tool Selection)**: `Context -> Next Tool Call` (e.g. `read_rtl_file`)
   - **Type B (Evidence-Conditioned Action)**: `Context + Tool Result -> Next Tool Call` (e.g. `get_waveform_summary`)
   - **Type C (Final Decision)**: `Context + Complete Evidence -> Final RCA or UNKNOWN`
2. **Context Budget Compliance**:
   - Each training example is self-contained with complete context within 512–1,536 tokens.
   - **0% critical evidence or tool schema truncation**.
3. **Guaranteed Tool-Call Supervision**:
   - Substantial ratio ($\ge 50\%$) of training examples have `action: tool_call` as their explicit supervised target.
4. **Mandatory Behavioral Smoke Test Gate**:
   - Before full training, verify on 5 test cases that the model actually calls tools.
