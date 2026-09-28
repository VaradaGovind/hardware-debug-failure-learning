# Public Release Audit & Repository Inventory

**Repository**: `hardware-debug-failure-learning`  
**Remote**: `https://github.com/VaradaGovind/hardware-debug-failure-learning.git`  
**Date**: September 2026  
**Auditor**: Public Release Audit Suite  
**Target Release**: v12.1.0  

---

## 1. Executive Summary

This audit assesses the readiness of the `hardware-debug-failure-learning` repository for public release on GitHub as a student-built research project. The project explores verified root-cause analysis (RCA) reuse in hardware debugging, contrasting plain LLM RCA against verified LLM-reuse RCA.

The codebase is technically sound, cleanly partitioned, and has verified regression test suites (100 passed, 11 offline cache skipped). No committed secrets, API keys, or oversized binaries (>25 MB) were found. Historical research documents have been preserved for scientific immutability.

---

## 2. Directory & File Inventory

### Core Source Code (Keep)
* `src/`: Complete library code for RCA agent orchestration, deterministic patch synthesis, semantic certificate verification, role normalizers, and waveform analysis.
* `rtl/`: Verilog RTL circuits and self-checking testbenches across canonical families (`rtl/designs/`, `rtl/bugs/`, `rtl/testbenches/`) and external realistic IP (`rtl/v12/`).
* `scripts/`: Benchmark generators (`build_v11_benchmark.py`, `build_v12_external_benchmark.py`), integrity checkers (`check_integrity.py`), and lexical novelty analyzers (`calculate_novelty_metrics.py`).
* `tests/`: 15 pytest suites covering unit, schema, boundary, and regression tests for milestones V6 through V12.
* `experiments/`: Historical and master evaluation runners (`run_v11_generalization.py`, `run_v12_external_validation.py`, etc.).

### Public Research & Documentation Materials (Keep)
* `README.md`: Public-facing project overview, technical architecture, results, and student reflection.
* `RESULTS.md`: Detailed empirical breakdown of V8, V10.1, V10.2, V11, and V12.
* `REPRODUCIBILITY.md`: Portable reproduction steps, requirements, test commands, and expected outputs.
* `docs/`: In-depth architectural specifications (`ARCHITECTURE.md`), benchmark provenance (`BENCHMARK_PROVENANCE.md`), and historical milestone reports (V6–V12).
* `results/reports/`: Version-controlled machine-readable JSON evaluation reports, manifests, and statistical analysis outputs.
* `results/cost_analysis/`: Token, call, and cost evaluation summaries.
* `CITATION.cff`: Citation metadata for the project.
* `LICENSE`: MIT License (Varada Govind Aakula).

### Machine-Specific & Local Cache Files (Exclude / Ignore)
* `.venv/`, `venv/`: Local virtual environments.
* `__pycache__/`, `*.pyc`: Compiled Python bytecode.
* `.pytest_cache/`: Pytest internal cache.
* `build/`, `*.egg-info/`: Local setuptools build artifacts.
* `scratch/`: Transient simulator workspaces and temporary sandbox testbenches.
* `rtl/*.vcd`, `rtl/*.vvp`: Simulator waveform dumps and compiled Verilog binaries generated during local runs.
* `datasets/v9/`, `datasets/v10/`: Large raw training datasets (e.g., `agentic_train_v10.json`, ~19.3 MB). Only `datasets/README.md` is tracked.
* `checkpoints/`, `ml-cache/`: Local fine-tuned LoRA weights and model caches.

---

## 3. Security & Secret Scan

A scan was performed across the repository for sensitive tokens and credentials:
* **API Keys & Tokens (`sk-`, `AKIA`, `api_key`, `token`)**: Zero active credentials found. Occurrences of "token" correspond strictly to architectural hardware tokens (e.g., round-robin token arbiter) or security advisory statements in `SECURITY.md`.
* **Passwords & Private Keys (`password`, `secret`, `*.pem`, `*.key`)**: Zero occurrences. Only referenced in standard security policy text.
* **Environment Files (`.env`)**: No `.env` files present. Environment variable lookups in code (`os.environ.get`) use portable fallbacks (e.g., `RCA_REUSE_CACHE_DIR`).

---

## 4. Large File Analysis (>25 MB)

* **Files > 25 MB**: None detected across the entire repository.
* **Files > 5 MB**:
  * `datasets/v10/agentic_train_v10.json` (19.3 MB) — Excluded from Git via `.gitignore` (`/datasets/*` rule).
  * `datasets/v9/agentic_train_v9.json` (5.7 MB) — Excluded from Git via `.gitignore`.
* **Git Tracked Footprint**: Kept lightweight; only code, manifests, summaries, and documentation are committed.

---

## 5. Benchmark Provenance & Realism Audit

* **Upstream Heritage**: Benchmark V12 incorporates circuit designs derived from established open-source projects (OpenCores, CirFix ASPLOS '22 artifacts, open-source EDA IP) spanning 5 domains: Memory Controllers, Bus Protocols, Arbitration, DMA, and Crypto/Arithmetic.
* **Nature of Bug Instances**: Benchmark instances represent machine-validated bug instances modeled after structural RTL defect patterns, standardized for single-file deterministic simulation in Icarus Verilog. They are **not** raw unedited commits scraped directly from commercial issue trackers.
* **Licensing Compliance**: Upstream cores are under permissive open-source licenses (MIT, BSD, Apache-2.0, LGPL). Attribution and domain provenance are documented at the top of each `rtl/v12/` file and detailed in `docs/BENCHMARK_PROVENANCE.md`.

---

## 6. Reproducibility & Environment Audit

* **Simulator Dependency**: Full simulation requires Icarus Verilog (`iverilog` and `vvp`). The codebase checks `C:\iverilog\bin` and system `PATH`.
* **Offline Verification**: All statistical and metric analyses can be verified offline via checked-in evaluation manifests in `results/reports/` without requiring local GPU retraining or live simulation runs.
* **Test Suite Status**: 100 tests pass unconditionally. 11 tests skip gracefully when offline training cache files (`~/.cache/rca-reuse`) are absent.
* **Portability**: Hardcoded absolute paths in `training/README.md` and user-facing guides must be replaced with portable relative paths or environment variables.

---

## 7. Public Release Action Plan

1. **Clean Documentation**:
   * Ensure `README.md` has an authentic student voice: personal motivation, concise technical explanations, clear architecture diagram, results table, honest lessons learned, and limitations.
   * Format `RESULTS.md` with explicit sections for V8, V10.1, V10.2, V11, and V12.
   * Update `REPRODUCIBILITY.md` with portable instructions.
   * Add `CITATION.cff` with verified author and remote repository information.
2. **Path Sanitization**:
   * Replace any machine-specific paths in `training/README.md` and public guides with portable commands.
3. **Validation & Tagging**:
   * Execute test suite to confirm 100% pass on all regression tests.
   * Review Git staging to ensure zero private or transient files are included.
   * Prepare tag `v12.1.0`.
   * Report release readiness and public visibility status.
