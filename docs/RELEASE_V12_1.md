# RCA-Reuse V12.1 Release Notes

**Release Identifier**: `v12.1.0`  
**Release Date**: September 6, 2026  
**Focus**: Public Research Repository Release Readiness, Documentation Hygiene, and Reproducibility  

---

## 1. Release Purpose

Milestone **V12.1** prepares the RCA-Reuse research repository for its first serious public GitHub release. Following the completion and empirical validation of Experiments V11 ($N=100$) and V12 ($N=30$), this release ensures that external researchers, peer reviewers, and electronic design automation (EDA) practitioners can:
1. Understand the core scientific contribution within minutes from the top-level documentation.
2. Verify empirical results directly from machine-checked reports.
3. Review transparent provenance documentation for all evaluation circuits.
4. Reproduce test suites and experiments using clean, portable workflows free of machine-specific environment traps.

---

## 2. Research Highlights

* **Generalization on Expanded Canonical Corpus (V11, $N=100$)**:
  * Demonstrated statistically significant resolution gains (+8.0% absolute, +20.0% relative, McNemar $p = 0.007812$).
  * Reduced LLM inference token consumption by 42.64% and calls by 42.0%.
* **Generalization on External Realistic IP (V12, $N=30$)**:
  * Tested across 5 unfamiliar hardware domains (Memory Controllers, Bus Protocols, Arbitration, DMA, Crypto/Arithmetic) with 85.1% novel identifier tokens and 94.8% lexical divergence.
  * System B resolved 43.33% (13/30) vs. System A's 16.67% (5/30), representing an absolute improvement of +26.67% (+160.0% relative, McNemar $p = 0.007812$).
* **Rigorous Safety & Gating Verification**:
  * Maintained **zero false reuses** (100.0% precision) across 53 applied reuses.
  * Successfully rejected 100% of negative control cases (30/30 in V11, 10/10 in V12).
* **Physical Machine Grounding**:
  * 100% of repairs compiled and verified in physical simulation using Icarus Verilog v12.0 testbench assertions.

---

## 3. Key Results Summary

| Benchmark | System A (Plain LLM) | System B (Verified Reuse) | Absolute Delta | Token Savings | McNemar $p$ | False Reuses | Negative Rejection |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **V11 Benchmark** ($N=100$) | 40.0% (40/100) | **48.0% (48/100)** | **+8.0%** | **42.64%** | **$p = 0.007812$** | **0** | **100% (30/30)** |
| **V12 External** ($N=30$) | 16.67% (5/30) | **43.33% (13/30)** | **+26.67%** | **36.67%** | **$p = 0.007812$** | **0** | **100% (10/10)** |

---

## 4. Test Suite & Validation Status

The regression suite was verified prior to release:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\varad\Documents\Coding\Debugging\hardware-debug-failure-learning
configfile: pyproject.toml
testpaths: tests
collected 111 items

tests/test_adaptive_boundary.py ............                             [ 10%]
tests/test_agentic_rca.py ........                                       [ 18%]
tests/test_certificate_store.py ......                                   [ 23%]
tests/test_rca_vs_reuse_harness.py ....                                  [ 27%]
tests/test_safety_properties.py .........                                [ 35%]
tests/test_source_rca_verifier.py .......                                [ 41%]
tests/test_v10_1_bug_resolution.py .......                               [ 47%]
tests/test_v10_2_reproducibility.py ........                             [ 54%]
tests/test_v10_quality_and_schema.py ....                                [ 58%]
tests/test_v11_generalization.py .............                           [ 70%]
tests/test_v12_external_validation.py ............                       [ 81%]
tests/test_v6_dataset_and_pipeline.py ssss                               [ 84%]
tests/test_v7_dataset_and_pipeline.py sssss                              [ 89%]
tests/test_v8_generalization.py ss                                       [ 90%]
tests/test_v8_unit.py ...........                                        [100%]

======================== 100 passed, 11 skipped in 21.96s =======================
```

* **Passed**: 100 tests certifying schema validity, memory isolation, testbench determinism, and negative control safety.
* **Skipped**: 11 offline tests requiring live local GPU model weight caches.
* **Failed**: 0 failures.

---

## 5. What Changed in V12.1

### Documentation & Reporting Additions
* **[README.md](../README.md)**: Completely rewritten to introduce V12.1, problem motivation, Mermaid architecture, unified results, and scientific controls.
* **[RESULTS.md](../RESULTS.md)**: Detailed empirical report compiling progression tables, confidence intervals, bootstrap analyses, and family breakdowns.
* **[REPRODUCIBILITY.md](../REPRODUCIBILITY.md)**: Step-by-step reproduction guide with portable CLI commands.
* **[docs/BENCHMARK_PROVENANCE.md](BENCHMARK_PROVENANCE.md)**: Comprehensive origin and realism audit of V11 and V12 benchmarks.
* **[docs/ARCHITECTURE.md](ARCHITECTURE.md)**: Full architectural specification detailing memory schemas, semantic gating, and safety principles.
* **[docs/V12_1_RELEASE_AUDIT.md](V12_1_RELEASE_AUDIT.md)**: Initial release audit cataloging repository structure and blockers.
* **[docs/V12_1_COMMIT_PLAN.md](V12_1_COMMIT_PLAN.md)**: Structured commit organization.

### Tooling & Repository Organization
* **Promoted Scripts**: Promoted `calculate_novelty_metrics.py` and `check_integrity.py` from `scratch/` into `scripts/` with relative path handling and docstrings.
* **Refined `.gitignore`**: Fixed over-broad `*token*` rule that masked `rtl/v12/v12_arb_rr_token.v`; allowed tracking of reports in `results/reports/`, tests, docs, and scripts; excluded raw simulation dumps and virtual environments.

### Immutability Guarantees
* **No experimental results modified**: All historical metrics in `results/` remain untouched.
* **No models retrained**: Weights and training configs remain frozen.
* **No benchmarks altered**: V11 and V12 RTL and testbenches remain byte-identical.
* **No System A/B logic modified**: Core agent and gating algorithms remain unchanged.
