# Repository Structure Audit & Organization Plan

**Repository**: `hardware-debug-failure-learning`<br/>
**Date**: September 2026<br/>
**Target Quality Level**: High-clarity, student-built open-source hardware/AI research project (comparable to Prolepsis)

---

## 1. Executive Summary

This audit assesses the physical file layout of the repository to balance two critical requirements:
1. **Clean, intuitive navigation**: A student or researcher landing on the repository should immediately understand the layout, how to run tests, where to find RTL designs, and how the experiments are organized.
2. **Strict experimental immutability**: 41 pre-registered historical files (including experiment runners `experiments/run_v10_*.py`, `experiments/run_v11_generalization.py`, evaluation engines, and regression tests) are cryptographically pinned via SHA-256 in `results/reports/v12_frozen_artifacts.json` and validated by automated tests (`test_historical_artifact_immutability`). Moving these files arbitrarily would break cryptographic reproducibility.

Therefore, this audit proposes a clean, logical organization that maintains exact path compatibility for all frozen artifacts while eliminating stale empty directories and clarifying documentation.

---

## 2. File & Directory Classification

### KEEP (Essential Public Assets)
* **Root Configuration & Metadata**:
  * `README.md`: Polished, student-made project documentation modeled after the visual structure of Prolepsis.
  * `RESULTS.md`: Master experimental results across V8, V10.1, V10.2, V11, and V12.
  * `REPRODUCIBILITY.md`: Step-by-step reproduction instructions and commands.
  * `LICENSE`: MIT License.
  * `CITATION.cff`: Citation metadata.
  * `pyproject.toml` & `requirements.txt`: Python package dependency declarations.
  * `SECURITY.md` & `CONTRIBUTING.md`: Open-source project policies.
  * `.gitignore`: Thorough exclusion rules for simulator dumps, weights, and caches.
* **Core RTL (`rtl/`)**:
  * `rtl/designs/`: Canonical RTL implementations across 5 families (FIFO, AXI, FSM, UART, Pipeline).
  * `rtl/bugs/`: Buggy variant designs used in benchmark construction.
  * `rtl/testbenches/`: Self-checking simulation testbenches.
  * `rtl/v12/`: 30 external realistic Verilog implementations spanning 5 domains (SDRAM, I2C, SPI, Arbiter, DMA, SHA-3) with explicit open-source license attribution.
* **Source Code (`src/`)**:
  * `src/agent/`: Prompt construction and LLM orchestration.
  * `src/evaluation/`: Deterministic patch synthesizers and resolution engines.
  * `src/reuse/`: Semantic certificate schemas, store, and verification gating.
  * `src/tools/`: Icarus Verilog simulation interfaces and waveform parsers.
  * `src/constraints/`, `src/credit/`, `src/mining/`, `src/reporting/`, `src/trajectory/`.
* **Experiment Runners (`experiments/`)**:
  * `experiments/run_v11_generalization.py`: Master runner for V11 (100 cases).
  * `experiments/run_v12_external_validation.py`: Master runner for V12 (30 cases).
  * Historical runners (V6–V10.2). *Retained in `experiments/` to preserve pre-registered SHA-256 manifest paths.*
* **Scripts (`scripts/`)**:
  * `scripts/build_v11_benchmark.py`: Constructs 100-case canonical benchmark.
  * `scripts/build_v12_external_benchmark.py`: Constructs 30-case external benchmark.
  * `scripts/check_integrity.py`: Cryptographic hash verifier across 41 frozen files.
  * `scripts/calculate_novelty_metrics.py`: Lexical divergence and identifier analyzer.
  * Historical transition, dataset preparation, and training utilities.
* **Automated Tests (`tests/`)**:
  * 15 pytest suites ensuring 100% pass on all schema, isolation, safety, and immutability tests.
* **Results & Telemetry (`results/`)**:
  * `results/reports/`: Version-controlled machine-readable JSON evaluation outputs and manifests.
  * `results/cost_analysis/`: Token, call, and latency measurement summaries.
* **Documentation (`docs/`)**:
  * `docs/ARCHITECTURE.md`: System architecture and semantic gating principles.
  * `docs/BENCHMARK_PROVENANCE.md`: Comprehensive IP origins and licensing audit.
  * Historical milestone evaluation reports (V6–V12).
* **Training & Datasets**:
  * `training/README.md` & `training/configs/`: LoRA configurations and training procedures.
  * `datasets/README.md`: Explanatory benchmark metadata (heavy JSONs excluded).

