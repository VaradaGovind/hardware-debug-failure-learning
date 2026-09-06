# V12.1 Release Readiness Audit

**Audit Date**: September 6, 2026  
**Auditor**: Antigravity Automated Release Auditor  
**Target Release**: V12.1 (Public Research Repository Release Readiness)  
**Status**: AUDIT COMPLETE — ACTION ITEMS IDENTIFIED  

---

## 1. Executive Summary

This repository audit evaluates the public readiness, reproducibility, scientific rigor, and hygiene of the **RCA-Reuse** repository. The primary objective is to ensure that any experienced hardware or machine learning researcher opening the GitHub repository can rapidly comprehend the verified reuse contribution, verify experimental results, understand benchmark provenance, and reproduce findings without encountering machine-specific path traps or confusing internal scratch artifacts.

---

## 2. Repository Structure Summary

The repository layout comprises the following functional subtrees:

```text
hardware-debug-failure-learning/
├── configs/            # Training configurations and hyperparameters (V6/V7 LoRA)
├── datasets/           # Dataset manifests and descriptions (private training archives excluded)
├── docs/               # Technical documentation, milestone reports, and audits
├── examples/           # Demonstrations of certificate matching and verification
├── experiments/        # Controlled benchmark evaluation runners (V10.1, V10.2, V11, V12)
├── results/            # Experimental records, cost analyses, and frozen reports
│   ├── cost_analysis/  # Token, call, and latency measurements
│   └── reports/        # Canonical JSON evaluation reports and benchmark manifests
├── rtl/                # Verilog modules, testbenches, and multi-domain evaluation circuits
│   ├── designs/        # Historical V6–V8 designs
│   ├── testbenches/    # Historical V6–V8 testbenches
│   └── v12/            # 30-case external / realistic benchmark circuits and testbenches
├── scripts/            # Benchmark generators, dataset construction, and evaluation utilities
├── src/                # Core Python package (rca_reuse)
│   ├── agent/          # LLM prompt templates and client drivers
│   ├── evaluation/     # Deterministic resolution evaluators and patch synthesizers
│   ├── reuse/          # Certificate schema, role normalizer, and verification gate
│   └── tools/          # Icarus Verilog simulation and waveform inspection tools
├── tests/              # Pytest verification suites (100 passed, 11 skipped, 0 failures)
└── scratch/            # Development scratchpad, novelty scanners, and integrity checkers
```

---

## 3. Identified Release Blockers

### Blocker 1: Overly Aggressive `.gitignore` Masking Valid RTL
* **Issue**: `.gitignore` line 117 specifies `*token*` under `# Secrets and credentials`.
* **Impact**: This rule unintentionally ignored the Round-Robin Token Arbiter benchmark files:
  - `rtl/v12/v12_arb_rr_token.v`
  - `rtl/v12/v12_arb_rr_token_tb.v`
* **Remediation**: Refine the pattern in `.gitignore` to match security tokens specifically (e.g., `*api_token*`, `*secret_token*`, `*auth_token*`) without masking architectural hardware tokens.

### Blocker 2: `.gitignore` Masking Evaluation Reports and Test Suites
* **Issue**: `.gitignore` contained legacy rules from early V8 development (`/results/*`, `docs/*V10*`, `tests/test_v10*`, `scripts/*v10*`) intended to shield internal milestones during active development.
* **Impact**: Key JSON reports in `results/reports/` (such as `v11_master_report.json` and `v12_master_report.json`), as well as V10 test suites, were excluded from git tracking.
* **Remediation**: Update `.gitignore` to explicitly allow tracking of all JSON and Markdown reports in `results/reports/`, all test files in `tests/`, all docs in `docs/`, and benchmark manifests while maintaining strict exclusion of raw waveform dumps (`*.vcd`, `*.vvp`) and virtual environments (`.venv/`).

### Blocker 3: Top-Level README Out of Date (Frozen at V8)
* **Issue**: The current root `README.md` documents only up to Milestone V8 (25-case toy stream). It makes no mention of the statistical expansion in V11 ($N=100$) or the external realistic validation in V12 ($N=30$).
* **Impact**: A visiting researcher would assume the project stopped at V8 without peer-scale statistical testing or external hardware validation.
* **Remediation**: Rewrite `README.md` to reflect V12.1, highlighting V11 and V12 results, architecture, safety gating, and reproducibility.

### Blocker 4: Missing High-Level Research Results & Reproducibility Guides
* **Issue**: Key research findings and reproduction instructions are scattered across multiple milestone markdown files in `docs/`.
* **Remediation**: Create top-level `RESULTS.md` and `REPRODUCIBILITY.md` for fast onboarding.

---

## 4. Reproducibility Blockers

