# RCA-Reuse: Reproducibility Protocol & User Guide

This guide provides step-by-step instructions for reproducing all experimental results, validation suites, and statistical analyses reported in the **RCA-Reuse** repository.

---

## 1. System Requirements & Environment

### Python Environment
* **Python Version**: Python 3.10, 3.11, or 3.12 (developed and tested on Python 3.12).
* **Package Manager**: `pip` (standard).
* **Virtual Environment**: Strongly recommended (`venv`).

### Core Dependencies
The package dependencies declared in `requirements.txt` and `pyproject.toml` include:
* `numpy>=1.24.0` (Numerical routines, bootstrap resampling)
* `scipy>=1.10.0` (Statistical distributions, McNemar exact tests)
* `pandas>=2.0.0` (Dataframe manipulation, telemetry aggregation)
* `matplotlib>=3.7.0` (Plot generation and visualization)
* `pyvcd>=0.4.0` (Value Change Dump parsing for hardware waveform traces)
* `scikit-learn>=1.2.0` (Metrics and token evaluation)
* `pytest>=7.0.0` (Automated regression testing)

### Hardware Simulator Prerequisite
* **Simulator**: **Icarus Verilog** (`iverilog` and `vvp`), version 12.0 or later.
* **Simulator Purpose**: Compiles RTL sandboxes, executes simulation testbenches, and evaluates formal assertion verifiers.
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
    Download the installer from [Bleyer Icarus Verilog for Windows](https://bleyer.org/icarus/) or install via Chocolatey:
    ```powershell
    choco install icarus-verilog
    ```
    Ensure `iverilog.exe` and `vvp.exe` are accessible on your system `PATH`.

---

## 2. Installation & Quickstart

```bash
# 1. Clone the repository
git clone https://github.com/VaradaGovind/hardware-debug-failure-learning.git
cd hardware-debug-failure-learning

# 2. Create and activate a clean virtual environment
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Or on Windows (Command Prompt):
# .venv\Scripts\activate.bat

# 3. Upgrade pip and install package in editable development mode
python -m pip install --upgrade pip
pip install -e .
pip install pytest scipy
```

---

## 3. Running the Regression Test Suite

The test suite validates schema integrity, deterministic patch synthesis, data isolation, negative control safety, and historical artifact immutability.

```bash
# Run the full regression test suite (100 passed, 11 skipped, 0 failures)
python -m pytest -q

# Run V11 Generalization integrity tests specifically
python -m pytest tests/test_v11_generalization.py -v

# Run V12 External Validation integrity tests specifically
python -m pytest tests/test_v12_external_validation.py -v

# Run V10.1 & V10.2 Bug Resolution and Reproducibility tests
python -m pytest tests/test_v10_1_bug_resolution.py tests/test_v10_2_reproducibility.py -v
```

*Note: 11 tests are skipped under offline testing when local fine-tuned model weight checkpoints or live simulation sandboxes are not loaded in memory.*

---

## 4. Reproducing Benchmark Evaluations

### Reproducing Experiment V11 ($N=100$)
Executes the controlled evaluation comparing System A (Plain LLM) vs. System B (Verified Reuse) on the expanded 100-case canonical corpus across 5 hardware families (FIFO, AXI, FSM, UART, Pipeline):

```bash
python experiments/run_v11_generalization.py
```

**Expected Primary Output**:
* Console summary of System A (40.0%) vs. System B (48.0%), token reduction (42.64%), and McNemar exact test ($p = 0.007812$).
* Generated reports in `results/reports/`:
  * `v11_master_report.json`
  * `v11_case_level_results.json`
  * `v11_transition_analysis.json`
  * `v11_statistical_analysis.json`
  * `v11_repeated_runs.json`

### Reproducing Experiment V12 ($N=30$)
Executes the controlled evaluation on 30 external, unfamiliar hardware IP cases across 5 domains (Memory Controllers, Bus Protocols, Arbitration, DMA, Crypto/Arithmetic):

```bash
python experiments/run_v12_external_validation.py
```

**Expected Primary Output**:
* Console summary of System A (16.67%) vs. System B (43.33%), token reduction (36.67%), McNemar exact test ($p = 0.007812$), and 10,000 paired bootstrap analysis.
* Generated reports in `results/reports/`:
  * `v12_master_report.json`
  * `v12_case_level_results.json`
  * `v12_transition_analysis.json`
  * `v12_statistical_analysis.json`
  * `v12_repeated_runs.json`

---

## 5. Benchmark Reconstruction & Audits

### Rebuilding Benchmark Corpi
Both benchmarks are constructed deterministically from specification scripts:

```bash
# Rebuild the 100-case V11 canonical benchmark
python scripts/build_v11_benchmark.py

# Rebuild the 30-case V12 external realistic benchmark
python scripts/build_v12_external_benchmark.py
```

### Running Lexical Novelty & Divergence Scanner
Computes the token and identifier overlap between historical designs (V7–V11) and the V12 external benchmark:

```bash
python scripts/calculate_novelty_metrics.py
```
*Expected Output*: 80 / 94 novel identifiers (85.1%), Jaccard token similarity 0.0524 (94.8% lexical divergence).

### Running Historical Artifact Immutability Audit
Verifies that all 41 pre-registered historical files remain bitwise unchanged:

```bash
python scripts/check_integrity.py
```
*Expected Output*: 41 files verified, 0 mismatches (`all_verified: True`).

---

## 6. Determinism & Statistical Guarantees

All reported experiments adhere to strict determinism standards:
1. **Greedy Decoding**: Temperature $T = 0.0$ and top-p = 1.0 eliminate token sampling stochasticity.
2. **Deterministic Patch Synthesizer**: Unified diff generation follows deterministic rule-based replacement from AST and diagnosis objects.
3. **Multi-Seed Stability**: Evaluations were repeated across 5 distinct random seeds (`42, 43, 44, 45, 46`). Standard deviation across runs is $\sigma = 0.000$.
4. **Offline Replay**: Pre-computed evaluation reports are checked into `results/reports/` and verified by automated unit tests so that researchers without local GPU clusters can verify all metrics and statistical tests immediately upon cloning.
