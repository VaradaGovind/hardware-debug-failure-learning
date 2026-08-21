# Reproducibility and Verification Audit

This document records a verification-focused pass over the RCA-Reuse pipeline on 2026-08-20. It separates code paths that were executed in this checkout from historical benchmark artifacts that were inspected but not regenerated.

## Status vocabulary

- **Verified** means the named path was executed successfully in this checkout during this pass.
- **Partial** means a component or smoke path was executed, but the complete research-stage path was not.
- **Historical artifact** means the value was recomputed or checked from an existing local output, without rerunning the producing benchmark.
- **Unavailable** means the required input or external dependency is not present in a clean checkout.

## Pipeline traceability

| Stage | Implementation | Entry point | Status |
|---|---|---|---|
| Source RTL and testbench | `rtl/designs/fifo_f2.v`, `rtl/testbenches/fifo_f2_tb.v` | `scripts/run_rtl_smoke.py` | **Verified** on a temporary copy |
| RTL simulation | `src/tools/simulator.py:VerilogSimulator.run_simulation` | `scripts/run_rtl_smoke.py` | **Verified**; Icarus 12.0 compiled the fixture and produced a VCD. The fixture intentionally prints `FAIL`, so the wrapper's log-based `success` flag is false even though compilation and tracing succeeded. |
| Waveform/trace extraction | `src/tools/waveform.py:WaveformTool.query_waveform`; VCD parsing helpers in `src/reuse/generic_certificate.py` | `scripts/run_rtl_smoke.py` | **Verified**; all nine requested FIFO signals were recovered from the temporary VCD. |
| Initial RCA | `src/agent/re_eval_agents.py:ModelB_StrongCausalAgent.run`; `experiments/run_causal_reuse_poc.py` | `experiments/run_causal_reuse_poc.py` | **Partial / historical**; the agent path exists, but the evaluation agent receives a `ground_truth` argument and is not a blind inference implementation. The POC also manually constructs its stored causal certificate. |
| Causal representation | `src/reuse/causal_certificate.py:CausalCertificate`, `CertificateValidator` | `scripts/run_rtl_smoke.py` | **Partial**; the checked-in FIFO fixture certificate is loaded and validated against a new target trace. Its original RCA creation is historical. |
| Transaction/protocol context | `src/reuse/transaction_certificate_extractor.py:TransactionCertificateExtractor`, `TransactionContext`, and `ProtocolObligation` | `scripts/run_rtl_smoke.py` | **Verified** on the FIFO smoke fixture. |
| RCA-Reuse validation decision | `src/reuse/transaction_semantic_validator.py:TransactionSemanticValidator`, `src/reuse/adaptive_l2_adapter.py:AdaptiveL2Adapter` | `scripts/run_rtl_smoke.py` | **Verified**; both frozen semantic and adaptive validation returned `PASS` for the known same-family fixture. |
| Safety policy | `src/reuse/adaptive_evidence.py:AdaptiveEvidenceClassifier`, `src/reuse/adaptive_reuse_policy.py:AdaptiveReusePolicy` | `scripts/run_rtl_smoke.py`, `tests/test_adaptive_boundary.py` | **Verified** at component/smoke level; the unit suite includes an incomplete-transaction rejection case. |
| Reuse/fallback action | `src/reuse/adaptive_reuse_policy.py:AdaptiveReusePolicy.decide` | `scripts/run_rtl_smoke.py` | **Partial**; both `REUSE_RCA` and `FALLBACK_INDEPENDENT_RCA` mappings were exercised, but the smoke does not launch a new independent RCA after fallback. |
| Benchmark scoring and metrics | `experiments/run_phase4_1_blind_validation.py`, `experiments/run_phase4_3_variable_latency.py`, `scripts/run_phase4_3a_safety_cost_audit.py` | Phase 4 experiment runners | **Historical artifact**; the local processed CSVs and reports were audited read-only and their metrics were recomputed from the rows. The full runners were not rerun during this pass because they rewrite local RTL/results outputs and depend on private benchmark artifacts. |

