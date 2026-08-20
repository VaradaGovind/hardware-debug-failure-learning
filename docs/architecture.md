# RCA-Reuse architecture

RCA-Reuse treats reuse as a causal validation pipeline. A prior RCA is not reused merely because a target has a similar log message or signal trace.

```text
failure manifestation
        |
        v
      RCA  ------------------------------+
        |                                |
        v                                |
causal representation                    |
  (generic or transaction-semantic)      |
        |                                |
        +--> transaction/protocol context|
                                         |
new failure manifestation                |
        |                                |
        +--> waveform / RTL observation  |
                                         v
              reuse matching and validation
                         |
                         v
                  safety validation
                   /       |        \\
                  /        |         \\
              reuse   insufficient   new RCA
                       evidence
```

## Components implemented in the repository

The project deliberately keeps the implementation’s existing module layout. The names below refer to code that is present in `src/` rather than to a proposed agent architecture.

### Failure observation and initial RCA

`src/tools/simulator.py`, `src/tools/waveform.py`, and `src/tools/rtl_search.py` provide the local RTL simulation, waveform, and source-search utilities used by the agent and experiment code. `src/agent/` contains baseline, constrained, and re-evaluation agent components. These components support the initial investigation that produces a trajectory and a candidate causal explanation.

### Causal representation

The repository contains two related certificate families:

- `src/reuse/causal_certificate.py` defines a causal certificate and validation helpers based on signal-level state and propagation evidence.
- `src/reuse/generic_certificate.py` defines a generic certificate and validator used by several baselines and audits.
- `src/reuse/transaction_semantic_certificate.py` defines `TransactionContext`, `ProtocolObligation`, and `TransactionSemanticCertificate` for representing a transaction’s context, obligations, and causal expectations.

`src/reuse/transaction_certificate_extractor.py` extracts a transaction-semantic certificate from the project’s available evidence. Its current behavior is benchmark- and protocol-dependent; the UART limitation recorded in the experiment reports is an example.

### Transaction and protocol context

`TransactionContext` captures context such as initiating conditions and an active evidence window. `ProtocolObligation` captures the conditions and expected behavior that must be checked for a reuse decision. This is the layer intended to distinguish two failures that look similar in low-level signal space but occur under different transaction semantics.

### Matching and validation

`src/reuse/similarity_baselines.py` and `src/reuse/scale_similarity_baselines.py` implement comparison baselines. `GenericCertificateValidator`, the remediated validator, and `TransactionSemanticValidator` provide progressively richer validation paths. `src/reuse/audit_validators.py` contains additional trigger/state/temporal and waveform-similarity controls used in audits.

The validator’s outcomes are not all equivalent:

- `PASS` means the stored causal explanation was validated for the available evidence;
- `FAIL` means the observed evidence contradicts the certificate’s requirements;
- `INSUFFICIENT_EVIDENCE` means the target did not exercise the necessary preconditions or did not provide enough evidence to make a safe decision.

### Adaptive boundary and evidence safety

`AdaptiveTransactionBoundaryDetector` in `src/reuse/adaptive_transaction_boundary.py` identifies observable edges, handshakes, state transitions, data movement, activity clusters, and quiescence. It does not use benchmark labels or certificate oracles according to the audit contract in the implementation.

`AdaptiveEvidenceClassifier` in `src/reuse/adaptive_evidence.py` classifies transaction evidence. In particular, a transaction that is active at trace termination can be classified as `TRANSACTION_ACCEPTED_INCOMPLETE` and mapped to `INSUFFICIENT_EVIDENCE`; missing evidence is not converted into `PASS`.

`AdaptiveL2Adapter` connects adaptive boundary recovery to the transaction-semantic validator. The adapter chooses the evidence window and applies the evidence gate, while the frozen L2 validator evaluates the transaction-semantic certificate. The current experiments support a safety interpretation of this component; they do not establish a general recall improvement.

### Reuse or new RCA

If a certificate passes safety validation, the experiment can count the case as a reuse decision. If evidence is insufficient or the certificate fails, the safe path is to avoid reuse and run a new RCA. The current code and experiments do not themselves provide a universal end-to-end bug-resolution oracle, so a validation outcome must not be reported as a resolved bug without a separate resolution measurement.
