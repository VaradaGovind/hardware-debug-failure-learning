# V10.2 Reproducibility Audit & Pre-Execution Certification

**Audit Date**: September 6, 2026  
**Experiment Identifier**: `V10.2_ROBUSTNESS_AND_REPRODUCIBILITY`  
**Git Commit**: `c717e91c2c9ec972666e4fdce325504fe1627575`  
**Certification Scope**: Environment Specification, Frozen Artifact Checksums, and Immutability Safeguards  

---

## 1. System & Execution Environment

| Component | Specification / Version |
|:---|:---|
| **Operating System** | Microsoft Windows 11 Pro 64-bit |
| **Python** | 3.12.10 (tags/v3.12.10:0cc8128, MSC v.1943 64-bit AMD64) |
| **PyTorch** | 2.4.1+cpu (DirectML device backend configured) |
| **Transformers** | 4.48.3 |
| **PEFT** | 0.20.0 |
| **SciPy** | 1.18.1 |
| **NumPy** | 2.5.2 |
| **Icarus Verilog** | 12.0 (devel) (s20150603-1539-g2693dd32b) |
| **Hardware Device** | AMD Radeon RX 7600S (DirectML) / x86_64 CPU Fallback |

---

## 2. Model & Adapter Identity

| Asset | Path / HuggingFace Identifier |
|:---|:---|
| **Base Model** | `Qwen/Qwen2.5-Coder-1.5B-Instruct` |
| **Fine-Tuned Adapter** | `C:/Users/varad/ml-cache/rca-reuse/v7/checkpoints/soup_v7_qwen_lora/best_v7_checkpoint` |
| **Sampling Config** | Deterministic greedy decoding (`temperature=0.0`, `do_sample=False`) |
| **Max Iterations** | 4 multi-turn diagnostic reasoning steps |

---

## 3. Frozen Benchmark Corpus & Checksums

The benchmark corpus consists of 25 canonical hardware debugging cases across 5 digital design families (FIFO, AXI, FSM, UART, Pipeline).

* **Benchmark Manifest**: `results/reports/v10_1_experiment_manifest.json`
* **Benchmark Manifest SHA256**: `a85a53a33a9485f765f33029d831e79aaae0f183cadc84b43b777a31e1e5f1d7`

### Frozen File Integrity Checksums

Prior to executing any V10.2 script, the SHA256 checksums of all existing baseline, audit, and benchmark files were recorded:

| File Path | SHA256 Checksum |
|:---|:---|
| `results/reports/v10_1_experiment_manifest.json` | `a85a53a33a9485f765f33029d831e79aaae0f183cadc84b43b777a31e1e5f1d7` |
| `results/reports/v10_1_master_evaluation_report.json` | `6820deff54b8257eb84322393e6e506f3765f03fc239ef1884e4fef7f1593a2a` |
| `results/reports/v10_1_case_level_comparison.json` | `c9f856b6cd5293eec6266b2191a3e6dd4bf747a648cf8c4cc3f8c2003f58dc2f` |
| `results/cost_analysis/v10_1_system_a_plain_llm.json` | `0d8383093f75dea16b401dc7c7240422a31803a74ca1156f7f86961340cc05d3` |
| `results/cost_analysis/v10_1_system_b_llm_reuse.json` | `bf072331dbfb13202d8a0ae1d32c0331db5dbc8e5a499476594a057d5b3c570e` |
| `results/cost_analysis/v8_end_to_end_comparison.json` | `78fe75da2fca2323b34fedf01faeaa12715c419309d6493da4364d5fa845559c` |
| `results/cost_analysis/v10_2_end_to_end_comparison.json` | `38ecd1ac9f7354ad0320982d2e327315058930c204ecd492f6dc0ad2c581be26` |
| `experiments/run_v10_1_plain_llm_rca.py` | `b2c971202109215759dc40ad6e757095bcd6ae7ce6ab09cce8ac8cf24482d3e6` |
| `experiments/run_v10_1_llm_reuse_rca.py` | `0590509e14a6461e735bcf402c14309dbf78cf6dbeb7cae49d21aa2c3841cc93` |
| `experiments/run_v10_1_controlled_experiment.py` | `b741a871ef8f63db3fe895239bb4c366784024b5fcef8adf24e181435e7999b8` |
| `src/evaluation/deterministic_resolution.py` | `5d355d232963c8aa2da7350c15a8934cd1e4600affa004ba14076610067a6142` |
| `tests/test_v10_1_bug_resolution.py` | `6d859665a953da62137245f0759bef0ef9c094787339eee72b6c514da36f76c6` |
| `docs/V10_1_CONTROLLED_BUG_RESOLUTION_REPORT.md` | `db80d74f7ecaa9e1552a64caa55aa4baa06fa5384d731e5bf4a092923cc342ac` |
| `docs/V10_1_SCIENTIFIC_AUDIT.md` | `7ce1f02901cc062f751fee7ca7610df876b9cffd850355477f103335f97ba767` |

---

## 4. Immutability & Reproducibility Safeguards

1. **No Overwrites of Historical Files**: All V10.2 scripts write strictly to new filenames (`results/reports/v10_2_*`, `docs/V10_2_*`, `experiments/run_v10_2_*`, `tests/test_v10_2_*`).
2. **Benchmark Source RTL Freeze**: `rtl/designs/` remains read-only.
3. **Repeated Runs Requirement**: 5 independent runs will be conducted with seeds `[42, 43, 44, 45, 46]` to rigorously evaluate behavioral, diagnostic, and token accounting determinism.
4. **Statistical Rigor**: McNemar's exact test, 10,000 paired bootstrap resamples, and Wilson score intervals will be calculated.