### MOVE / REVISE (Paths & Formatting)
* **Path Preservation Decision**: The prompt considered sub-dividing `experiments/` into `experiments/v11/`, etc., and `scripts/` into `scripts/benchmarks/`. However, `results/reports/v12_frozen_artifacts.json` enforces exact paths for `experiments/run_v11_generalization.py`, `experiments/run_v10_*.py`, etc. Moving these files breaks `check_integrity.py` and regression tests. As instructed in Section 4 ("*Only do this if imports and relative paths can remain clean. If moving scripts creates unnecessary path complexity, leave them in the existing structure and document it*"), the existing flat structure within `experiments/` and `scripts/` is retained and documented.

### EXCLUDE (Guarded by `.gitignore`)
* Python virtual environments (`.venv/`, `venv/`).
* Simulator wave dumps (`*.vcd`) and compiled simulation objects (`*.vvp`).
* Transient sandbox run directories (`scratch/`).
* Local weight checkpoints (`checkpoints/`, `ml-cache/`, `*.safetensors`, `*.bin`).
* Heavy intermediate dataset files (`datasets/v9/`, `datasets/v10/` JSONs).
* Local test and IDE caches (`.pytest_cache/`, `__pycache__/`, `.vscode/`).

### DELETE (Disposable / Stale)
* Top-level `configs/` directory: Empty untracked folder (all active YAML configs live cleanly in `training/configs/`).

---

## 3. Proposed Final Repository Layout

```text
hardware-debug-failure-learning/
│
├── README.md               # Visual, student-made overview inspired by Prolepsis
├── RESULTS.md              # Detailed empirical result tables (V8 through V12)
├── REPRODUCIBILITY.md      # Reproduction protocol and environment setup
├── LICENSE                 # MIT License
├── CITATION.cff            # Citation metadata (CFF 1.2.0)
├── .gitignore              # Clean exclusion rules
├── pyproject.toml          # Package configuration
├── requirements.txt        # Core dependencies
├── CONTRIBUTING.md         # Guidelines for community contributions
├── SECURITY.md             # Security policy and disclosure
│
├── rtl/                    # Verilog RTL implementations and testbenches
│   ├── designs/            # Canonical benchmark circuits (FIFO, AXI, FSM, UART, Pipe)
│   ├── bugs/               # Seed defect implementations
│   ├── testbenches/        # Self-checking testbenches with assertion monitors
│   └── v12/                # External realistic circuits across 5 domains (30 cases)
│
├── src/                    # Core library implementation
│   ├── agent/              # LLM prompt templates and client orchestration
│   ├── evaluation/         # Deterministic patch synthesis & resolution engines
│   ├── reuse/              # Semantic certificates, role normalizers, and safety gates
│   ├── tools/              # Icarus Verilog simulator harness and VCD parsers
│   └── ...
│
├── experiments/            # Master evaluation runners (V10.1, V10.2, V11, V12)
│   ├── run_v11_generalization.py      # V11 benchmark runner (N=100)
│   ├── run_v12_external_validation.py  # V12 external benchmark runner (N=30)
│   └── ...
│
├── scripts/                # Benchmark generators and validation utilities
│   ├── build_v11_benchmark.py          # Constructs 100-case canonical corpus
│   ├── build_v12_external_benchmark.py # Constructs 30-case external corpus
│   ├── check_integrity.py              # Validates 41 frozen evaluation artifacts
│   ├── calculate_novelty_metrics.py    # Analyzes lexical novelty and divergence
│   └── ...
│
├── tests/                  # Pytest automated test suite (100 passed, 11 skipped)
│
├── results/                # Machine-readable experiment records
│   ├── reports/            # JSON manifests, evaluation reports, and statistics
│   └── cost_analysis/      # Token, call, and latency measurement data
│
├── docs/                   # Architecture, provenance, and milestone reports
│   ├── ARCHITECTURE.md     # In-depth architectural decomposition and safety gating
│   ├── BENCHMARK_PROVENANCE.md # Origin, adaptation, and validation of benchmark IP
│   ├── GITHUB_ABOUT.md     # Recommended GitHub repository description and topics
│   ├── REPOSITORY_STRUCTURE_AUDIT.md   # This document
│   └── ...
│
├── datasets/               # Dataset documentation / lightweight metadata
│   └── README.md
│
└── training/               # Local fine-tuning configs and instructions
    ├── README.md
    ├── configs/            # YAML configurations (soup_v7_qwen_lora.yaml, etc.)
    └── schemas/            # Training JSON schemas
```
