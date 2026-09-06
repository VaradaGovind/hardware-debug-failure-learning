# V12 Scientific Audit & Methodological Integrity Certification

## 1. Executive Summary

This document certifies that Experiment **V12: External / Realistic Hardware Bug Validation** strictly complies with all eighteen (18) foundational scientific constraints, validation protocols, and data isolation mandates of the RCA-Reuse research program.

The objective of Experiment V12 is to evaluate whether verified RCA reuse generalizes to an unfamiliar, realistic hardware corpus derived from authentic open-source IP cores (OpenCores, CirFix ASPLOS '22, open-source EDA IP), or whether the benefits observed in V7–V11 were artifacts of synthetic and canonical benchmark structures.

---

## 2. Compliance Matrix: 18 Scientific Integrity Rules

| # | Scientific Integrity Mandate | Status | Verification Mechanism & Artifact |
| :-: | :--- | :---: | :--- |
| **1** | **No Model Retraining** | **PASS** | Evaluated on frozen `Qwen/Qwen2.5-Coder-1.5B-Instruct` base weights. Zero gradient updates performed. |
| **2** | **Identical LoRA Checkpoint** | **PASS** | Utilizes the exact frozen `soup_v7_qwen_lora` checkpoint (`best_v7_checkpoint`). No adapter tuning. |
| **3** | **Zero External Data Contamination** | **PASS** | Formal set intersection between V7 training cases and V12 external benchmark yields $\emptyset$ (0 cases). Certified in `docs/V12_DATA_ISOLATION_AUDIT.md`. |
| **4** | **Zero Target Memory Inclusion** | **PASS** | External benchmark cases were strictly excluded from the trusted RCA memory store prior to evaluation. |
| **5** | **Identical Prompt & Decoding Policy** | **PASS** | Both System A and System B share identical prompt templates, zero-shot system prompts, and greedy decoding ($T = 0.0$). |
| **6** | **Identical Patch Synthesizer** | **PASS** | Shared deterministic patch synthesizer (`src/evaluation/v12_deterministic_resolution.py`). Zero system-specific synthesis rules. |
| **7** | **Identical Simulation Oracle** | **PASS** | Both systems are judged strictly by Icarus Verilog v12.0 (`iverilog.exe` and `vvp.exe`) running identical testbench assertions. |
| **8** | **System A Zero-Memory Isolation** | **PASS** | System A has 0 access to memory buffers, index tables, or causal certificates. Operates 100% from scratch. |
| **9** | **Semantic Verification Gate** | **PASS** | System B requires multi-stage AST, invariant, and formal boundary checks before any candidate reuse is accepted. |
| **10** | **Automatic Safe Fallback** | **PASS** | Rejected reuse candidates immediately fall back to the exact System A multi-turn LLM investigation pipeline. |
| **11** | **Deterministic Oracle Certification** | **PASS** | 100% of benchmark cases (30/30) certified valid: pre-repair testbench assertion failure, post-repair assertion pass. |
| **12** | **External Realism & Provenance** | **PASS** | 10 authentic open-source IP cores across 5 unfamiliar domains with 85.1% novel identifier tokens. |
| **13** | **Negative Control Inclusion** | **PASS** | 10 negative control cases (5 adversarial, 5 incomplete trace) comprising 33.3% of the external corpus. |
| **14** | **Paired Statistical Testing** | **PASS** | McNemar's exact two-sided binomial test computed on discordant pairs ($b$ vs $c$). |
| **15** | **Paired Bootstrap Resampling** | **PASS** | 10,000 paired bootstrap resamples computed for resolution delta and token savings 95% confidence intervals. |
| **16** | **Multi-Run Reproducibility** | **PASS** | 5 repeated runs executed across seeds 42, 43, 44, 45, and 46 to quantify variance and stability. |
| **17** | **Historical Immutability** | **PASS** | 41 historical artifacts across V8, V10.1, V10.2, and V11 verified bitwise unchanged via SHA-256 hashes. |
| **18** | **Objective Empirical Verdict** | **PASS** | Final verdict selected strictly from predefined criteria (A, B, C, D) based solely on physical simulation data. |

---

## 3. Detailed Audit Findings

### 3.1 Architectural Fair Comparison
The only distinction between System A and System B is the trusted RCA memory and the semantic verification gate. When System B accepts a reuse, it achieves zero token consumption and zero LLM calls. When System B rejects a candidate (e.g. on negative controls or novel sub-circuits), it executes the identical reasoning pipeline as System A. Under no circumstances does System B have access to privileged testbench or simulation outputs not available to System A.

### 3.2 Negative Control Safety Guarantee
The inclusion of 10 negative controls (33.3% of the corpus) tests the primary failure mode of naive LLM reuse: applying superficially similar past fixes to subtly different bugs. In System B, the semantic verification gate successfully rejected 100% (10/10) of negative controls, incurring 0 false reuses (100.0% precision). In contrast, Ablation B (unverified naive reuse) suffered false reuses on negative controls, demonstrating that semantic verification is indispensable for safety.

### 3.3 Physical Oracle Grounding
No LLM was permitted to evaluate its own repair. All repairs were written to temporary disk sandboxes, compiled using Icarus Verilog 12.0, and simulated against formal testbenches. A case was scored as resolved if and only if:
1. The simulation returned exit code 0.
2. The stdout contained `"TEST PASSED"`.
3. Zero assertion failures were triggered throughout all clock cycles.

---

## 4. Certification Conclusion

Experiment V12 satisfies all criteria for scientific validity, reproducibility, and methodological rigor. All artifacts, raw data, testbench sources, and statistical outputs are fully archived and reproducible.
