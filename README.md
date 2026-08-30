# RCA-Reuse: Safe Reuse of RTL Root-Cause Analysis

> Research prototype for evaluating whether an expensive RTL root-cause analysis (RCA) can be safely validated and reused for later manifestations of related failures.

---

## 1. What Problem is RCA-Reuse Solving?

Debugging hardware failure manifestations in RTL simulation is expensive. Diagnosing a single failing testbench often requires iterative signal tracing, waveform inspection, source-code analysis, and hypothesis testing. When similar failure manifestations recur during hardware development or regression testing, engineers or automated debugging agents often repeat the entire investigation from scratch.

**RCA-Reuse** evaluates whether the causal explanation produced by an initial root-cause analysis can be formalized into a reusable **causal certificate** and checked against subsequent failures, bypassing redundant search when the underlying defect mechanism is identical.

---

## 2. Why is RCA Reuse Difficult?

Reusing a prior debugging explanation is not a simple string or waveform similarity search:

1. **Symptom Aliasing:** Completely different defects often produce identical symptoms (e.g., buffer overflow, timeout, or dropped handshake).
2. **Invariant Ambiguity:** Low-level signal properties (e.g., signal stability or counter increments) can be identical between correct execution, benign timing variations, and distinct bugs.
3. **Variable Transaction Latency:** Handshake stalls, pipeline backpressure, and arbitrary testbench delays change the cycle distance between trigger and manifestation.
4. **Incomplete Traces:** Truncated waveforms or aborted testbenches may display matching initial states before downstream causal divergence occurs.
5. **Asymmetric Cost of False Reuse:** In hardware debugging, a false reuse (transferring the wrong root cause) misdirects verification engineers and costs significantly more time than falling back to independent search.

---

## 3. What is the Proposed Approach?

RCA-Reuse frames reuse as a **formal causal verification and safety triage pipeline**:

```text
Target Failure Trace (VCD)
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 1. Adaptive Transaction Boundary Recovery              │
│    Isolates active transaction segment from waveform   │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. Evidence Sufficiency Gate                           │
│    Rejects incomplete, truncated, or unexercised traces│
└────────┬───────────────────────────────────────┬───────┘
         │ [Sufficient Evidence]                 │ [Incomplete / Ambiguous]
         ▼                                       │
┌─────────────────────────────────────────┐      │
│ 3. Transaction-Semantic Validator       │      │
│    - Transaction Preconditions          │      │
│    - Protocol Obligations               │      │
│    - Downstream Causal Propagation      │      │
└────────┬────────────────────────┬───────┘      │
         │ [Validated PASS]       │ [FAIL]       │
         ▼                        ▼              ▼
┌─────────────────┐     ┌────────────────────────────────┐
│  REUSE_RCA      │     │  FALLBACK_INDEPENDENT_RCA      │
│  (Bypass Search)│     │  (Run Full Autonomous Search)  │
└─────────────────┘     └────────────────────────────────┘
```

1. **Transaction-Semantic Certificates:** Capture initiating transaction preconditions, protocol-level obligations, and required downstream causal propagation signals.
2. **Adaptive Boundary Detection:** Recovers variable-length evidence windows directly from observable signal activity and quiescence without relying on fixed cycle counts.
3. **Conservative Safety Policy:** If evidence is insufficient, truncated, or inconsistent with the certificate, the policy avoids guessing and safely triggers `FALLBACK_INDEPENDENT_RCA`.

---

## 4. Project Evolution

The project progressed through empirical hypothesis-and-failure iterations:

- **Initial Idea:** Can an existing RCA result be safely reused for future failure manifestations?
- **First Approach (Phase 3 - Low-Level Invariants):** Matched signal-level invariants and stability constraints.
- **Problem Discovered:** Failed on adversarial controls; different defects produced identical low-level deltas, leading to a 44.4% false reuse rate.
- **Next Approach (Phase 4 - Transaction Semantics):** Introduced transaction-level context and protocol obligations (`TransactionSemanticCertificate`).
- **Blind Evaluation (Phase 4.1):** 50 unseen failures across 5 hardware families (`FIFO`, `AXI`, `FSM`, `UART`, `PIPELINE`).
  - *Result:* Precision improved from 55.6% to 71.4%, and false reuse dropped to 28.6%.
