# RCA-Reuse: Verified Reuse of Hardware Root-Cause Knowledge

> A research prototype for verifying whether expensive hardware debugging root-cause analysis (RCA) explanations can be formalized as semantic certificates and safely reused across recurring failure manifestations.

---

## 1. Project Overview

Diagnosing failure manifestations in Register-Transfer Level (RTL) simulation is computationally expensive and engineer-intensive. When debugging an automated regression failure, engineers or AI agents iteratively inspect waveforms, trace signals across clock cycles, search source files, and test causal hypotheses.

When similar or structurally related bugs recur across design revisions, testing streams, or parameter variants, standard practice reruns the complete investigation from scratch. **RCA-Reuse** investigates whether the causal explanation produced by an initial root-cause analysis can be structured into a verifiable **semantic certificate** and safely reused for later failure manifestations, bypassing redundant debugging search without introducing unsafe diagnostic transfers.

---

## 2. Core Idea

Previous RCA knowledge is represented as formal **semantic certificates** and is reused only after passing an explicit **verification and trust gate**:

```text
RCA → Certificate → Verification / Trust Gate → Trusted Memory → Semantic Matching → Reuse
```

Rather than treating reuse as a syntactic or embedding-based similarity lookup, RCA-Reuse enforces that:
1. **Source Certificates Must Be Trusted:** An initial diagnosis must pass automated causal and structural verification before its certificate is admitted to memory.
2. **Target Traces Must Pass Formal Validation:** A target failure trace must satisfy the certificate's preconditions, protocol obligations, and observable anomaly signatures before diagnosis transfer occurs.
3. **Conservative Fallback on Ambiguity:** If evidence is incomplete, truncated, or inconsistent with the certificate, the system safely abstains and routes the failure to an independent fallback RCA investigation.

---

## 3. Architecture

The system coordinates deterministic hardware analysis, protocol obligations, and safety gating:

```text
                          ┌────────────────────────┐
                          │ Target Failure (Trace) │
                          └───────────┬────────────┘
                                      │
                                      ▼
                      ┌────────────────────────────────┐
                      │ 1. Adaptive Evidence Horizon   │
                      │    (Settlement Engine)         │
                      └───────────────┬────────────────┘
                                      │
                                      ▼
                      ┌────────────────────────────────┐
                      │ 2. Semantic Role Normalizer    │
                      │    (Canonical Hardware Roles)  │
                      └───────────────┬────────────────┘
                                      │
                                      ▼
                      ┌────────────────────────────────┐
                      │ 3. Modular Protocol Adapters   │
                      │    (FIFO, AXI, FSM, UART, Pipe)│
                      └───────────────┬────────────────┘
                                      │
                                      ▼
                      ┌────────────────────────────────┐
                      │ 4. V5 Safety & Trust Gate      │
                      │    (Final Validation Authority)│
                      └───────┬────────────────┬───────┘
                              │                │
            [Validation PASS] │                │ [FAIL / Insufficient]
                              ▼                ▼
                     ┌────────────────┐ ┌───────────────────────────┐
                     │   REUSE_RCA    │ │ FALLBACK_INDEPENDENT_RCA  │
                     │ (Bypass Search)│ │ (Run Autonomous RCA)      │
                     └────────────────┘ └───────────────────────────┘
```

### Key Architectural Pillars:

* **Deterministic Evidence:** Leverages verifiable RTL simulation outputs, deterministic testbench assertion triggers, and structured waveform slices rather than ungrounded textual summaries.
* **Waveform & Temporal Context:** Captures multi-cycle temporal causality, identifying the trigger cycle and tracking the settlement window across clock cycles.
* **Semantic Role Normalization:** Standardizes heterogeneous signal names across different design implementations into normalized `HardwareRole` enums (e.g., `count` and `fifo_count` $\rightarrow$ `OCCUPANCY_TRACKER`; `cnt` and `baud_cnt` $\rightarrow$ `BAUD_PRESCALER`) while strictly preventing role conflation.
* **Modular Protocol Adapters:** An extensible `ProtocolRegistry` provides dedicated protocol verifiers:
  - `FifoProtocolAdapter`: Evaluates occupancy conservation and pointer divergence.
  - `AxiProtocolAdapter`: Evaluates handshake stability and transfer completion contracts.
  - `FsmProtocolAdapter`: Evaluates state progress and transition deadlocks.
  - `UartProtocolAdapter`: Models bit-period prescaler timing and baud rollover contracts.
  - `PipelineProtocolAdapter`: Models pipeline stage retention and hazard stall drainage.
* **V5 Verification Gate:** A multi-layer trust gate (`SourceRCAVerifier`) ensuring that unverified, hallucinated, or ungrounded diagnoses cannot enter trusted memory.
* **V8 Unified Certificate Architecture:** A domain-independent 6-dimensional schema capturing root-cause identity, formal invariant obligations, temporal behavior, multi-stage evidence, competing hypothesis rejections, and trust audit trails.

---

## 4. Validated V8 Results

The V8 system was evaluated on an **immutable, frozen 25-case evaluation stream** comprising 5 hardware design families (`FIFO`, `AXI`, `FSM`, `UART`, `PIPELINE`), including 5 source cases, 10 valid reuse targets, 5 adversarial same-symptom negative controls, and 5 truncated/incomplete waveform stress cases.

Controlled head-to-head comparison between the baseline reuse architecture (Control A) and the V8 Unified Semantic Architecture (Control B) demonstrated:

