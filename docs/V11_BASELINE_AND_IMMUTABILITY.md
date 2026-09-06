# V11 Baseline & Immutability Audit

**Audit Date**: September 6, 2026  
**Experiment Identifier**: `V11_BENCHMARK_EXPANSION_AND_GENERALIZATION`  
**Git Commit**: `c717e91c2c9ec972666e4fdce325504fe1627575`  
**Certification Scope**: Baseline Summary, Architectural Contract, and Frozen File Checksums  

---

## 1. Project Context & Preceding Benchmarks

The Root Cause Analysis (RCA) Reuse project investigates whether trusted, semantic RCA memory combined with formal verification can significantly reduce LLM reasoning workload and maintain or improve bug resolution rates compared to diagnosing hardware bugs from scratch.

### V10.1 Controlled Experiment Baseline
* **Benchmark**: 25 frozen hardware debugging failure cases across 5 digital design families (FIFO, AXI, FSM, UART, Pipeline).
* **Base Model**: `Qwen/Qwen2.5-Coder-1.5B-Instruct`
* **LoRA Adapter**: `soup_v7_qwen_lora` (`best_v7_checkpoint`)
* **Evaluation Oracle**: Deterministic formal Verilog assertions under Icarus Verilog (`iverilog` + `vvp`).
* **V10.1 Measured Results**:
  * Bug Resolution: System A = 12/25 (48.0%) vs. System B = 14/25 (56.0%) (+8.0% abs, +16.67% rel).
  * RCA Accuracy: System A = 15/25 (60.0%) vs. System B = 17/25 (68.0%).
  * LLM Tokens: System A = 83,238 vs. System B = 64,896 (-22.04% reduction).
  * LLM Calls: System A = 48 vs. System B = 35 (-27.08% reduction).
  * Safety: 7 correct reuses, 0 false reuses, 100% negative rejection rate.

### V10.2 Reproducibility & Statistical Findings
* **Repeated Runs**: 5 independent runs across seeds `[42, 43, 44, 45, 46]` showed complete determinism ($\sigma^2 = 0.0$).
* **Statistical Power Limitation**: On $n=25$, discordant pairs were $b=0, c=2$. McNemar's exact test yielded $p = 0.5000$ (statistically underpowered).
* **Official Conclusion**: *"The V10.1 result is fully reproducible, deterministic, and safe, but the benchmark size ($n=25$) prevents strong statistical conclusions."*

---

## 2. Architectural Contrast: System A vs. System B

| Architectural Feature | System A (Plain LLM RCA) | System B (Verified LLM-Reuse RCA) |
|:---|:---|:---|
| **Base Model** | `Qwen2.5-Coder-1.5B-Instruct` | Identical (`Qwen2.5-Coder-1.5B-Instruct`) |
| **LoRA Adapter** | `soup_v7_qwen_lora` | Identical (`soup_v7_qwen_lora`) |
| **Decoding Policy** | Greedy ($T=0.0$, `do_sample=False`) | Identical |
| **RCA Memory Access** | **Strictly Isolated (0% access)** | Trusted Memory of Established Sources |
| **Semantic Verification Gate** | None | Multi-Stage AST + Causal Trace + Invariant Gate |
| **Accepted Reuse Action** | N/A | Bypasses LLM (0 tokens, 0 calls) |
| **Rejected Reuse Action** | Always runs LLM pipeline | Safe fallback to identical System A pipeline |
| **Patch Synthesis Engine** | Deterministic syntax & AST engine | Identical |
| **Resolution Oracle** | Formal hardware assertions in Icarus Verilog | Identical |

---

## 3. Frozen Historical Artifact Checksums

All 25 pre-existing code, manifest, result, and documentation files are strictly frozen. Their SHA256 checksums are recorded below and in [`results/reports/v11_frozen_artifacts.json`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/results/reports/v11_frozen_artifacts.json):

