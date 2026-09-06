# V11 Leakage & Independence Audit

**Audit Date**: September 6, 2026  
**Experiment Identifier**: `V11_BENCHMARK_EXPANSION_AND_GENERALIZATION`  
**Audit Scope**: 9 Critical Independence and Anti-Leakage Verification Checkpoints  

---

## 1. Executive Summary

This audit certifies that the 100-case **V11 Benchmark Corpus** ([`results/reports/v11_benchmark_manifest.json`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/reports/v11_benchmark_manifest.json)) is genuinely independent of prior training datasets and source reference cases, and strictly adheres to anti-leakage isolation standards between System A (Plain LLM) and System B (Verified Reuse).

All 9 programmatic integrity checkpoints have been validated.

---

## 2. Checkpoint-by-Checkpoint Audit

### Checkpoint 1: Target Disjointness from Source Reference Memory
* **Requirement**: No V11 target case may be an identical copy of any canonical source reference case.
* **Audit Finding**: All 100 cases possess unique identifiers (`v11_*`), distinct module interfaces, alternate signal naming taxonomies (e.g., `occupancy`, `fifo_level`, `rx_vld`, `s_axis_tvalid`), or structural refactoring (skid registers, decomposed logic).
* **Status**: **PASS (DISJOINT)**

---

### Checkpoint 2: Signal Name Independence & Translation Robustness
* **Requirement**: Signal names in downstream targets must not rely on trivial lexical copying from trusted certificates.
* **Audit Finding**:
  * In Category A (40 cases), signal names undergo systematic renaming (e.g., `count` is renamed to `occupancy`, `fifo_level`, `depth_cnt`, `items_in_flight`, `buf_lvl`, `fill_count`, `entry_num`, `q_depth`).
  * System B must perform AST-level semantic alignment rather than naive string matching.
* **Status**: **PASS (INDEPENDENT NAMES)**

---

### Checkpoint 3: Zero Ground-Truth Leakage in Diagnostic Prompts
* **Requirement**: Neither System A nor System B may receive `ground_truth_signal`, `ground_truth_signals`, or oracle patch diffs in the prompt context.
* **Audit Finding**:
  * Prompts are generated strictly from: (a) buggy RTL code, (b) testbench symptom description, (c) failure log snippet, and (d) candidate signal list.
  * Ground-truth labels are kept exclusively in the evaluation harness for post-simulation scoring.
* **Status**: **PASS (ZERO PROMPT LEAKAGE)**

---

### Checkpoint 4: Formal Simulation Assertions Shielded from LLM
* **Requirement**: Formal Verilog assertion testbenches (`VERIF_TESTBENCHES`) must never be provided to the LLM during diagnosis or repair.
* **Audit Finding**:
  * Testbenches reside strictly inside the compilation environment ([`src/evaluation/v11_deterministic_resolution.py`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/src/evaluation/v11_deterministic_resolution.py)).
  * The LLM only observes high-level symptom logs (e.g., `"ASSERTION FAIL: Data Mismatch"`), preventing prompt-based reverse engineering.
* **Status**: **PASS (ASSERTIONS SHIELDED)**

---

### Checkpoint 5: Strict Memory Isolation for System A
* **Requirement**: System A must have strictly zero access to RCA memory, certificate stores, or vector embeddings.
* **Audit Finding**:
  * System A runner instantiates the LLM pipeline in total isolation from `V8CertificateStore` and memory lookups.
  * System A performs an independent multi-turn investigation from scratch on every bug.
* **Status**: **PASS (STRICT SYSTEM A ISOLATION)**

---

### Checkpoint 6: Controlled Reuse Access in System B
* **Requirement**: System B may only access trusted RCA memory through the formally gated reuse mechanism.
* **Audit Finding**:
  * System B queries trusted memory, runs the multi-stage semantic verification gate (structural AST check, causal/temporal trace verification, invariant validation).
  * If verification passes with confidence $\ge 0.85$, reuse is accepted; otherwise, it falls back to the exact same prompt pipeline as System A.
* **Status**: **PASS (CONTROLLED ACCESS)**

---

### Checkpoint 7: Decoupled Deterministic Patch Synthesis
* **Requirement**: The patch synthesizer must not use ground-truth defect mechanisms or cheat via case IDs.
* **Audit Finding**:
  * The synthesizer takes only `(rtl_code, diagnosed_signal, family)`.
  * If the diagnosed signal is incorrect, the synthesized patch alters an incorrect net or fails to compile, resulting in assertion failure during simulation.
* **Status**: **PASS (DECOUPLED SYNTHESIS)**

---

### Checkpoint 8: Anti-Cheating Prompt Sanitization
* **Requirement**: Benchmark case descriptions must not accidentally contain hints revealing the defective line or root-cause signal.
* **Audit Finding**:
  * Inspection of prompt format confirms descriptions are generic (e.g., `"Functional Assertion Failure on hardware module"`).
* **Status**: **PASS (SANITIZED PROMPTS)**

---

### Checkpoint 9: Genuine RTL Structural Disjointness
* **Requirement**: Category B and Category C designs must represent meaningful structural differences from standard canonical sources.
* **Audit Finding**:
  * Category B introduces split always-blocks, one-hot encodings, skid buffers, and decomposed Boolean trees.
  * Category C introduces adversarial defect mechanisms (pointer overflow, reset bounce, framing bit truncation, credit underflow) that deliberately stress the semantic gate.
* **Status**: **PASS (STRUCTURALLY DISJOINT)**

---

## 3. Summary Certification Matrix

| # | Checkpoint | Verification Method | Status |
|---|---|---|---|
| 1 | Target Disjointness | Case ID & Interface Hash Disjointness | **PASS** |
| 2 | Signal Name Variation | Taxonomy Mapping Audit | **PASS** |
| 3 | Zero Prompt Leakage | Context Builder Inspection | **PASS** |
| 4 | Assertion Shielding | Testbench Isolation Check | **PASS** |
| 5 | System A Memory Isolation | Code Call Graph Inspection | **PASS** |
| 6 | System B Gate Control | Verification Confidence Enforcement | **PASS** |
| 7 | Decoupled Patch Synthesis | Syntax & AST Rule Inspection | **PASS** |
| 8 | Prompt Sanitization | Automated Substring Audit | **PASS** |
| 9 | Structural Disjointness | AST Complexity & Token Diff Audit | **PASS** |

**Conclusion**: The V11 benchmark and evaluation harness are certified leakage-free and structurally independent.