| Metric | Control A (V7 + V5 Baseline) | Control B (V7 + V8 Semantic Reuse) | Impact / Delta |
|---|:---:|:---:|:---:|
| **Trusted Source Certificates** | 4 / 5 (80.0%) | **5 / 5 (100.0%)** | +25.0% trusted ingestion |
| **Autonomous Reuses Applied** | 3 / 20 (15.0%) | **7 / 20 (35.0%)** | +133.3% transfer rate |
| **Correct Autonomous Reuses** | 3 / 20 (15.0%) | **7 / 20 (35.0%)** | +133.3% correct reuses |
| **False Reuses Observed** | **0** | **0** | **0 false reuses observed** |
| **Reuse Decision Precision** | **100.0% (3/3)** | **100.0% (7/7)** | Preserved at 100.0% |
| **Negative Target Rejection Rate** | **100.0% (10/10)** | **100.0% (10/10)** | Preserved at 100.0% |
| **RCA Investigations Avoided** | 3 | **7** | 7 full searches avoided |
| **LLM Inference Token Reduction** | 19.6% | **22.0%** | ~22% token reduction |
| **Wall-Clock Latency Reduction** | 11.3% | **24.7%** | ~24.7% latency reduction |

### Critical Safety Findings:
- **0 false reuses were observed on the frozen evaluation.** In every target arrival where reuse was executed, the transferred root cause matched the ground truth defect signal exactly.
- **10/10 non-reusable cases safely rejected.** All 5 adversarial same-symptom negatives and all 5 incomplete/truncated waveforms were safely routed to fallback independent RCA.
- *Note:* Hardware verification involves complex state spaces; these empirical results demonstrate that 0 false reuses were observed on the frozen benchmark under formal invariant triage.

---

## 5. Research Progression (V1 – V8)

The project advanced through 8 empirical milestones:

* **V1 / V2 — Controlled Baselines & Bias Removal:** Established the initial paired evaluation methodology and eliminated prompt formatting bias.
* **V3 / V4 — Deterministic RTL & Temporal Evidence:** Introduced simulator tool integration, multi-cycle waveform query tools, and execution traces into the agentic loop.
* **V5 — Source Verification & Safety Gate:** Implemented `SourceRCAVerifier`, preventing untrusted initial analyses from poisoning downstream memory and establishing the multi-layer target invariant validator.
* **V6 / V7 — Learned Causal Discrimination:** Developed canonical training datasets with zero-leakage guarantees and fine-tuned open-weight language models on causal hardware failure isolation.
* **V7.1 — Systems Bottleneck Analysis:** Audited end-to-end failure modes, identifying schema brittleness, literal signal-name coupling, UART extractor omission, and second-pass ingestion drops as downstream bottlenecks.
* **V8 — Unified Semantic Certificate Architecture:** Introduced canonical semantic roles, modular protocol adapters, deterministic source ingestion, and evidence-aware adaptive settlement, unlocking a +133% increase in autonomous reuse with 0 false reuses observed.

---

## 6. Repository Structure

```text
hardware-debug-failure-learning/
├── docs/                   # Experiment reports, bottleneck audits, and methodology
│   ├── V8_BASELINE.md
│   ├── V8_FINAL_REPORT.md
│   ├── V7_1_FINAL_REPORT.md
│   ├── FROZEN_25_CASE_INTEGRITY.md
│   └── ...
├── experiments/            # Controlled comparison runners and benchmark harnesses
│   ├── run_rca_vs_reuse_controlled_comparison.py  # Frozen 25-case benchmark
│   └── ...
├── results/                # Recorded cost analysis and frozen evaluation logs
│   └── cost_analysis/
│       ├── v8_end_to_end_comparison.json
│       ├── v8_end_to_end_comparison.csv
│       └── ...
├── rtl/                    # Verilog designs and testbenches for evaluation stream
│   ├── designs/
│   └── testbenches/
├── scripts/                # Benchmark generators, dataset builders, and audits
├── src/                    # Core library implementation
│   ├── agent/              # Multi-step agentic RCA loop and LLM providers
│   ├── evaluation/         # Metrics, paired evaluation harness, and V8 replay
│   ├── reuse/              # Unified certificates, protocol adapters, role normalizer
│   └── tools/              # Simulation, waveform parsing, and search tools
├── tests/                  # Unit and integration test suites
└── pyproject.toml          # Package configuration
```

---

## 7. Getting Started & Reproducibility

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Icarus Verilog (`iverilog`) for simulation (optional for offline replay)

### Installation
```bash
# Clone the repository
git clone https://github.com/VaradaGovind/hardware-debug-failure-learning.git
cd hardware-debug-failure-learning

# Initialize a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install package in editable mode
pip install -e .
pip install pytest
```

### Running Tests
```bash
# Execute the core unit and generalization test suites (53 tests)
pytest tests/test_v8_unit.py tests/test_v8_generalization.py tests/test_source_rca_verifier.py tests/test_safety_properties.py tests/test_adaptive_boundary.py tests/test_certificate_store.py tests/test_rca_vs_reuse_harness.py tests/test_agentic_rca.py
```

### Deterministic V8 Offline Replay
To reproduce the V8 results without requiring GPU access or local model weights:
```bash
python src/evaluation/v8_offline_replay.py
```
This executes the V8 unified semantic certificate store and adaptive settlement engine against the frozen 25-case stream, printing the exact comparison metrics reported above.