- **Next Problem Discovered:** Rigid static transaction windows (4 cycles) collapsed positive recall (33.3%) on variable-latency testbench stimulus.
- **Adaptive Boundaries (Phase 4.2 / 4.3):** Added dynamic boundary recovery based on signal transitions, handshakes, and quiescence.
  - *Result:* False reuse dropped to 3.1%, and 10/10 incomplete traces were conservatively rejected.
- **Cost Analysis:** Modeled full-lifecycle tool costs, demonstrating a ~1.24x search compression and break-even at 2 total manifestations.
- **Current Research Question:** Can transaction boundaries and protocol obligations be inferred dynamically across complex, interleaved multi-clock protocols without human annotations?

---

## 5. Summary of Experimental Results

| Metric | Baseline (Low-Level) | Proposed (Transaction-Semantic) | Evaluation Scope |
|---|:---:|:---:|---|
| **Reuse Precision** | 55.6% | **71.4%** (Frozen) / **96.9%** (Adaptive) | 50-target blind test / 75-target stress test |
| **False Reuse Rate (FRR)** | 44.4% | **28.6%** (Frozen) / **3.1%** (Adaptive) | 50-target blind test / 75-target stress test |
| **Positive Transfer (Recall)** | 33.3% | **33.3%** (Frozen) / **77.5%** (Adaptive) | 15 designated positive controls |
| **Incomplete Trace Handling** | 0% Rejected | **10/10 Rejected (100%)** | 10 truncated stress cases (Class I) |
| **Search Compression Ratio (SCR)** | 0.96x | **~1.24x** | Analytical full-lifecycle cost model |
| **Break-Even Point** | Never | **2 total manifestations** | 1 initial source RCA + 1 subsequent target reuse |

*Note: These metrics measure triage and validation decisions, not end-to-end bug resolution rates. See [docs/rca_vs_reuse.md](docs/rca_vs_reuse.md).*

### 5.1 Paired Controlled Comparison (Operational Workload Stream)

In addition to static benchmark validation, an end-to-end paired controlled comparison evaluates sequential failure arrivals across 5 hardware families:
- **Workload Stream:** 25 failure manifestations (5 sources + 20 targets).
- **RCA Avoidance:** 8 / 25 full RCA investigations avoided (32% reduction in initial RCA invocations).
- **Latency Reduction:** ~34% lower measured wall-clock execution time under local simulation.
- **Diagnostic Parity:** 80.0% baseline correctness vs. 80.0% RCA-Reuse correctness (zero accuracy loss).
- **Incomplete Trace Safety:** 100% (5/5) of truncated traces safely rejected to independent fallback.
- **Backend Note:** Uses a deterministic local proxy backend; physical LLM token accounting is not available in local mode. Full details and operational accounting are in [docs/rca_vs_reuse.md](docs/rca_vs_reuse.md).

---

## 6. Reproducibility Boundaries

### What Can Currently Be Reproduced
- **Unit Tests:** All unit tests for boundary detection, evidence classification, and certificate parsing run via `pytest`.
- **End-to-End RTL Smoke Test:** `python scripts/run_rtl_smoke.py` compiles real Verilog fixtures with Icarus Verilog (`iverilog`), runs simulation, generates VCDs, extracts waveforms, checks transaction semantics, and executes the reuse/fallback policy.
- **Adaptive Boundary Demo:** `python examples/adaptive_boundary_demo.py` demonstrates boundary segmentation on synthetic traces.

### What Is Treated as Historical Artifacts
- **The 50-Target Blind Benchmark:** The historical 50-row CSV ([results/transaction_semantic_certs/blind_validation/processed/scored_heldout_evaluation.csv](results/transaction_semantic_certs/blind_validation/processed/scored_heldout_evaluation.csv)) contains 19 rows where VCDs were unsimulated during the initial Phase 4.1 run (17 testbench string escaping typos and 2 AXI net conflicts). All 50 rows were retained in the denominator.
- **Raw Waveform Traces:** 295 local `.vcd` trace files and compiled `.vvp` simulator binaries are excluded from version control via `.gitignore` to prevent repository bloat.

See [docs/blind_test_audit.md](docs/blind_test_audit.md) and [docs/reproducibility.md](docs/reproducibility.md) for full audit records.

---

## 7. Quickstart & Running the Prototype

### Prerequisites
- **Python:** 3.11 or newer
- **External RTL Simulator:** Icarus Verilog (`iverilog` and `vvp`). On Windows, Icarus 12.0 at `C:\iverilog\bin` is automatically detected by `VerilogSimulator`.

### Setup
```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3. Optional: Install src namespace in editable mode
python -m pip install -e .
```