| Artifact Path | SHA256 Checksum |
|:---|:---|
| `results/reports/v10_1_experiment_manifest.json` | `a85a53a33a9485f765f33029d831e79aaae0f183cadc84b43b777a31e1e5f1d7` |
| `results/reports/v10_1_master_evaluation_report.json` | `6820deff54b8257eb84322393e6e506f3765f03fc239ef1884e4fef7f1593a2a` |
| `results/reports/v10_1_case_level_comparison.json` | `c9f856b6cd5293eec6266b2191a3e6dd4bf747a648cf8c4cc3f8c2003f58dc2f` |
| `results/cost_analysis/v10_1_system_a_plain_llm.json` | `ff5d98c66ff1eb7ec9a52bce5d0cc9ea6add49462fd63a96c595b3862610f185` |
| `results/cost_analysis/v10_1_system_b_llm_reuse.json` | `f881f2ff48649a5a20ccf416797298600182bb1d1ad5caca2b6684c02d58ae95` |
| `results/reports/v10_2_reproducibility_manifest.json` | `a4913cbd81bdc7ec1cd88008233a3ce3b8fb310f5c4675f988bab2304c95ffa7` |
| `results/reports/v10_2_repeated_runs.json` | `0f870b6099926b0251a251f0afc37094d9b7f27364ca11cf6daebaf26288ddd9` |
| `results/reports/v10_2_determinism_audit.json` | `90001f481e17aaa8d6480ae2245e089bd4eca0f91a6b5e634cc43bd32aa5b7cd` |
| `results/reports/v10_2_transition_analysis.json` | `7877e3759469fa2651dd4cc703fa495baa1814a48ea3a011e740d02fb7f292f5` |
| `results/reports/v10_2_bootstrap_analysis.json` | `9153ca0280d0a513bf4aeebf177d43b06160284dbc464f5be06b09a0015c1b96` |
| `results/reports/v10_2_master_robustness_report.json` | `dba966c8d00f25cc635e4b5395dc8cc5608dac7426532cfcdf157d1565040d8b` |
| `results/cost_analysis/v8_end_to_end_comparison.json` | `78fe75da2fca2323b34fedf01faeaa12715c419309d6493da4364d5fa845559c` |
| `results/cost_analysis/v10_2_end_to_end_comparison.json` | `38ecd1ac9f7354ad0320982d2e327315058930c204ecd492f6dc0ad2c581be26` |
| `experiments/run_v10_1_plain_llm_rca.py` | `b2c971202109215759dc40ad6e757095bcd6ae7ce6ab09cce8ac8cf24482d3e6` |
| `experiments/run_v10_1_llm_reuse_rca.py` | `0590509e14a6461e735bcf402c14309dbf78cf6dbeb7cae49d21aa2c3841cc93` |
| `experiments/run_v10_1_controlled_experiment.py` | `b741a871ef8f63db3fe895239bb4c366784024b5fcef8adf24e181435e7999b8` |
| `experiments/run_v10_2_reproducibility.py` | `b534c6dc1cb0e593808766b2559cd8e64f4beccfd622cdbfc866410dd9751508` |
| `src/evaluation/deterministic_resolution.py` | `5d355d232963c8aa2da7350c15a8934cd1e4600affa004ba14076610067a6142` |
| `tests/test_v10_1_bug_resolution.py` | `6d859665a953da62137245f0759bef0ef9c094787339eee72b6c514da36f76c6` |
| `tests/test_v10_2_reproducibility.py` | `22ce2df3815806e4b2bebcdb57297a86f7e424f76affc1930b424575edc48613` |
| `docs/V10_1_BUG_RESOLUTION_AUDIT.md` | `325f2ac4c5668744bd367f3b5e38190c756e7962902cad6e6120a17948d02c44` |
| `docs/V10_1_CONTROLLED_BUG_RESOLUTION_REPORT.md` | `db80d74f7ecaa9e1552a64caa55aa4baa06fa5384d731e5bf4a092923cc342ac` |
| `docs/V10_1_SCIENTIFIC_AUDIT.md` | `7ce1f02901cc062f751fee7ca7610df876b9cffd850355477f103335f97ba767` |
| `docs/V10_2_REPRODUCIBILITY_AUDIT.md` | `5d4cc02c0e0aca0efec10cbb47e268f59b6cb33dab014bd636328aba9cccef6b` |
| `docs/V10_2_ROBUSTNESS_AND_STATISTICAL_ANALYSIS.md` | `29765dedbe7138d20ff697d7bfc80bb32f6bf28ea76d30509309b3c9b74496e7` |
