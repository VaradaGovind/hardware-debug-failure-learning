# Experiment V10.1: Agentic SFT Failure Forensics Report

**Author:** Google DeepMind Advanced Agentic Coding Pair  
**Date:** September 4, 2026  
**Status:** COMPLETED & VERIFIED  
**Baseline Model:** Qwen2.5-Coder-1.5B-Instruct + Soup V7 LoRA Adapter (`soup_v7_qwen_lora`)  
**Investigated Checkpoints:** V10 Model A (Generic SFT), V10 Model B (Topological SFT)  
**Primary Finding:** Pathological Context Truncation & Loss Masking Defect (0% Tool Calls Trained)

---

## 1. Executive Summary & Core Verdict

The objective of Experiment V10.1 was to perform a forensic root-cause analysis into the severe diagnostic and reuse regressions observed in Experiment V10:
* Frozen V8 on V10 disjoint validation: **58.2%** (53/91)
* V10 Model A on disjoint validation: **40.7%** (37/91)
* V10 Model B on disjoint validation: **8.8%** (8/91)
* V8 on frozen 25-case stream: **68.0%** (17/25, 7 autonomous reuses)
* Model A on frozen 25-case stream: **40.0%** (10/25, 4 autonomous reuses)
* Model B on frozen 25-case stream: **8.0%** (2/25, 0 autonomous reuses)

### The Smoking Gun:
The investigation discovered a **catastrophic implementation defect in the multi-turn training data ingestion pipeline (`scripts/train_v10_agentic_lora.py`)**:

1. **Severe Context Truncation**: Multi-turn agentic trajectories in V10 averaged **5,434.6 tokens** (minimum 2,777 tokens). However, the training script enforced an arbitrary context ceiling of `max_length = 768`.
2. **Pathological Slicing**: The script truncated sequences using:
   ```python
   head_len = min(120, max_length // 4)  # 120 tokens
   tail_len = max_length - head_len       # 648 tokens
   full_ids = full_ids[:head_len] + full_ids[-tail_len:]
   ```
3. **100% of Tool Calls Excised**: In **100.0% (988/988)** of training trajectories, the middle 4,000–7,500 tokens were discarded. This middle region contained:
   - The failing symptom and initial context,
   - The list of candidate signals and ports,
   - **Every single assistant tool-call action (`tool_call`) across all turns**,
   - All simulation logs and waveform summaries.
4. **Zero Tool-Calling Gradients**: In the entire training dataset that the model actually saw, **EXACTLY ZERO (0 / 988, 0.0%) `tool_call` actions survived**.
5. **Trained Exclusively to Terminate Prematurely**: The model was trained *only* on the concluding JSON suffix (`action: conclude`) spliced directly onto a truncated fragment of the system prompt. Consequently, during evaluation, **the models terminated immediately on Step 1 in 100% of cases (0% tool invocation rate)**, guessing blindly without querying tools.
6. **Model B Over-Suppression**: In Model B, 70.1% of the dataset consisted of hard-negative contrast examples whose concluding thoughts emphasized rejection. When truncated to the concluding suffix, Model B collapsed into an over-suppressed state, predicting `unknown` on 55%+ of cases.

**Primary Classification**: **CASE 2 — The training setup is clearly pathological.**  
Experiment V10 did not test the capability of Agentic SFT; it inadvertently tested the behavior of a model trained on mutilated, tool-less text fragments.

---

## 2. Checkpoint Loading & Architecture Verification

All three checkpoints were inspected and validated:
- **Base Architecture**: `Qwen/Qwen2.5-Coder-1.5B-Instruct`
- **Tokenizer**: 151,665 vocabulary size, identical ChatML special tokens (`<|im_start|>`, `<|im_end|>`)
- **LoRA Configuration**: $r=16$, $\alpha=32$, target modules `[q_proj, v_proj]`, 112 LoRA weight tensors across 28 decoder layers
- **Weights Integrity**: Non-zero weight norms, distinct parameter distributions across checkpoints.
- **Verdict**: Checkpoint loading is **100% verified and correct**. Weight corruption or loading failure is ruled out.

---

## 3. Same-Input Behavioral Comparison (20 Representative Cases)

A 20-case representative benchmark spanning FIFO, AXI, FSM, UART, Pipeline, UNKNOWN, and Paired Hard Negatives was evaluated under strictly identical prompt and environment conditions (`results/reports/v10_1_behavioral_comparison.json`).

