# Experiment V10.2 Final Audit Baseline & Immutable Artifact Registry

**Audit Date:** September 4, 2026  
**Audit Purpose:** Final Scientific Audit, Reproducibility Verification, and Offline Hybrid Validation of Experiment V10.2  
**Operational Invariant:** All models, weights, datasets, benchmarks, and historical baselines are frozen and immutable. No training, retraining, tuning, or benchmark modification is permitted.

---

## 1. Immutable Model Checkpoints & Adapters

| Component | Identifier / Path | Format / Size | SHA-256 Hash |
|---|---|---|---|
| **V8 Baseline Adapter Config** | `C:/Users/varad/ml-cache/rca-reuse/v7/checkpoints/soup_v7_qwen_lora/best_v7_checkpoint/adapter_config.json` | JSON (1,132 B) | `c5fbe1e33e2ee1704cbf11beaa5b12aa84729b7cd2cc98d814099d569232fa09` |
| **V8 Baseline Adapter Weights** | `C:/Users/varad/ml-cache/rca-reuse/v7/checkpoints/soup_v7_qwen_lora/best_v7_checkpoint/adapter_model.safetensors` | Safetensors (8,731,128 B) | `e4a33d47bfcca0c922cb3971101fdc92f4e67b6f6783cba8fa1004ca44c1dee4` |
| **V10.2 Agentic Adapter Config**| `C:/Users/varad/ml-cache/rca-reuse/v10_2/checkpoints/v10_2_agentic_lora/best_v10_2_checkpoint/adapter_config.json` | JSON (1,132 B) | `c5fbe1e33e2ee1704cbf11beaa5b12aa84729b7cd2cc98d814099d569232fa09` |
| **V10.2 Agentic Adapter Weights**| `C:/Users/varad/ml-cache/rca-reuse/v10_2/checkpoints/v10_2_agentic_lora/best_v10_2_checkpoint/adapter_model.bin` | PyTorch Bin (8,755,146 B) | `93572b01be8335174196aa5a91987abc8c68d02029792a3f70ce92c3e2b6eeea` |
| **Base Model Architecture** | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | Transformers CausalLM | Frozen HuggingFace Hub Release |

---

## 2. Immutable Dataset Splitting & Trajectories

| Dataset Partition | File Path | Records / Size | SHA-256 Hash |
|---|---|---|---|
| **V10.2 Per-Turn Train Set** | `datasets/v10_2/per_turn_train_v10_2.json` | 618 turns (2,632,679 B) | `fca974db81e9d269acf029718644957e19e825e09be3c3f3586058823079493a` |
| **V10.2 Per-Turn Validation Set**| `datasets/v10_2/per_turn_val_v10_2.json` | 114 turns (483,614 B) | `d8cfcdf6d9490b13eebc230f0c4d9bcab12ed5dff49099dd568d6b7cd6456def` |
| **V10.2 Per-Turn Gen Set** | `datasets/v10_2/per_turn_gen_v10_2.json` | 36 turns (150,879 B) | `c2bd6b191b2bbf90e85d6b077f828b9fa501c9676a61a6c493afe081572b11a8` |
| **V10 Disjoint Validation Suite**| `datasets/v10/agentic_val_v10.json` | 91 cases (1,673,328 B) | `1db0b8f295c10fea02b80c53d4c5383dfa2ac880a62c4f5ab59d5f6390dd1f40` |
| **V10 Unseen Topology Suite** | `datasets/v10/agentic_gen_v10.json` | 30 cases (598,297 B) | `7e54c9cdd618f538b16103adfb390e4aa367889c1b0cf32ecd72e7750a382301` |
| **V9 Pipeline Gen Suite** | `datasets/v9/pipeline_generalization_suite.json` | 5 cases (2,736 B) | `cf7b9bfc5f0de674a03cf53b3378ab9c01ead801d22a74e280534a671c14e95c` |

---

## 3. Immutable Historical Results & Audit Files

| Experimental Record | File Path | Size | SHA-256 Hash |
|---|---|---|---|
| **V10.2 Full Evaluation Report** | `results/reports/v10_2_evaluation_report.json` | 82,598 B | `eeced8b06e5336446afc8d526993c1082d424d13b58c7ce91e8144f6c05f4548` |
| **V10.2 End-to-End Stream Report**| `results/cost_analysis/v10_2_end_to_end_comparison.json` | 39,358 B | `38ecd1ac9f7354ad0320982d2e327315058930c204ecd492f6dc0ad2c581be26` |
| **V8 Baseline Pretrain Report** | `results/reports/v10_pretrain_validation_baseline.json` | 24,482 B | `2ce210880563b99f4b0a21fe296315f986a114068c01af3215014d79d7b6bc89` |
| **V8 End-to-End Stream Report** | `results/cost_analysis/v8_end_to_end_comparison.json` | 51,743 B | `c52a3c45cda6242b7da158287f8e83cca148ac12aa7caf98e66bd607ec693dab` |

---

## 4. Immutable Evaluation Harness & Safety Architecture

| Subsystem Component | File Path | Size | SHA-256 Hash |
|---|---|---|---|
| **Controlled Stream Definition** | `experiments/run_rca_vs_reuse_controlled_comparison.py` | 15,625 B | `bd65cd7b4a9f18a28190c36e1c6d5eb0f540d072361255a2c4f3d99c27ffd1c9` |
| **Evaluation Harness Implementation** | `src/evaluation/rca_vs_reuse_harness.py` | 23,512 B | `c1f0c229943b3fc95499ebf384325aa28536fa9bb38995a9a26afe264384e92a` |
| **Formal Safety Gate Validator** | `src/reuse/remediated_certificate_validator.py` | 12,387 B | `326f2f69f9c753e05a487f9de7bc13b7341d8a3bcd87f10690023516858484e0` |
| **V8 Unified Semantic Certificate**| `src/reuse/v8_unified_certificate.py` | 8,418 B | `f5ba55847f6d7215f6feb5aa6e47bda0cd56f0dbf2791338ef5c3a5f9f27fb69` |
| **V8 Dynamic Certificate Store** | `src/reuse/v8_certificate_store.py` | 11,321 B | `141d24b50c753c0509744175d42ce7a05549febf816c4fcf46290f4009f7f64b` |

---

## 5. Audit Policy & Behavioral Invariants

1. **Frozen Operational Baseline**: V8 remains the frozen operational baseline throughout this audit.
2. **Strict Invariant**: No model retraining, fine-tuning, adapter modification, or benchmark tampering is permitted.
3. **Safety Verification Standard**: All safety conclusions adhere strictly to: *"0 false reuses were observed on the frozen evaluation."*
