# V12.1 Git Release & Commit Plan

**Date**: September 6, 2026  
**Target Release**: Milestone V12.1 (Public Research Repository Release Preparation)  
**Status**: DRAFT PLAN — READY FOR HUMAN REVIEW  

---

## 1. Safety Directive

> [!IMPORTANT]
> **No commits or pushes should be executed automatically.**
> This plan organizes all uncommitted and newly generated files into logical, reviewable commit batches so that the repository maintainer can inspect and stage changes with full confidence.

---

## 2. Uncommitted Files Classification

### Category A: READY TO COMMIT (Core Release Files)

#### 1. Public Documentation & Specifications
* `README.md` (Overhauled top-level guide)
* `RESULTS.md` (Research results summary)
* `REPRODUCIBILITY.md` (Reproduction instructions)
* `docs/BENCHMARK_PROVENANCE.md` (Benchmark origin and realism)
* `docs/ARCHITECTURE.md` (System architecture and safety principles)
* `docs/RELEASE_V12_1.md` (V12.1 release notes)
* `docs/V12_1_RELEASE_AUDIT.md` (Initial release audit)
* `docs/V12_1_COMMIT_PLAN.md` (This commit organization document)
* `docs/V12_1_RELEASE_READINESS.md` (Final release scorecard)

#### 2. Research Audit Documents (V11 & V12)
* `docs/V11_BASELINE_AND_IMMUTABILITY.md`
* `docs/V11_EXPERIMENT_PROTOCOL.md`
* `docs/V11_FAILURE_ANALYSIS.md`
* `docs/V11_GENERALIZATION_AND_STATISTICAL_EVALUATION.md`
* `docs/V11_LEAKAGE_AND_INDEPENDENCE_AUDIT.md`
* `docs/V11_SCIENTIFIC_AUDIT.md`
* `docs/V12_DATA_ISOLATION_AUDIT.md`
* `docs/V12_EXTERNAL_CORPUS_SELECTION.md`
* `docs/V12_EXTERNAL_GENERALIZATION_REPORT.md`
* `docs/V12_FAILURE_ANALYSIS.md`
* `docs/V12_SCIENTIFIC_AUDIT.md`
* `docs/V12_STRUCTURAL_NOVELTY_AUDIT.md`

#### 3. Canonical Evaluation Reports & Manifests
* `results/reports/v11_benchmark_manifest.json`
* `results/reports/v11_benchmark_validation.json`
* `results/reports/v11_master_report.json`
* `results/reports/v11_case_level_results.json`
* `results/reports/v11_transition_analysis.json`
* `results/reports/v11_statistical_analysis.json`
* `results/reports/v11_repeated_runs.json`
* `results/reports/v11_frozen_artifacts.json`
* `results/reports/v12_external_benchmark_manifest.json`
* `results/reports/v12_external_benchmark_validation.json`
* `results/reports/v12_master_report.json`
* `results/reports/v12_case_level_results.json`
* `results/reports/v12_transition_analysis.json`
* `results/reports/v12_statistical_analysis.json`
* `results/reports/v12_repeated_runs.json`
* `results/reports/v12_historical_integrity.json`
* `results/reports/v12_frozen_artifacts.json`

#### 4. Hardware RTL & Testbenches
* `rtl/v12/` (All 60 Verilog design and testbench files across 30 cases)

#### 5. Evaluation Harnesses & Scripts
* `experiments/run_v11_generalization.py`
* `experiments/run_v12_external_validation.py`
* `scripts/build_v11_benchmark.py`
* `scripts/build_v12_external_benchmark.py`
* `scripts/calculate_novelty_metrics.py` (Promoted utility)
* `scripts/check_integrity.py` (Promoted utility)
* `src/evaluation/v11_deterministic_resolution.py`
* `src/evaluation/v12_deterministic_resolution.py`

#### 6. Regression Test Suites
* `tests/test_v11_generalization.py`
* `tests/test_v12_external_validation.py`

#### 7. Repository Configuration
* `.gitignore` (Refined exclusions)

---

### Category B: REVIEW REQUIRED (Historical V9 & V10 Artifacts)
The following files represent historical research milestones (V9 and V10). They are valuable for complete project provenance but should be reviewed prior to inclusion:
* `docs/V10_*` (V10.1 and V10.2 milestone reports)
* `docs/V9_*` (V9 pipeline validation reports)
* `experiments/run_v10_*.py`, `experiments/run_v9_evaluation.py`
* `results/cost_analysis/v10_*`, `results/cost_analysis/v9_*`
* `rtl/designs/v10_*`, `rtl/testbenches/v10_*`
* `scripts/*v10*`, `scripts/*v9*`
* `tests/test_v10_*`
* `training/` (LoRA configs and schemas)
* *Recommendation*: Include in a dedicated historical milestone commit or stage together with release to preserve 100% frozen artifact hash validation.

---

### Category C: DO NOT COMMIT (Scratch & Transient Files)
* `scratch/` (Development logs, sandbox caches, temporary test files; correctly ignored by `.gitignore`)
* `results/cost_analysis/logs/` (504 raw `.jsonl` run traces; correctly ignored by `.gitignore`)
* `.venv/`, `venv/` (Virtual environments)
* `*.vcd`, `*.vvp` (Simulator waveform dumps and compiled bytecode)
* `__pycache__/`, `.pytest_cache/` (Python execution caches)

---

## 3. Recommended Staged Commit Structure

When ready to commit, the following 4-step commit structure is recommended:

### Commit 1: Core Research Infrastructure & Benchmarks
```bash
git add rtl/v12/
git add src/evaluation/v11_deterministic_resolution.py src/evaluation/v12_deterministic_resolution.py src/evaluation/deterministic_resolution.py
git add experiments/run_v11_generalization.py experiments/run_v12_external_validation.py
git add scripts/build_v11_benchmark.py scripts/build_v12_external_benchmark.py
git add results/reports/v11_* results/reports/v12_*
git commit -m "feat(benchmarks): add V11 expanded and V12 external realistic benchmarks and runners"
```

### Commit 2: Regression Testing & Historical Milestones
```bash
git add tests/
git add rtl/designs/ rtl/testbenches/
git add experiments/run_v10* experiments/run_v9*
git add scripts/audit_* scripts/build_v10* scripts/evaluate_* scripts/recompute_* scripts/simulate_* scripts/train_* scripts/verify_*
git add results/cost_analysis/
git add results/reports/v10_* results/reports/v9_* results/reports/v8_*
git add training/
git commit -m "test(regression): add full test suite and historical milestone records"
```

### Commit 3: Tooling Promotion & Git Hygiene
```bash
git add scripts/calculate_novelty_metrics.py scripts/check_integrity.py
git add .gitignore
git commit -m "chore(tooling): promote novelty and integrity utilities and refine gitignore"
```

### Commit 4: Public Documentation & V12.1 Release Readiness
```bash
git add README.md RESULTS.md REPRODUCIBILITY.md
git add docs/
git commit -m "docs(release): prepare V12.1 public research release documentation and audits"
```