| Metric | Frozen V8 Baseline | V10 Model A (Generic) | V10 Model B (Topological) |
|---|---|---|---|
| **Diagnostic Accuracy (20 Cases)** | **10 / 20 (50.0%)** | 3 / 20 (15.0%) | 3 / 20 (15.0%) |
| **Invoked Tools at Step 1** | **15 / 20 (75.0%)** | **0 / 20 (0.0%)** | **0 / 20 (0.0%)** |
| **Premature Conclude at Step 1** | 5 / 20 (25.0%) | **20 / 20 (100.0%)** | **20 / 20 (100.0%)** |
| **Average Steps Taken** | **2.05 steps** | **1.00 steps** | **1.00 steps** |
| **Hallucinated Signal Rate** | 3 / 20 (15.0%) | **7 / 20 (35.0%)** | 3 / 20 (15.0%) |
| **Unjustified `unknown` Rate** | 0 / 20 (0.0%) | 4 / 20 (20.0%) | **11 / 20 (55.0%)** |

---

## 4. Identification of the First Point of Failure

The evaluation was categorized into 9 distinct potential failure stages:
1. Initial Interpretation
2. Tool Selection
3. Tool Argument Generation
4. Tool Result Interpretation
5. Hypothesis Generation
6. Temporal Reasoning
7. Candidate Discrimination
8. Final RCA Formatting
9. Structured Output Formatting

### Failure Stage Quantification:
* **V8**: Succeeded in 10 cases; 2 failed at Step 1 tool selection; 8 failed at downstream tool argument matching or aliased signal naming.
* **Model A**: **17 / 20 failures (85%) occurred at Stage 2 (Tool Selection)**. In 100% of cases, Model A refused to invoke tools and immediately terminated at Step 1.
* **Model B**: **17 / 20 failures (85%) occurred at Stage 2 (Tool Selection)**. Like Model A, Model B never invoked a single tool, immediately outputting `action: conclude` at Step 1.

---

## 5. Format & Schema Collapse Analysis

| Schema Property | Frozen V8 | Model A | Model B |
|---|---|---|---|
| Valid JSON Syntax Rate | 100.0% | 100.0% | 100.0% |
| Valid Final RCA Structure | 100.0% | 100.0% | 100.0% |
| Valid Tool Call Execution Rate | **75.0%** | **0.0%** | **0.0%** |
| Premature Termination Rate | 25.0% | **100.0%** | **100.0%** |

**Finding**: The model outputs were syntactically valid JSON. There was no JSON syntax collapse. The collapse was purely **procedural/agentic**: the models learned to bypass tool execution entirely.

---

## 6. Context Truncation Deep Dive (The Root Bug)

The multi-turn ChatML formatting logic in `scripts/train_v10_agentic_lora.py` and `scripts/train_v9_agentic_lora.py` contained a fatal flaw:

```python
# scripts/train_v10_agentic_lora.py (Lines 58-63)
if len(full_ids) > max_length:
    head_len = min(120, max_length // 4)
    tail_len = max_length - head_len
    full_ids = full_ids[:head_len] + full_ids[-tail_len:]
    labels = labels[:head_len] + labels[-tail_len:]
```

### Empirical Distribution of V10 Trajectory Token Lengths:
* **Training Set (988 Trajectories)**:
  - Minimum Length: **2,777 tokens**
  - Maximum Length: **8,170 tokens**
  - Mean Length: **5,434.6 tokens**
  - Trajectories Exceeding 768 Budget: **988 / 988 (100.0%)**
* **Validation Set (91 Trajectories)**:
  - Minimum Length: **3,035 tokens**
  - Maximum Length: **6,868 tokens**
  - Mean Length: **5,114.4 tokens**
  - Trajectories Exceeding 768 Budget: **91 / 91 (100.0%)**

### The Splicing Artifact:
For every single training example:
- Tokens 0 to 119 captured the first half of the system prompt (`...5. get_wave`).
- Tokens 120 to 767 captured the final 648 tokens of the concluding turn.
- Over **4,500 tokens of intermediate context were chopped out** at an arbitrary character boundary.
- The initial failure context, bug symptom, candidate signal list, and all tool-call turns were erased.

---

## 7. Assistant-Token Loss Masking Audit

We audited which tokens actually received gradient supervision:
```
Total training examples: 988
Examples where [Step 1/] survived: 75 / 988 (7.6%)
Examples where a tool_call action survived in training: 0 / 988 (0.0%)
```
* **Tool-Call Tokens Trained**: **0 tokens (0.0%)**
* **Tool-Result Tokens Trained**: Correctly masked with `-100`
* **User Tokens Trained**: Correctly masked with `-100`
* **Conclude Tokens Trained**: ~250 tokens per example (100% of all trained tokens)

Because `tool_call` was completely absent from the training target, the model was conditioned with 100% probability to output `action: conclude` whenever prompted.

---

## 8. Training Hyperparameters & Training Curves

