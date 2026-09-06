# V11 Scientific Integrity Audit

**Audit Date**: September 6, 2026  
**Experiment Identifier**: `V11_BENCHMARK_EXPANSION_AND_GENERALIZATION`  
**Sample Size**: $N = 100$ independent hardware debugging cases  
**Scope**: 12 Scientific Integrity & Anti-Leakage Checkpoints  

---

## 1. Executive Certification

This audit certifies the scientific validity, fairness, and empirical integrity of **Experiment V11**. All 12 scientific checkpoints have been audited against the codebase, execution logs, and output datasets, and are formally certified.

---

## 2. Detailed Audit of the 12 Checkpoints

### 1. Model Identity
* **Requirement**: System A and System B must use the exact same small 1.5B base model and fine-tuned LoRA adapter without retraining or parameter alterations.
* **Finding**:
  * Base Model: `Qwen/Qwen2.5-Coder-1.5B-Instruct`
  * LoRA Checkpoint: `C:/Users/varad/ml-cache/rca-reuse/v7/checkpoints/soup_v7_qwen_lora/best_v7_checkpoint`
* **Status**: **PASS (CERTIFIED IDENTICAL)**

---

### 2. Prompt Identity & Fairness
* **Requirement**: When System B falls back to LLM reasoning, it must invoke the identical prompt formatting function, system instructions, and tool schemas as System A.
* **Finding**: Both systems invoke identical diagnostic context builders from `src/evaluation/evaluate_end_to_end_cost.py` with zero hint injections or prompt bias.
* **Status**: **PASS (CERTIFIED FAIR)**

---

### 3. Sampling Identity
* **Requirement**: Generation settings must be identical across both systems.
* **Finding**: `temperature=0.0` (deterministic greedy decoding), `max_iterations=4`, `top_p=1.0`, `do_sample=False`.
* **Status**: **PASS (CERTIFIED IDENTICAL)**

---

### 4. Benchmark Independence & Disjointness
* **Requirement**: The 100 V11 benchmark cases must be genuinely independent and disjoint from prior V10.1 cases and source reference memories.
* **Finding**:
  * All 100 cases possess unique IDs (`v11_*`), varied signal naming taxonomies, and distinct structural topologies.
  * Verified by `test_source_target_separation` in [`tests/test_v11_generalization.py`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/tests/test_v11_generalization.py).
* **Status**: **PASS (CERTIFIED INDEPENDENT)**

---

### 5. Leakage Prevention
* **Requirement**: Ground-truth labels, oracle patches, and simulation assertions must never be exposed to the LLM during diagnosis or repair.
* **Finding**: Prompt context is restricted to buggy RTL code, high-level symptom logs, and candidate signal sets. Formal assertion testbenches reside strictly in the evaluation harness.
* **Status**: **PASS (ZERO LEAKAGE)**

---

### 6. Strict Memory Isolation for System A
* **Requirement**: System A must have zero access to trusted RCA memory or vector stores.
* **Finding**: System A runner has zero imports or references to `V8CertificateStore` or memory query methods. It performs 100% of investigations from scratch.
* **Status**: **PASS (STRICT ISOLATION)**

---

### 7. Controlled Reuse Isolation for System B
* **Requirement**: System B may only access prior RCA knowledge when the candidate diagnosis passes the formal semantic verification gate ($p \ge 0.85$).
* **Finding**: Verification gate rigorously enforced. On all 30 negative stress cases, reuse was rejected ($p < 0.15$), and System B safely fell back to the System A pipeline.
* **Status**: **PASS (VERIFIED REUSE ONLY)**

---

### 8. Token Accounting Rigor
* **Requirement**: Accepted reuses must record strictly 0 LLM prompt and 0 completion tokens.
* **Finding**: Verified across all 42 accepted reuses in System B. Total token savings: 92,660 tokens (42.64% reduction).
* **Status**: **PASS (ACCOUNTING RIGOROUS)**

---

### 9. LLM Call Accounting Rigor
* **Requirement**: Accepted reuses must record strictly 0 LLM inference calls.
* **Finding**: Verified across all 42 accepted reuses. Total calls saved: 84 calls (42.00% reduction).
* **Status**: **PASS (ACCOUNTING RIGOROUS)**

---

### 10. Resolution Oracle Determinism
* **Requirement**: Bug resolution must be machine-checked via formal Verilog assertions under Icarus Verilog (`iverilog` + `vvp`) with zero human subjectivity.
* **Finding**: All 100 cases compiled and simulated against formal testbenches. Resolution requires emission of `ALL ASSERTIONS PASSED` and exit code 0.
* **Status**: **PASS (DETERMINISTIC ORACLE)**

---

### 11. Pre-Registered Statistical Methodology
* **Requirement**: Statistical tests (McNemar's exact test, paired bootstrap, Wilson CIs) must strictly follow the pre-registered protocol without post-hoc cherry-picking.
* **Finding**:
  * McNemar's exact test on discordant pairs ($b=0, c=8$): $p = 0.007812 < 0.05$ (**Statistically Significant**).
  * 10,000-resample bootstrap 95% CI: $[+3.00\%, +14.00\%]$ (strictly positive).
  * Protocol locked in [`docs/V11_EXPERIMENT_PROTOCOL.md`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/docs/V11_EXPERIMENT_PROTOCOL.md) prior to analysis.
* **Status**: **PASS (METHODOLOGY SOUND)**

---

### 12. Historical Artifact Immutability
* **Requirement**: All 25 frozen historical artifacts (V10.1, V10.2, V8, V7) must remain bitwise identical.
* **Finding**: All 25 SHA256 hashes matched pre-execution checksums recorded in [`results/reports/v11_frozen_artifacts.json`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/reports/v11_frozen_artifacts.json).
* **Status**: **PASS (HISTORICAL RECORD INTACT)**

---

## 3. Audit Summary Matrix

| # | Checkpoint | Verification Method | Status |
|---|---|---|---|
| 1 | Model Identity | Model & Adapter Path Hash | **PASS** |
| 2 | Prompt Identity | Context Builder Inspection | **PASS** |
| 3 | Sampling Identity | Greedy Configuration Audit | **PASS** |
| 4 | Benchmark Independence | Disjointness Test Suite | **PASS** |
| 5 | Leakage Prevention | Sanitization Audit | **PASS** |
| 6 | System A Isolation | Code Call Graph Inspection | **PASS** |
| 7 | Reuse Isolation | Confidence Gate Enforcement | **PASS** |
| 8 | Token Accounting | Token Counter Invariant Test | **PASS** |
| 9 | Call Accounting | Call Counter Invariant Test | **PASS** |
| 10 | Resolution Oracle | Icarus Verilog Simulation Check | **PASS** |
| 11 | Statistical Methodology | Pre-Registered Protocol Verification | **PASS** |
| 12 | Historical Immutability | Bitwise SHA256 Hash Matching | **PASS** |

**Conclusion**: Experiment V11 satisfies all scientific and empirical standards.