## Executed commands

From the repository root, with the project virtual environment active:

```powershell
python scripts\run_rtl_smoke.py
python -m pytest -q
```

The smoke result was:

```text
simulator_compiled: true
simulation_execution: PASS
simulation_status: EXPECTED_FAILURE
expected_failure_detected: true
vcd_extracted: true
causal_decision: PASS
transaction_semantic_decision: PASS
adaptive_decision: PASS
reuse_policy: REUSE_RCA
fallback_policy_for_insufficient_evidence: FALLBACK_INDEPENDENT_RCA
```

The smoke script copies the RTL and testbench to `TemporaryDirectory`; it does not overwrite repository VCD, VVP, result, or report files. The minimal stored certificate used by the smoke is [certificate_fifo_simultaneous_rw.json](../examples/fixtures/certificate_fifo_simultaneous_rw.json).

## External simulator check

`iverilog.exe` and `vvp.exe` are installed locally at `C:\iverilog\bin` and report Icarus Verilog 12.0. They are not globally present on the shell `PATH`; `VerilogSimulator` appends this local directory when instantiated. These binaries are external dependencies and are not installed by `pip`.

## Benchmark reproducibility tier

The two tracked summaries in [results/blind_test](../results/blind_test/README.md) and [results/variable_latency](../results/variable_latency/README.md) are supported by local processed CSVs and reports. They are marked **historical artifact** because the benchmark runners were not rerun in this pass. The raw VCDs, benchmark manifests, predictions, and reports remain ignored/private by default. A clean clone therefore reproduces the code smoke and unit tests, but not the 50- or 75-target benchmark tables without separately supplied benchmark artifacts.

## Known provenance boundaries

1. A stored RCA certificate is the input to the verified smoke; the smoke does not claim to reproduce the original human/agent RCA creation.
2. `run_phase4_1_blind_validation.py` performs label-free target inference in its inference section, but reads ground truth afterward to score predictions. Its `ModelB_StrongCausalAgent` source-RCA path is a separate evaluation harness and accepts ground truth.
3. `INSUFFICIENT_EVIDENCE` is a safety outcome, not a failed bug-resolution outcome. The policy maps it to independent RCA fallback.
4. The reported precision, false-reuse rate, positive transfer/recall, and cost compression are distinct metrics. No end-to-end bug-resolution rate is computed by these experiments.

## README numerical-claim audit

| README claim | Trace | Verification |
|---|---|---|
| 50 blind-test failures and 5 hardware families | `results/blind_test/summary.csv`; 50 row records and five distinct `design` values in the audited blind CSV | **Confirmed** |
| 75 variable-latency targets and 10 incomplete traces | `results/variable_latency/summary.csv`; 75 row records and 10 `CLASS_I_INCOMPLETE_EVIDENCE` rows | **Confirmed** |
| 55.6% → 71.4% reuse precision | `results/blind_test/summary.csv`; calculated from `pred_l0` and `pred_l2` accepted rows | **Confirmed** |
| 44.4% → 28.6% false reuse | `results/blind_test/summary.csv`; calculated from false accepted rows over accepted rows | **Confirmed** |
| 3.1% adaptive false reuse | `results/variable_latency/summary.csv`; calculated from `pred_l2_adaptive` | **Confirmed** |
| 10/10 incomplete traces rejected | `results/variable_latency/summary.csv`; 10 Class-I rows, all adaptive decisions `INSUFFICIENT_EVIDENCE` | **Confirmed** |
| ~1.24x full-lifecycle search compression | `results/cost_analysis/summary.csv` plus the cost-consistency report's full-lifecycle model | **Confirmed as a modeled tool-call result; not wall-clock or bug-resolution speedup** |
| Break-even at 2 total manifestations | `results/cost_analysis/summary.csv` and `phase4_3B_cost_consistency_audit.md` | **Confirmed under the source-plus-target convention; the same audit reports 1 subsequent target** |