| Parameter | V7 Baseline | V9 Diagnostic | V10 Model A | V10 Model B |
|---|---|---|---|---|
| Formulation | Single-Turn RCA | Multi-Turn Agentic | Multi-Turn Agentic | Multi-Turn Agentic |
| Effective Batch Size | 4 | 4 | 4 | 4 |
| Learning Rate | 2.5e-4 | 2.0e-4 | 2.0e-4 | 2.0e-4 |
| Epochs | 3 | 3 | 3 | 3 |
| Max Context Length | 768 (Preserves prompt) | 768 (Truncates middle) | 768 (Truncates middle) | 768 (Truncates middle) |
| Surviving Tool Calls | N/A (Single-Turn) | ~0% (Masked by leakage) | **0% (0/988)** | **0% (0/988)** |
| Final Train Loss | 0.0450 | 0.0035 | **0.0021** | **0.0019** |

### Why Loss Collapsed to 0.002:
Training loss collapsed to ~0.002 not because the model learned hardware reasoning, but because it was fitting a repetitive ~250-token concluding JSON boilerplate template after arbitrary text.

---

## 9. Dataset Composition & Label Quality

- **Underlying RTL & Simulations**: 100% verified. Real Icarus Verilog testbenches generated authentic simulation logs and VCD traces.
- **Topology Disjointness**: 100% verified. 0 exact matches, 0 structural matches with the frozen benchmark.
- **Model B Dataset Skew**:
  - Positive RCA: 220 (22.3%)
  - Hard Negatives: **693 (70.1%)**
  - UNKNOWN: 75 (7.6%)
  - In Model B, 70% of surviving templates were negative rejection arguments. Deprived of context, Model B collapsed into an over-suppressed state.

---

## 10. Evaluation Harness Verification

We verified the evaluation harness against the frozen 25-case benchmark:
1. **V8 Baseline**: Reproduces **68.0%** (17/25) accuracy and **7 autonomous reuses** with 0 false reuses.
2. **Reporting Dictionary Key Note**: In `scripts/evaluate_v10_full_study.py`, terminal display accessed `reuse_accuracy_pct` instead of `reuse_pipeline_diagnosis_correctness`. The actual JSON data revealed:
   - **Model A**: Achieved **40.0%** (10/25) stream accuracy and **4 autonomous reuses** (matching V9).
   - **Model B**: Achieved **8.0%** (2/25) stream accuracy and **0 autonomous reuses**.

---

## 11. Primary Failure Mode Determination

| Potential Cause | Verdict | Numerical Evidence |
|---|---|---|
| **A. Checkpoint Loading Bug** | **RULED OUT** | Checkpoints load verified distinct weights, float16 dtype, identical vocab. |
| **B. Format / JSON Syntax Collapse** | **RULED OUT** | 100% of outputs were valid JSON. |
| **C. Hardware / Topology Contamination** | **RULED OUT** | 0 exact, 0 structural leakage confirmed by AST fingerprinting. |
| **D. Evaluation Harness Flaw** | **RULED OUT** | V8 reproduces 68% / 7 reuses; Model A achieved 40% in saved JSON. |
| **E. Context Truncation & Loss Masking Pathology** | **PRIMARY CAUSE** | **100% of examples truncated; 0 / 988 tool calls survived into training loss.** |
| **F. Agentic Reasoning Infeasibility** | **UNPROVEN** | Agentic SFT was never actually tested because 0 tool calls were trained. |

---

## 12. Scientific Usability & Final Recommendation

### Usability Verdict: **CASE 2**
> **The training setup is clearly pathological.**
> V10 represents conclusive evidence that *monolithic multi-turn sequence truncation at 768 tokens* is fatal for agentic training. However, it does NOT prove that Agentic SFT itself is fundamentally impossible.

### Official Recommendation:
**RECOMMENDATION B: Keep V8 as the official operational baseline and redesign the Agentic SFT training methodology.**

### Remediation Blueprint for Future Agentic SFT (Post-V10):
1. **Decompose Multi-Turn Trajectories into Per-Turn Examples**:
   Instead of packing an entire 5,000-token multi-turn conversation into a single sequence and chopping out the middle, decompose each trajectory into individual turn training examples:
   - Example 1: `(System + Initial Prompt) -> Tool Call 1`
   - Example 2: `(System + Context + Tool 1 Result) -> Tool Call 2`
   - Example 3: `(System + Context + Tool 1 + Tool 2) -> Conclude`
   Each turn easily fits within 1,024–1,536 tokens without any loss of initial context or tool calls.
2. **Rebalance Hard Negatives**: Limit hard negatives to $\le 30\%$ of the training mixture to avoid over-suppression.
3. **Preserve V8 Invariant**: V8 remains the frozen operational baseline. No deployment or replacement until a clean per-turn agentic model demonstrates superior performance.
