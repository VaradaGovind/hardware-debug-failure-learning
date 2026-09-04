# V7 Training Configuration & Experimental Contamination Audit

**Document Identifier:** `docs/V7_TRAINING_AUDIT.md`  
**Configuration Source:** `training/configs/soup_v7_qwen_lora.yaml`  
**Training Implementation:** `scripts/train_v7_lora.py`  
**Training Summary Artifact:** `~/.cache/rca-reuse\v7\reports\v7_training_summary.json`

---

## 1. Executive Summary

This audit verifies that the fine-tuning of `Qwen2.5-Coder-1.5B-Instruct` was executed with rigorous experimental hygiene, valid hardware acceleration parameters, and strict insulation of the frozen 25-case evaluation benchmark.

* **Target Compute Device:** AMD Radeon RX 7600S (`privateuseone:0`, 8 GB GDDR6) via DirectML.
* **Checkpoint Selection Criterion:** Selected solely via cross-entropy validation loss on `rca_val_v7.json`.
* **Zero Frozen Contamination:** Neither model weights, prompt templates, hyperparameters, nor threshold constants were exposed to or tuned on the frozen 25-case stream.

---

## 2. Parameter Specification Table

| Hyperparameter / Setting | Value | Implementation Rationale |
|---|:---:|---|
| **Base Model** | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | High-efficiency 1.5B dense parameter model suitable for local edge execution. |
| **Precision** | `torch.float16` | Required for DirectML D3D12 operator compatibility and ~4.1 GB VRAM residency. |
| **LoRA Rank ($r$)** | `16` | Provides sufficient capacity for domain adaptation without parameter bloat. |
| **LoRA Alpha ($\alpha$)** | `32` | Standard scaling ratio ($\alpha/r = 2.0$). |
| **Target Modules** | `["q_proj", "v_proj"]` | Targeted attention projection layers; minimizes activation memory footprint on DirectML. |
| **LoRA Dropout** | `0.05` | Regularization against token memorization. |
| **Trainable Parameters** | `2,179,072` (0.14%) | 2.18M out of 1.55B total base parameters. |
| **Max Sequence Length** | `768` | Sequence window cap with prompt head/tail preservation and 100% target preservation. |
| **Loss Formulation** | Active-Token Cross Entropy | Computes loss only on target JSON tokens ($80 \times 151936$), reducing memory by 20x. |
| **Per-Device Batch Size** | `1` | Minimal per-step memory footprint. |
| **Gradient Accumulation** | `4` steps | Yields an effective batch size of 4. |
| **Optimizer** | `torch.optim.AdamW` | Weight decay = 0.01, gradient clipping norm = 1.0. |
| **Initial Learning Rate** | `2.5e-4` | Tuned for stable half-precision LoRA convergence. |
| **LR Scheduler** | Cosine Annealing | 5% warmup steps (23 steps) followed by cosine decay to $0.0$. |
| **Epochs** | `2` | 466 total optimizer steps across 935 training cases. |
| **Total Training Time** | `3,038.2 s` (50.6 min) | Average step latency: `1,376.8 ms / step`. |
| **Best Validation Loss** | `0.0254` | Epoch 1: 0.0429 $\rightarrow$ Epoch 2: 0.0254. |

---

## 3. Checkpoint Selection & Blind Evaluation Protocol

### Checkpoint Selection Method
* During training, validation loss was evaluated at the end of every epoch across a random stratified subset of `rca_val_v7.json` (`compute_eval_loss`).
* The checkpoint was persisted only when `val_loss < best_val_loss`.
* **Zero Frozen Test Interaction:** The frozen test set (`FROZEN_TEST_IDS`) was neither loaded, referenced, nor evaluated during any part of the training loop.

---

## 4. Contamination & Leakage Audit

A comprehensive codebase audit was conducted across all training scripts, dataset generators, and configuration files to detect potential inadvertent contamination:

1. **Training Data Contamination:** $\checkmark$ **Passed.** All 25 frozen test identifiers (`heldout_fifo_src`, `fifo_vl_a1`, etc.) were strictly excluded via Check 2 of `build_v7_canonical_dataset.py`.
2. **Prompt Template Contamination:** $\checkmark$ **Passed.** ChatML prompt templates were standardized using standard system instructions without testbench-specific reverse-engineering.
3. **Hyperparameter Tuning Contamination:** $\checkmark$ **Passed.** Learning rate and sequence length hyperparameters were selected based on GPU memory constraints and validation loss convergence.
4. **Post-Hoc Threshold Contamination:** $\checkmark$ **Passed.** Confidence thresholds ($\tau = 0.85$) inside the `SourceRCAVerifier` remained identical to the frozen V5 architecture.
