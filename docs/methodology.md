# RCA-Reuse methodology

This document separates what the current experiments measure from hypotheses that remain to be tested.

## Baseline approach

The earlier reuse baselines represent failure behavior using signal-level observations, invariants, trigger/state predicates, similarity measures, and propagation checks. Relevant implementation paths include `generic_certificate.py`, `causal_certificate.py`, `similarity_baselines.py`, `scale_similarity_baselines.py`, and the validators in `src/reuse/`.

These baselines are useful controls but are not assumed to be safe for reuse in every context. The motivating observation is that different defects can produce similar low-level signal behavior.

## Why low-level signal matching is unsafe

Two traces can share a symptom, trigger, state value, or low-level delta while differing in the transaction that was initiated or in the protocol obligation that applied. A validator that sees only the shared signal pattern can accept a certificate for the wrong defect. The adversarial tests in `tests/test_adaptive_boundary.py` and the transaction-semantic reports exercise examples of same-symptom, same-trigger, same-invariant, incomplete, stalled, and reset-related cases.

## Transaction-level extension

The transaction-semantic extension adds:

- an initiating transaction context;
- protocol obligations and expected behavior;
- a bounded active evidence window;
- downstream causal propagation checks;
- explicit handling for unexercised and incomplete evidence.

The implementation uses `TransactionContext`, `ProtocolObligation`, `TransactionSemanticCertificate`, `TransactionCertificateExtractor`, and `TransactionSemanticValidator`. The extension is intended to make the reuse decision conditional on the causal mechanism being exercised, not only on an observed signal shape.

## Frozen blind evaluation

The Phase 4.1 blind evaluation report describes 50 unseen failure instances across five hardware families. The target inference was separated from bug IDs, family labels, and ground-truth metadata; scoring was performed afterward. The reported low-level comparison was 55.6% reuse precision and 44.4% false reuse, while the frozen transaction-semantic result was 71.4% precision and 28.6% false reuse.

The report also records that the initial Phase 4.1 run had missing VCDs for some generated FIFO and PIPELINE cases. The Phase 4.2 reproducibility audit attributes the change from 33.3% to 66.7% positive transfer in the later re-evaluation to a benchmark compilation typo being corrected, not to adaptive boundary recovery. This distinction is important: the repository must not present that change as an algorithmic recall improvement.

## Variable-length transaction evaluation

The Phase 4.3 variable-latency stress test evaluates held-out traces with short, delayed, multi-beat, stalled/backpressured, negative, and incomplete-evidence classes. It compares static windows with fixed-window controls, adaptive boundary recovery, and additional non-semantic controls.

The local report describes 75 targets and 10 incomplete traces. The adaptive L2 configuration reached 77.5% positive transfer, the same as the fixed-window controls in that benchmark, while its reuse precision was 0.969 and its false reuse rate was 0.031. The experiment therefore supports a safety result, not a recall increase.

## Adaptive-boundary methodology

The boundary detector is designed to use observable waveform structure:

1. ignore reset activity when identifying active execution;
2. detect signal activity and transitions;
3. identify handshake stalls/accepts, state transitions, and data movement where the relevant signals are present;
4. cluster activity separated by a configurable quiescence threshold;
5. extend the active segment with a small downstream propagation margin;
6. classify the resulting evidence as absent, stalled, incomplete, sufficient, or ambiguous.

The adaptive adapter sends sufficient evidence to the frozen transaction-semantic validator. The safety property under test is that missing or truncated evidence is represented as `INSUFFICIENT_EVIDENCE` rather than being treated as proof of a certificate.

The variable-latency audit reports 10/10 conservative rejections of incomplete traces and a false reuse reduction from 8.8% for the static controls to 3.1% for adaptive L2. It also reports equal positive transfer for adaptive and fixed controls in the evaluated stress set. A future hypothesis is that better protocol-specific boundary inference could recover positives that genuinely require longer or delayed windows; that hypothesis is not established by the current benchmark.

## Cost analysis

The cost audit includes the validation path, fallback RCA for rejected targets, initial source RCA, and certificate extraction. The reported full-lifecycle adaptive search compression is approximately 1.24×.

The audit distinguishes two break-even quantities:

- one subsequent reuse target is enough to recover the one-time extraction investment (`N_targets* = 1`);
- counting the source manifestation itself, the total break-even point is `N* = 2` manifestations.

The second convention is the one used in the README because it includes the initial source failure in the lifecycle count. These are modeled search/tool-call-equivalent costs, not a complete measurement of wall-clock time, energy, or LLM token usage.

## Measured results versus hypotheses

Measured in the current artifacts:

- the 50-instance blind comparison and its precision/false-reuse values;
- the variable-latency safety audit and 10/10 incomplete-trace result;
- the 3.1% adaptive false-reuse rate;
- the full-lifecycle cost audit and its approximately 1.24× compression value.

Not established by the current artifacts:

- universal safe RCA reuse;
- a particular end-to-end bug-resolution rate;
- recall improvement caused by adaptive transaction boundaries;
- SoC-level generalization;
- generalization beyond the evaluated bug classes and protocol families.
