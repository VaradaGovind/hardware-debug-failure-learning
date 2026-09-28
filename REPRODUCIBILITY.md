# Reproducibility Guide

This guide describes how to set up the environment, run the automated test suite, and reproduce the evaluation benchmarks reported in this repository.

---

## Requirements

### Python Environment
* **Python**: Version 3.10, 3.11, or 3.12 (developed and validated on Python 3.12).
* **Package Manager**: Standard `pip`.

### Dependencies
Dependencies declared in `pyproject.toml` and `requirements.txt`:
* `numpy>=1.24.0`
* `scipy>=1.10.0`
* `pandas>=2.0.0`
* `matplotlib>=3.7.0`
* `pyvcd>=0.4.0`
* `scikit-learn>=1.2.0`
* `pytest>=7.0.0`

### Hardware Simulator Prerequisite
* **Icarus Verilog** (`iverilog` and `vvp`), version 12.0 or later.
* **Simulator Role**: Compiles Verilog sandboxes and runs self-checking testbenches with assertion monitors.
* **Installation**:
  * **Ubuntu / Debian**:
    ```bash
    sudo apt-get update && sudo apt-get install -y iverilog
    ```
  * **macOS (Homebrew)**:
    ```bash
    brew install icarus-verilog
    ```
  * **Windows**:
    Download the installer from [Bleyer Icarus Verilog](https://bleyer.org/icarus/) or install via Chocolatey:
    ```powershell
    choco install icarus-verilog
    ```
    Ensure `iverilog` and `vvp` are on your system `PATH` (or located at default `C:\iverilog\bin`).

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/VaradaGovind/hardware-debug-failure-learning.git
cd hardware-debug-failure-learning

# 2. Create and activate a virtual environment
python -m venv .venv

# Linux / macOS:
source .venv/bin/activate

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (Command Prompt):
# .venv\Scripts\activate.bat

# 3. Install dependencies in editable mode
pip install --upgrade pip
pip install -e .
pip install pytest scipy
```

---

## Tests

Run the full pytest suite:

```bash
python -m pytest -q
```
*Expected output*: `100 passed, 11 skipped` in ~20–30s.

*(Note: The 11 skipped tests check local fine-tuning dataset caches that are intentionally excluded from the Git repository. All 100 benchmark, schema, isolation, and regression tests pass unconditionally.)*

### Dedicated Regression Tests
You can also run specific regression suites individually:

```bash
# V11 Generalization tests (13 test points)
python -m pytest tests/test_v11_generalization.py -v

# V12 External Validation tests (12 test points)
python -m pytest tests/test_v12_external_validation.py -v

# V10.1 & V10.2 Bug Resolution and Reproducibility tests
python -m pytest tests/test_v10_1_bug_resolution.py tests/test_v10_2_reproducibility.py -v
```

---

## V11 Reproduction

To run the master evaluation for the 100-case V11 canonical benchmark (FIFO, AXI, FSM, UART, Pipeline):

```bash
python experiments/run_v11_generalization.py
```

### What it does:
1. Loads the 100 canonical benchmark cases across the 5 digital design families.
2. Runs System A (Plain LLM RCA) and System B (Verified LLM-Reuse RCA) across 5 independent passes (seeds 42–46).
3. Compiles and simulates every patched design in Icarus Verilog.
4. Computes exact McNemar $p$-values, 10,000-resample paired bootstrap confidence intervals, Wilson score intervals, and token/call reductions.

### Expected Output Summary:
* System A Resolution: **40/100 (40.0%)**
* System B Resolution: **48/100 (48.0%)**
* Absolute Improvement: **+8.00%** (Relative: +20.0%)
* McNemar Exact $p$-value: **0.007812**
* Token Savings: **42.64%**
* Verified Reuses: **42 correct, 0 false**
* Negative Control Rejection: **30/30 (100.0%)**

---

## V12 Reproduction

To run the master evaluation for the 30-case V12 external benchmark (Memory, Bus, Arbitration, DMA, Crypto/Arithmetic):

```bash
python experiments/run_v12_external_validation.py
```

### What it does:
1. Loads 30 structurally unfamiliar cases derived from open-source IP cores.
2. Evaluates System A, System B, and Ablation B (unverified naive reuse) across 5 seeds.
3. Compiles and simulates each case under Icarus Verilog testbenches.
4. Computes contingency matrix transitions, McNemar test, and paired bootstrap statistics.

### Expected Output Summary:
* System A Resolution: **5/30 (16.7%)**
* System B Resolution: **13/30 (43.3%)**
* Absolute Improvement: **+26.67%** (Relative: +160.0%)
* McNemar Exact $p$-value: **0.007812**
* Token Savings: **36.67%**
* Verified Reuses: **11 correct, 0 false**
* Negative Control Rejection: **10/10 (100.0%)**
* Ablation B False Reuses: **7** (demonstrating why semantic verification is needed)

---

## Auxiliary Benchmark Scripts

```bash
# Verify lexical novelty & Jaccard token divergence of V12
python scripts/calculate_novelty_metrics.py

# Verify historical integrity across all 41 frozen evaluation artifacts
python scripts/check_integrity.py

# Reconstruct canonical V11 and external V12 benchmark manifests
python scripts/build_v11_benchmark.py
python scripts/build_v12_external_benchmark.py
```

---

## Expected Output Files

All experiment outputs, manifests, and statistical reports are saved to:
* `results/reports/v11_master_report.json`
* `results/reports/v11_statistical_analysis.json`
* `results/reports/v11_case_level_results.json`
* `results/reports/v12_master_report.json`
* `results/reports/v12_statistical_analysis.json`
* `results/reports/v12_case_level_results.json`

Detailed qualitative discussions, case studies, and failure analyses are documented in `docs/`:
* `docs/V11_GENERALIZATION_AND_STATISTICAL_EVALUATION.md`
* `docs/V12_EXTERNAL_GENERALIZATION_REPORT.md`
* `docs/BENCHMARK_PROVENANCE.md`

---

## Hardware Environment & Cache Portability

* **Evaluation Hardware**: The models and experiments in this project were developed and evaluated locally on consumer hardware (AMD Ryzen 7 CPU, 16 GB RAM, local Icarus Verilog simulator).
* **Model Inference**: Historical experiments used a fine-tuned 1.5B parameter model (`Qwen2.5-Coder-1.5B-Instruct` with `soup_v7_qwen_lora`). Greedy decoding ($T=0.0$) and rule-based deterministic patch synthesis ensure reproducibility across runs.
* **Cache Directory Override**: Scripts that reference external training or dataset caches read the `RCA_REUSE_CACHE_DIR` environment variable, defaulting to `~/.cache/rca-reuse`:
  ```bash
  # Optional: customize cache location
  export RCA_REUSE_CACHE_DIR="/path/to/local/cache"
  ```
