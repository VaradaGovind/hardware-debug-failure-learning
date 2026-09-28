# Hardware Agentic RCA: Soup Fine-Tuning & Training Pipeline

This directory contains the training configuration, data schemas, and compatibility audit for fine-tuning small open-weight language models (1.5B – 3B parameters) on hardware root-cause analysis (RCA) tasks using **Soup** (`soup-cli`).

---

## 1. Hardware Compatibility Assessment

| Hardware Resource | Machine Specification | Compatibility Status | Recommended Workflow |
|---|---|---|---|
| **CPU** | AMD Ryzen 7 7735HS (8 Cores, 16 Threads) | Supported (Fast 16-thread AVX/AVX2) | Layer-streaming CPU training or local inference |
| **RAM** | 16 GB DDR5 System RAM | Supported | Holds frozen 1.5B/3B base models in system memory |
| **GPU** | AMD Radeon RX 7600S Laptop GPU (8 GB VRAM) | Partially Supported (DirectML/Vulkan on Windows) | Local Vulkan Ollama inference; DirectML training |
| **WSL2 Environment** | Ubuntu 26.04 (`/dev/dxg` present, `/dev/kfd` absent) | ROCm Not Supported in WSL | Avoid forcing fragile ROCm builds; train via CPU or host DirectML |

---

## 2. Soup Framework Evaluation

- **Repository:** [`MakazhanAlpamys/Soup`](https://github.com/MakazhanAlpamys/Soup)
- **Key Mechanism:** *Layer Streaming* — streams individual decoder layers between RAM and GPU/VRAM during forward and backward passes.
- **Suitability for This Machine:**
  - Allows fine-tuning 1.5B to 3B models (e.g., `Qwen2.5-Coder-1.5B-Instruct`) without requiring large GPU VRAM clusters.
  - On AMD hardware without native Linux ROCm KFD drivers, Soup falls back to CPU layer streaming or standard PyTorch backends.

---

## 3. Dataset Generation & Zero-Leakage Guarantee

To prevent test-set data leakage, `scripts/prepare_soup_dataset.py` constructs training and validation splits from the non-heldout benchmark catalog while strictly excluding all 25 evaluation stream cases (`heldout_*`, `*_vl_*`, etc.).

### Generating the Dataset
```bash
python scripts/prepare_soup_dataset.py
```

### Dataset Artifacts (Stored in Local Cache)
- Training Split: `~/.cache/rca-reuse/training/rca_train.json` (24 examples, or configured via `$RCA_REUSE_CACHE_DIR`)
- Validation Split: `~/.cache/rca-reuse/training/rca_val.json` (6 examples)
- Schema Definition: [`training/schemas/rca_training_schema.json`](schemas/rca_training_schema.json)

---

## 4. Soup Decision Gate Status (Section 79)

| Gate Condition | Status | Evidence |
|---|:---:|---|
| 1. Deterministic RCA-Reuse works | **PASS** | 25/25 safety property and unit tests pass. |
| 2. Minimal Agentic RCA backend works | **PASS** | `AgenticRCABackend` executes multi-step tool-use loops. |
| 3. RCA-Reuse integrates with Agentic backend | **PASS** | Evaluator coordinates paired validation with live LLM backend. |
| 4. Controlled baseline experiment runs | **PASS** | Full 25-case paired comparison recorded in `results/cost_analysis/`. |
| 5. Base model has measurable limitations | **PASS** | Base Qwen2.5-Coder-1.5B achieves 16.0% accuracy on complex raw RTL. |
| 6. Training data created without test leakage | **PASS** | Zero held-out test overlap verified by `prepare_soup_dataset.py`. |
| 7. Hardware compatibility understood | **PASS** | External artifact paths, Vulkan inference, and portable YAML configs prepared. |

---

## 5. Training Execution Instructions

When fine-tuning in an environment with GPU acceleration (or CPU layer-streaming):

```bash
# 1. Install Soup CLI in external environment
pip install "soup-cli[train]"

# 2. Dry-run and validate YAML configuration
soup check --config training/configs/soup_rca_lora.yaml

# 3. Launch training
soup train --config training/configs/soup_rca_lora.yaml
```
