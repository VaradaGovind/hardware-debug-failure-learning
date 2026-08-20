# RCA-Reuse limitations

The current results do not establish universal RCA reuse. They are evidence from bounded experiments on a finite set of generated RTL families, protocols, and failure manifestations.

## Evaluation scope

The blind result covers 50 unseen instances across five hardware families. The variable-latency stress report covers 75 held-out targets, including 10 incomplete traces. These are useful adversarial checks but are not a broad sample of RTL bugs, verification environments, or SoC integrations.

## Bug-class and protocol dependence

Reuse behavior depends on the defect class, transaction protocol, stimulus, and observability of the relevant signals. A certificate that works for one causal mechanism can be invalid for another mechanism with the same symptom. The current reports also document a UART extractor limitation: the frozen extractor selected FIFO-style context for UART cases, causing conservative `INSUFFICIENT_EVIDENCE` outcomes. This must be addressed before treating the results as protocol-independent.

## Boundary inference

Adaptive boundary recovery relies on observable activity, transitions, handshakes, state changes, data movement, and quiescence. It can encounter ambiguous boundaries, missing signals, reset interactions, overlapping transactions, asynchronous behavior, or traces that end before causal propagation. The implementation has bounded and heuristic parameters, including quiescence and maximum-window settings. It should not be treated as a formal proof of transaction boundaries.

## Recall and resolution claims

Adaptive boundaries did not improve positive-transfer recall over the fixed-window controls in the current variable-latency stress experiment. Their demonstrated value in that experiment is primarily safety and evidence sufficiency. The project also does not yet provide a direct, end-to-end bug-resolution comparison against full RCA. Reuse precision, false reuse, positive transfer/recall, and cost compression must remain separate metrics.

In particular, no current result justifies reporting a universal or fixed end-to-end bug-resolution rate for RCA-Reuse.

## Scaling and cost measurement

SoC-level scaling, multi-clock protocols, long-running traces, and integration with production verification environments remain to be validated. The cost analysis uses modeled tool-call-equivalent or search costs and does not constitute a complete token, compute, wall-clock, simulator-license, or energy accounting.

## Reproducibility and data availability

Raw traces, waveform files, simulator outputs, held-out labels, and generated results are local artifacts. Some may be private or may not have redistribution terms. They are excluded by default from the initial Git history. Full reproduction therefore requires the local benchmark artifacts and the exact external RTL simulator environment.

The Phase 4.1/4.2 reports also record a benchmark compilation error that affected an initial blind run. Any future public result should preserve the audit trail and state exactly which benchmark generation and simulation artifacts were used.

## Future validation required

- broader and independently reviewed bug corpora;
- direct full-RCA versus RCA-Reuse resolution studies;
- protocol-specific and asynchronous boundary handling;
- SoC-level evaluation with multiple interacting transactions;
- per-class uncertainty and abstention reporting;
- independently reproducible cost and resource measurements.