### Running the End-to-End Smoke Test
```powershell
python scripts/run_rtl_smoke.py
```

Expected output:
```json
{
  "adaptive_decision": "PASS",
  "causal_decision": "PASS",
  "expected_failure_detected": true,
  "explanation": "The fixture intentionally contains a failing FIFO scenario. The simulator executed cleanly and produced the expected failure trace for RCA-Reuse analysis.",
  "fallback_policy_for_insufficient_evidence": {
    "incurred_cost_calls": 10.9,
    "policy_action": "FALLBACK_INDEPENDENT_RCA",
    "raw_decision": "INSUFFICIENT_EVIDENCE",
    "reason": "",
    "safe_to_reuse": false,
    "stage": "UNKNOWN"
  },
  "fixture": "fifo_f2",
  "reuse_policy": {
    "incurred_cost_calls": 2.0,
    "policy_action": "REUSE_RCA",
    "raw_decision": "PASS",
    "reason": "Full transaction obligation violation and causal propagation verified.",
    "safe_to_reuse": true,
    "stage": "FULL_TRANSACTION_SEMANTIC"
  },
  "simulation_execution": "PASS",
  "simulation_status": "EXPECTED_FAILURE",
  "simulator_compiled": true,
  "transaction_semantic_decision": "PASS",
  "vcd_extracted": true,
  "waveform_signals": [
    "clk",
    "count",
    "empty",
    "full",
    "read_en",
    "read_ptr",
    "rst_n",
    "write_en",
    "write_ptr"
  ]
}
```

### Running the Unit & Safety Property Suite (25 Tests)
```powershell
python -m pytest -v
```

### Running the Paired Controlled Comparison (Baseline Full RCA vs. RCA-Reuse)
```powershell
python experiments/run_rca_vs_reuse_controlled_comparison.py
```

This runs a 25-manifestation stream across 5 hardware families, comparing Independent Full RCA against the RCA-Reuse pipeline on real RTL simulation traces.


---

## 8. Limitations & Scope

A complete list of research limitations is maintained in [docs/limitations.md](docs/limitations.md):

1. **Bug Resolution Unmeasured:** End-to-end bug resolution has not yet been directly compared against full RCA.
2. **Benchmark Scope:** Limited to five controlled RTL hardware families (`FIFO`, `AXI`, `FSM`, `UART`, `PIPELINE`) using controlled research fixtures.
3. **Adaptive Recall:** Adaptive boundaries demonstrate safety and false-reuse reduction, but do not improve recall over fixed-window controls.
4. **SoC-Level Scalability:** Multi-clock domains, hierarchy crossing, and million-cycle traces remain unvalidated.
5. **Cost Accounting:** Cost compression is derived from an analytical tool-call model, not physical LLM token or wall-clock logging.
6. **Not a Universal RCA Replacement:** Designed strictly as an upstream safety triage filter.

---

## 9. Repository Structure

```text
src/
  reuse/          Causal certificates, semantic validators, adaptive boundary/evidence code
  agent/          Baseline, constrained, and re-evaluation agent components
  tools/          RTL search, Icarus simulator wrapper, and VCD waveform extraction utilities
  evaluation/     Metrics and evaluation scoring
  reporting/      Plot generation utilities
  trajectory/     Agent trajectory schema and logging
scripts/          Smoke test runner, benchmark generators, and audit scripts
tests/            Unit tests for boundary detectors and safety validators
examples/         Self-contained demo scripts and minimal certificate fixtures
results/          Audited summary CSVs and experimental documentation
docs/             Architecture, methodology, limitations, audit reports, and comparisons
rtl/              Verilog designs and testbenches (raw VCDs/VVPs are gitignored)
```

---

## 10. Documentation Index

- [docs/architecture.md](docs/architecture.md): Component pipeline and certificate representations.
- [docs/methodology.md](docs/methodology.md): Experimental methodology, baselines, and safety checks.
- [docs/limitations.md](docs/limitations.md): Explicit research boundaries and unproven hypotheses.
- [docs/rca_vs_reuse.md](docs/rca_vs_reuse.md): Direct comparison of RCA vs. RCA-Reuse metrics, resolution, and costs.
- [docs/blind_test_audit.md](docs/blind_test_audit.md): Forensic audit of the 50-failure blind evaluation.
- [docs/reproducibility.md](docs/reproducibility.md): Reproducibility tier breakdown and command verification.

---

## License

Source code is released under the [MIT License](LICENSE).
