# RCA-Reuse

## Safe Reuse of RTL Root-Cause Analysis Across Repeated Failures

> Research prototype for evaluating whether an expensive RTL root-cause analysis (RCA) result can be validated and reused for later manifestations of a related failure.

## Overview

Debugging an RTL failure can require repeated signal inspection, simulation, source searches, and hypothesis testing. RCA-Reuse studies whether the result of one expensive RCA can be turned into a causal artifact and checked against later failures before running the full RCA again.

The central safety requirement is conservative reuse: a similar symptom is not enough. A later failure should be reused only when the observed transaction context, protocol obligations, causal behavior, and available evidence are consistent with the stored RCA. If the trace is incomplete or the evidence is insufficient, the prototype can recommend falling back to a new RCA.

This repository contains the implementation and local experiment artifacts for an ongoing research project. It is private by default and is not configured for publication or automated pushing.

## Motivation

Repeated failure manifestations can cause an engineer or debugging agent to repeat much of the same expensive investigation. Reusing a prior RCA could reduce redundant work, but an unsafe reuse decision can transfer the wrong explanation to a different bug. The project therefore treats reuse as a verification problem, not as a nearest-neighbor lookup.

## Key observation

Low-level signal behavior is not sufficient for safe RCA reuse. Different bugs can produce similar values, transitions, or invariants at the signal level. The same observed delta may have different meanings depending on which transaction was initiated, which protocol obligation applied, and whether the causal effect propagated through the design.

## Approach

The current code supports the following research-level pipeline:

1. An initial RCA investigates a failure using the project’s simulation, waveform, RTL-search, and agent components.
2. A causal representation is stored as a generic or transaction-semantic certificate. The implementation includes `CausalCertificate`, `GenericCausalCertificate`, and `TransactionSemanticCertificate`.
3. Transaction-level context records initiating signals, active windows, and other observable context.
4. Protocol obligations express conditions that must hold for a transaction and the expected causal behavior.
5. Reuse matching and validation compare a target waveform against the stored certificate. Low-level, remediated, and transaction-semantic validators are available for comparison.
6. Safety checks reject mismatches and can return `INSUFFICIENT_EVIDENCE` when a transaction was not exercised or the trace ended before the relevant behavior was observable.
7. The adaptive boundary detector recovers a variable-length evidence segment from observable activity, and the adaptive evidence classifier decides whether the frozen transaction-semantic validator has enough evidence to run.

The adaptive adapter is designed to select an evidence window and delegate the causal decision to the transaction-semantic validator. It does not establish that adaptive windows improve recall in general.

## Research questions

- Can RCA knowledge be safely reused across future failure manifestations?
- Does transaction-level context improve reuse precision and negative discrimination over low-level signal matching?
- Can protocol-aware transaction boundaries reduce unsafe reuse on incomplete or variable-length traces?
- When does reuse become cost-effective after initial RCA and certificate extraction costs are included?
- Which bug classes and protocol families remain difficult for certificate reuse?

## Experimental setup

The repository contains several generations of experiments. The claims summarized below focus on the transaction-semantic blind evaluation and the variable-latency safety/cost audits.

- Frozen blind evaluation: 50 unseen failure instances across five hardware families (FIFO, AXI, FSM, UART, and PIPELINE).
- Variable-length stress evaluation: held-out traces covering short, delayed, multi-beat, stalled/backpressured, negative, and incomplete-evidence cases. The local Phase 4.3 report describes 75 targets, including 10 incomplete traces.
- Controls: low-level and remediated validators, fixed transaction windows, adaptive boundary recovery, and non-semantic window controls where applicable.
- Cost model: validation, fallback RCA, initial source RCA, and certificate extraction are accounted for in the full-lifecycle analysis.

Inference is intended to be blind to target labels and ground-truth metadata; labels are used by the experiment harness only for post-hoc scoring. The held-out datasets and raw traces are local artifacts and are not included in the initial shareable package.

## Results

The table separates the scope of the 50-instance blind comparison from the 75-target variable-latency safety/cost audit. Percentages are shown as percentages rather than as probabilities to avoid conflating precision with recall.

| Metric | Result |
|---|---|
| Blind-test failures | 50 |
| Hardware families | 5 |
| Reuse precision, low-level baseline → frozen transaction-semantic result | 55.6% → 71.4% |
| False reuse, low-level baseline → frozen transaction-semantic result | 44.4% → 28.6% |
| Adaptive-boundary false reuse, variable-latency audit | 3.1% |
| Incomplete traces rejected conservatively by adaptive evidence checks | 10/10 |
| Full-lifecycle search compression, adaptive pipeline | ~1.24× |
| Break-even including the source manifestation | 2 total manifestations (1 source + 1 subsequent target) |

These values are measured experiment outputs, not an end-to-end bug-resolution claim. In particular, the project has not established a universal RCA reuse rate or a particular end-to-end bug resolution rate.

### Metric definitions

