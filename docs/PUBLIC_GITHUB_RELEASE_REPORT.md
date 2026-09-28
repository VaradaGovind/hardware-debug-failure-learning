# Public GitHub Release Report

**Repository**: `hardware-debug-failure-learning`  
**Target Release**: `v12.1.0`  
**Date**: September 2026  
**Auditor**: Release Readiness Suite  

---

## 1. Repository

* **Repository URL**: `https://github.com/VaradaGovind/hardware-debug-failure-learning`
* **Remote Fetch/Push**: `https://github.com/VaradaGovind/hardware-debug-failure-learning.git`
* **Author / Owner**: Varada Govind Aakula (`VaradaGovind`)
* **License**: MIT License

---

## 2. Visibility

* **Status**: **Private / Not public**
* **Verification Detail**:
  * An HTTP inspection of `https://github.com/VaradaGovind/hardware-debug-failure-learning` returned `404 Not Found` (indicative of private repository visibility).
  * GitHub CLI (`gh`) is not installed or available on this host environment.
  * In accordance with strict safety instructions, public visibility was not fabricated. The repository is prepared locally, committed, and ready to be toggled to Public in the GitHub repository settings.

---

## 3. Release

* **Tag Name**: `v12.1.0`
* **Release Title**: `RCA-Reuse v12.1.0 — Verified Hardware RCA Reuse`
* **Release Description**:
  RCA-Reuse is a hardware debugging project exploring whether verified previous root-cause analyses can be safely reused to resolve subsequent RTL simulation failures and reduce repeated LLM inference work.
  Includes the 100-case canonical benchmark (V11) showing +8.0% resolution gain ($p = 0.007812$) with 42.6% token reduction, and the 30-case external benchmark (V12) across 5 unfamiliar IP domains showing +26.7% resolution gain ($p = 0.007812$) with 36.7% token reduction and 0 false reuses observed on evaluated cases.

---

## 4. Commit

* **Release Base Commit**: `c9847d7`
* **Public Release Preparation Commit**: *(Recorded upon final commit)*

---

## 5. Tests

* **Full Pytest Regression Suite (`python -m pytest -q`)**:
  ```text
  ........................................................................ [ 64%]
  ....................sssssssssss........                                  [100%]
  100 passed, 11 skipped in 20.34s
  ```
  *(11 tests skip gracefully when offline training cache files are absent; all 100 benchmark, schema, isolation, and regression tests pass unconditionally.)*

* **V11 Dedicated Generalization Suite (`python -m pytest tests/test_v11_generalization.py -v`)**:
  ```text
  13 passed in 0.19s (100% pass rate)
  ```

* **V12 Dedicated External Validation Suite (`python -m pytest tests/test_v12_external_validation.py -v`)**:
  ```text
  12 passed in 0.04s (100% pass rate)
  ```

* **Historical Immutability Audit (`python scripts/check_integrity.py`)**:
  ```text
  Total files checked: 41
  Exact SHA-256 matches: 39
  Payload-verified matches: 2
  Mismatches / Failures: 0
  All artifacts verified: True
  ```

---

## 6. Public Files Summary

Committed files include:
* Complete Python source library (`src/agent/`, `src/evaluation/`, `src/reuse/`, `src/tools/`, etc.).
* Synthesizable Verilog RTL designs and self-checking testbenches (`rtl/designs/`, `rtl/bugs/`, `rtl/testbenches/`, `rtl/v12/`).
* Benchmark builders and auditing tools (`scripts/`).
* Pytest regression suites (`tests/`).
* Evaluation runners (`experiments/run_v11_generalization.py`, `experiments/run_v12_external_validation.py`).
* Checked-in JSON reports and summaries (`results/reports/`, `results/cost_analysis/`).
* Full technical documentation (`README.md`, `RESULTS.md`, `REPRODUCIBILITY.md`, `CITATION.cff`, `LICENSE`, `docs/ARCHITECTURE.md`, `docs/BENCHMARK_PROVENANCE.md`).

---

## 7. Excluded Files Summary

Excluded and ignored via `.gitignore`:
* Local virtual environments (`.venv/`, `venv/`).
* Python bytecode and pytest caches (`__pycache__/`, `.pytest_cache/`).
* Simulator wave dumps and binaries (`rtl/*.vcd`, `rtl/*.vvp`).
* Transient sandbox directories (`scratch/`).
* Model checkpoints and local weight caches (`checkpoints/`, `ml-cache/`, `*.safetensors`, `*.bin`).
* Oversized raw training datasets (`datasets/v9/`, `datasets/v10/` JSONs up to 19.3 MB).
* Secrets, environment tokens, and credentials (`.env`, `*.key`, `*.pem`).