### Blocker 1: Python Environment & Pytest Invocation
* **Issue**: If `pytest` is invoked directly from a system shell where the virtual environment is not active in PATH, command execution fails with `CommandNotFoundException`.
* **Remediation**: Explicitly document `python -m pytest -q` or `.venv\Scripts\python -m pytest -q` in `REPRODUCIBILITY.md`.

### Blocker 2: Hardware Simulator Dependency
* **Issue**: Full end-to-end evaluation requires Icarus Verilog (`iverilog` and `vvp`). While unit tests handle missing simulators gracefully by skipping simulation-dependent assertions, researchers need clear instructions on simulator prerequisites.
* **Remediation**: Document simulator requirements and offline replay capabilities clearly in `REPRODUCIBILITY.md`.

---

## 5. Machine-Specific Artifact & Path Audit

An automated search across all repository files identified several absolute paths and local references:

1. **Local Model Cache Paths in Historical Runners**:
   - `experiments/run_v10_1_plain_llm_rca.py` (lines 37, 206):  
     `default="C:/Users/varad/ml-cache/rca-reuse/v7/checkpoints/soup_v7_qwen_lora/best_v7_checkpoint"`
   - `experiments/run_v10_1_llm_reuse_rca.py` (lines 44, 365):  
     `default="C:/Users/varad/ml-cache/rca-reuse/v7/checkpoints/soup_v7_qwen_lora/best_v7_checkpoint"`
   - `experiments/run_v10_1_controlled_experiment.py` (lines 136, 443):  
     `default="C:/Users/varad/ml-cache/rca-reuse/v7/checkpoints/soup_v7_qwen_lora/best_v7_checkpoint"`
   - *Status*: These are frozen historical artifacts subject to SHA-256 hash checks in `results/reports/v12_frozen_artifacts.json`. Modifying them in-place would invalidate frozen hashes.
   - *Resolution*: Leave historical runners intact to preserve bitwise immutability. Ensure modern runners (`run_v11_generalization.py` and `run_v12_external_validation.py`) use strictly relative paths (`os.path.join(WORKSPACE_ROOT, ...)`), and provide environment variable/CLI override documentation in `REPRODUCIBILITY.md`.

2. **Absolute File URI Links in Historical Documentation**:
   - `docs/V11_*.md` and `docs/V12_*.md` contain IDE-generated links formatted as `file:///c:/Users/varad/...`.
   - *Resolution*: Public documentation (`README.md`, `RESULTS.md`, `REPRODUCIBILITY.md`, `docs/BENCHMARK_PROVENANCE.md`, `docs/ARCHITECTURE.md`) must exclusively use clean, relative Markdown links (e.g., `[results/reports/v12_master_report.json](results/reports/v12_master_report.json)`).

---

## 6. Scratch & Development Artifacts Audit

The `scratch/` directory contains 16 files and 1 subdirectory:

| File / Subdirectory | Purpose | Recommended Action |
| :--- | :--- | :--- |
| `scratch/calculate_novelty_metrics.py` | Calculates V12 lexical novelty and Jaccard metrics. | **Promote to `scripts/calculate_novelty_metrics.py`**. |
| `scratch/check_integrity.py` | Verifies SHA-256 integrity of frozen historical artifacts. | **Promote to `scripts/check_integrity.py`**. |
| `scratch/test_formatting.py` | Temporary formatting check script. | Retain in scratch (ignored by git). |
| `scratch/release_execution.log` | Development execution log. | Retain in scratch (ignored by git). |
| `scratch/run_release_commits.ps1` | Scratch commit automation script. | Retain in scratch (ignored by git). |
| `scratch/test_isolation_a.json` | Temporary evaluation sandbox output. | Retain in scratch (ignored by git). |
| `scratch/v10_2_run_*` | Intermediate seed outputs from V10.2. | Retain in scratch (ignored by git). |
| `scratch/v11_sandbox/` | Temporary simulation workspace for V11. | Retain in scratch (ignored by git). |

---

## 7. Recommended Cleanup Actions

1. **Promote Scripts**: Move `calculate_novelty_metrics.py` and `check_integrity.py` to `scripts/` with proper docstrings and relative path resolution.
2. **Update `.gitignore`**:
   - Change `*token*` to specific credential tokens.
   - Whitelist `results/reports/` for JSON and MD files.
   - Allow tracking of `tests/`, `docs/`, `rtl/v12/`, `scripts/`, and `experiments/`.
3. **Generate Release Documentation**:
   - `README.md` (Top-level public face)
   - `RESULTS.md` (Detailed research numbers)
   - `REPRODUCIBILITY.md` (Step-by-step reproduction instructions)
   - `docs/BENCHMARK_PROVENANCE.md` (Scientific origin of benchmarks)
   - `docs/ARCHITECTURE.md` (System design and safety principles)
   - `docs/RELEASE_V12_1.md` (Release changelog)
   - `docs/V12_1_COMMIT_PLAN.md` (Commit organization)
   - `docs/V12_1_RELEASE_READINESS.md` (Final scorecard)