- **Reuse precision**: the fraction of reuse decisions that are correct reuse decisions among the decisions that attempted reuse in the reported comparison.
- **False reuse rate**: the fraction of reuse decisions that incorrectly accepted a different defect; it is not the complement of recall.
- **Positive transfer / recall**: the fraction of designated same-defect positive manifestations accepted by the reuse validator; it is not bug resolution rate.
- **Bug resolution rate**: not directly measured end-to-end in the current project. A conservative validation decision or a fallback RCA should not be counted as a resolved bug without a separate resolution study.
- **Search compression ratio**: the modeled independent-search cost divided by the modeled reuse-pipeline cost. The `~1.24×` value includes the initial RCA and certificate extraction in the full-lifecycle audit.

The cost audit distinguishes one subsequent reuse target (`N_targets* = 1`) from two total manifestations (`N* = 2`, counting the source failure). This is why the repository reports the break-even result as two total manifestations.

## Interpretation

The blind comparison supports the claim that transaction-semantic context can improve reuse precision and reduce false reuse relative to the low-level baseline on the evaluated benchmark. The variable-latency audit supports a narrower safety claim: adaptive boundaries and evidence-sufficiency checks reduced false reuse, especially for incomplete traces, while the current stress test did not show a recall improvement over the fixed-window controls.

Adaptive transaction boundaries should therefore be described as a safety and evidence-efficiency mechanism in the current results, not as a demonstrated recall engine. The experiments also expose important failure modes, including fixed-window sensitivity and a UART extractor mismatch. Broader evaluation is needed before drawing conclusions about arbitrary RTL designs or SoC-scale debugging.

## Limitations

The current limitations are documented in [docs/limitations.md](docs/limitations.md). The most important are:

- the evaluation scale and hardware-family coverage are limited;
- results can depend strongly on bug class, protocol, and stimulus;
- transaction-boundary inference can be ambiguous or incomplete;
- SoC-level and multi-clock scaling remain unvalidated;
- direct comparison against end-to-end bug resolution by full RCA is future work;
- compute and token accounting are modeled experiment costs rather than a complete hardware or wall-clock accounting;
- some held-out datasets, waveforms, and results are local/private artifacts and are intentionally excluded here.

## Roadmap

- Improve protocol-aware boundary inference, including asynchronous and UART-specific control protocols.
- Evaluate a larger and more diverse bug corpus with independently reviewed ground truth.
- Extend validation to SoC-level and multi-clock environments.
- Compare full RCA and RCA-Reuse directly on the same manifestations, including resolution outcomes.
- Add explicit token, compute, wall-clock, and simulator-cost accounting.
- Strengthen failure-mode classification and report per-class precision, false reuse, recall, and insufficiency rates.

## Reproducibility

The project requires Python 3.11 or newer and the Python packages listed in `requirements.txt`. The RTL simulator helpers also expect `iverilog` and `vvp` to be available on `PATH`; these are external tools and are not installed by pip.

From the repository root:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python examples\\adaptive_boundary_demo.py
python -m pytest
```

The larger experiment runners are intentionally explicit scripts rather than a single package command. Examples are:

```powershell
python experiments\\run_phase4_1_blind_validation.py
python experiments\\run_phase4_2_adaptive_boundary.py
python experiments\\run_phase4_3_variable_latency.py
python scripts\\run_phase4_3a_safety_cost_audit.py
python scripts\\run_phase4_3b_cost_consistency_audit.py
```

These commands can regenerate local results, waveforms, and reports and may require the local benchmark artifacts. Full reproducibility is not claimed until the private/held-out datasets and their redistribution terms are resolved. See [results/README.md](results/README.md) and [datasets/README.md](datasets/README.md) before sharing anything outside the private research group.

## Repository structure

The existing layout is preserved where changing paths would change experiment behavior:

```text
src/
  reuse/          causal certificates, semantic validators, adaptive boundary/evidence code
  agent/          baseline, constrained, and re-evaluation agent components
  tools/          RTL search, simulation, and waveform utilities
  evaluation/     metric calculation
  reporting/      plot helpers
  trajectory/     trajectory schemas and logging
  constraints/    negative-constraint schemas
  credit/         action-credit and counterfactual components
  mining/         pattern-mining components
experiments/      end-to-end experiment runners
scripts/          benchmark generation and audit utilities
tests/            unit tests for reusable components
datasets/         local benchmark metadata; excluded from the initial commit by default
rtl/              RTL fixtures and generated simulator outputs; waveforms/binaries are ignored
results/           generated reports and artifacts; see results/README.md
docs/              architecture, methodology, and limitations
examples/          small local smoke examples
```

## License

The source code in this repository is released under the MIT License; see [LICENSE](LICENSE). Dataset, RTL, waveform, and generated-result redistribution is a separate question and is intentionally not implied by the source license.

## Research status

This repository contains an ongoing research prototype. Results and implementation are subject to change.

## Contact

Varada Govind Aakula<br>
IIIT Allahabad<br>
GitHub: <https://github.com/VaradaGovind>