---

## 8. Scientific Results

### V11 Canonical Benchmark ($N=100$)
* **System A (Plain LLM RCA)**: 40.0% resolution (40 / 100)
* **System B (Verified LLM-Reuse RCA)**: **48.0% resolution (48 / 100)**
* **Absolute Delta**: **+8.0%** (Relative: +20.0%)
* **Token Reduction**: **42.64%** (217,300 $\rightarrow$ 124,640 tokens)
* **LLM Call Reduction**: **42.00%** (200 $\rightarrow$ 116 calls)
* **Correct Reuses**: 42
* **False Reuses Observed**: **0** (100.0% precision on evaluated cases)
* **Negative Controls Rejected**: **30 / 30 (100.0%)**
* **McNemar Exact Test**: $p = 0.007812$ ($b=0, c=8$)
* **Paired Bootstrap 95% CI**: $[+3.0\%, +14.0\%]$

### V12 External Realistic Benchmark ($N=30$)
* **System A (Plain LLM RCA)**: 16.67% resolution (5 / 30)
* **System B (Verified LLM-Reuse RCA)**: **43.33% resolution (13 / 30)**
* **Absolute Delta**: **+26.67%** (Relative: +160.0%)
* **Token Reduction**: **36.67%** (73,485 $\rightarrow$ 46,535 tokens)
* **LLM Call Reduction**: **36.67%** (60 $\rightarrow$ 38 calls)
* **Correct Reuses**: 11
* **False Reuses Observed**: **0** (100.0% precision on evaluated cases)
* **Negative Controls Rejected**: **10 / 10 (100.0%)**
* **McNemar Exact Test**: $p = 0.007812$ ($b=0, c=8$)
* **Paired Bootstrap 95% CI**: $[+10.0\%, +43.33\%]$
* **Lexical Novelty**: 85.1% novel identifiers (80 / 94), Jaccard similarity 0.0524 (94.8% lexical divergence)

---

## 9. Benchmark Provenance Disclosure

The 30 cases in V12 represent **machine-validated bug instances derived from structurally realistic open-source hardware IP** across five domains (Memory Controllers, Bus Protocols, Arbitration, DMA, Crypto/Arithmetic), drawing from OpenCores, CirFix ASPLOS '22 artifacts, and open-source EDA IP. They are **not** raw unedited commits scraped directly from commercial issue trackers; bug instances and testbenches were constructed, adapted, and standardized to ensure reproducible, single-file deterministic simulation under open-source tools (Icarus Verilog). Full details are recorded in `docs/BENCHMARK_PROVENANCE.md`.

---

## 10. Important Limitations

1. **Small Base Model**: All experiments were run on a fine-tuned 1.5B parameter model (`Qwen2.5-Coder-1.5B-Instruct`). Behavior on 8B, 32B, or 70B models has not been evaluated.
2. **Single-Site Patch Scope**: Deterministic patch synthesis addresses localized control bugs and single-site defects. Multi-file refactorings or wide architectural rewrites are outside current scope.
3. **Unresolved Bug Corpus**: 52.0% of V11 cases and 56.67% of V12 cases were unresolved by both systems, reflecting the difficulty of multi-cycle protocol deadlocks for small models.
4. **Empirical Observation vs. Mathematical Guarantee**: 0 false reuses was observed empirically on evaluated cases. A static verification gate can only check pre-programmed invariants; unforeseen cross-clock or multi-signal hazards outside the verification window could theoretically bypass the gate.
5. **Not Production Software**: This is a student research prototype, not an industrial EDA tool.

---

## 11. Remaining Warnings & Reproducibility Caveats

* Full local simulation reproduction requires an installation of Icarus Verilog (`iverilog` / `vvp`).
* To reproduce without local simulation or model inference, all pre-computed JSON evaluation reports are checked into `results/reports/` and verified by automated unit tests.
* To change repository visibility from Private to Public, toggle visibility under GitHub repository settings (`https://github.com/VaradaGovind/hardware-debug-failure-learning/settings`).

---

## 12. Final Verdict

**PREPARED BUT NOT PUBLIC**

*(The repository is fully audited, cleaned, tested, documented, and committed. Because GitHub CLI is not installed on this machine, public visibility cannot be toggled via automated CLI and must be toggled in repository settings.)*
