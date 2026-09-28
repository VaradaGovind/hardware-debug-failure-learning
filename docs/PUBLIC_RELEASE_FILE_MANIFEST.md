# Public Release File Manifest

**Repository**: `hardware-debug-failure-learning`  
**Release Tag**: `v12.1.0`  
**Date**: September 2026  

---

## 1. Public Release Files (Committed / Tracked in Git)

### Root Documentation & Configuration
* `README.md`: Public-facing project overview, motivation, architecture, results table, lessons learned, and limitations.
* `RESULTS.md`: Detailed empirical breakdown of V8, V10.1, V10.2, V11, and V12.
* `REPRODUCIBILITY.md`: Portable reproduction steps, requirements, test commands, and expected outputs.
* `CITATION.cff`: Citation metadata file (CFF 1.2.0).
* `LICENSE`: MIT License (Varada Govind Aakula).
* `SECURITY.md`: Responsible security disclosure policy.
* `CONTRIBUTING.md`: Contribution guidelines.
* `pyproject.toml`: Build-system configuration and package metadata.
* `requirements.txt`: Python package requirements.
* `.gitignore`: Rules for excluding caches, checkpoints, build artifacts, and simulator binaries.

### Documentation (`docs/`)
* `docs/ARCHITECTURE.md`: In-depth architectural decomposition, component contracts, and safety gating principles.
* `docs/BENCHMARK_PROVENANCE.md`: Origin, adaptation, and validation of benchmark IP (OpenCores, CirFix ASPLOS '22, open-source EDA IP).
* `docs/PUBLIC_RELEASE_AUDIT.md`: Pre-release repository audit, security scan, and file classification.
* `docs/PUBLIC_RELEASE_FILE_MANIFEST.md`: Complete classification of public vs. excluded repository assets.
* `docs/PUBLIC_GITHUB_RELEASE_REPORT.md`: Final release readiness report.
* `docs/V11_GENERALIZATION_AND_STATISTICAL_EVALUATION.md`: Comprehensive V11 evaluation report.
* `docs/V12_EXTERNAL_GENERALIZATION_REPORT.md`: Comprehensive V12 external validation report.
* `docs/V12_STRUCTURAL_NOVELTY_AUDIT.md`: Lexical novelty and identifier divergence analysis.
* Historical reports, audits, and scientific records (Milestones V6–V12).

### Core Library (`src/`)
* `src/agent/`: Prompt builders and LLM client orchestration.
* `src/constraints/`: Structural hardware constraint models.
* `src/credit/`: Credit assignment and multi-turn contribution scoring.
* `src/evaluation/`: Deterministic patch synthesizers and assertion resolution engines (V10, V11, V12).
* `src/mining/`: Trace pattern mining and causal anomaly extractors.
* `src/reporting/`: Telemetry logging and result formatting.
* `src/reuse/`: Semantic certificate schemas, certificate store, role normalizers, and safety gates.
* `src/tools/`: Icarus Verilog simulation interfaces and waveform parsers.
* `src/trajectory/`: Execution trajectory logging and state tracking schemas.

### Hardware RTL & Testbenches (`rtl/`)
* `rtl/designs/`: Canonical RTL implementations across 5 families (FIFO, AXI, FSM, UART, Pipeline).
* `rtl/bugs/`: Seed defect instances and injected bug variations.
* `rtl/testbenches/`: Self-checking Verilog testbenches with assertion monitors.
* `rtl/v12/`: External realistic RTL circuits and testbenches spanning 5 domains (SDRAM, I2C, SPI, Arbiter, DMA, SHA-3).

### Benchmark Builders & Auditing Tools (`scripts/`)
* `scripts/build_v11_benchmark.py`: Constructs 100-case canonical benchmark.
* `scripts/build_v12_external_benchmark.py`: Constructs 30-case external benchmark.
* `scripts/calculate_novelty_metrics.py`: Computes lexical novelty and Jaccard divergence.
* `scripts/check_integrity.py`: Validates bitwise hash integrity of 41 frozen evaluation artifacts.
* Historical training, verification, and transition auditing scripts.

### Controlled Experiment Runners (`experiments/`)
* `experiments/run_v11_generalization.py`: Master runner for V11 canonical benchmark ($N=100$).
* `experiments/run_v12_external_validation.py`: Master runner for V12 external benchmark ($N=30$).
* Historical milestone experiment runners (V6–V10.2).

### Automated Regression Test Suite (`tests/`)
* 15 pytest suites verifying certificate stores, safety properties, deterministic patching, data isolation, and historical immutability.

### Version-Controlled Results (`results/`)
* `results/reports/`: Machine-readable JSON evaluation reports, manifests, and statistical outputs (`v11_master_report.json`, `v12_master_report.json`, etc.).
* `results/cost_analysis/`: Token, call, and latency measurement summaries (CSV and JSON).

---

## 2. Private / Excluded Assets (Ignored via `.gitignore`)

| Category | File Pattern / Directory | Rationale |
| :--- | :--- | :--- |
| **Model Checkpoints** | `checkpoints/`, `*.safetensors`, `*.bin`, `*.pt`, `training/checkpoints/` | Large binary model weights; reproducible via open weights + configs. |
| **Local Model Caches** | `ml-cache/`, `~/.cache/rca-reuse/` | Local Hugging Face / training caches. |
| **Virtual Environments** | `.venv/`, `venv/`, `env/` | Machine-specific Python environments. |
| **Python Bytecode** | `__pycache__/`, `*.pyc` | Compiled bytecode. |
| **Test & IDE Caches** | `.pytest_cache/`, `.vscode/`, `.idea/` | Local IDE state and test caches. |
| **Build Artifacts** | `build/`, `dist/`, `*.egg-info/` | Setuptools intermediate build files. |
| **Simulation Binaries** | `rtl/*.vcd`, `rtl/*.vvp`, `simv*`, `work/` | Transient waveform dumps and compiled Verilog binaries. |
| **Transient Sandboxes** | `scratch/` | Temporary simulation run directories. |
| **Raw Training Datasets** | `datasets/v9/`, `datasets/v10/` (>19 MB JSON files) | Large intermediate JSONs; only `datasets/README.md` is committed. |
| **Secrets & Keys** | `.env`, `*.pem`, `*.key`, `*api_key*` | Guarded against accidental secret leakage. |
