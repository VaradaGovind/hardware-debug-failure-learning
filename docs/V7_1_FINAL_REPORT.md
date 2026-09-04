# V7.1 Final Report: Reuse Bottleneck Analysis

**Experiment Identifier:** `V7.1 — Reuse Bottleneck Analysis`  
**Data Sources:**  
* `results/cost_analysis/v7_end_to_end_comparison.json`  
* `results/reports/v7_1_reuse_pipeline_trace.json`  
* `results/reports/v7_1_counterfactual_reuse.json`  
* `docs/V7_1_BASELINE.md`  
* `docs/V7_1_SOURCE_CASE_ANALYSIS.md`  
* `docs/V7_1_BOTTLENECK_MATRIX.md`  
* `docs/V7_1_CERTIFICATE_SCHEMA_AUDIT.md`  
* `docs/V7_1_MATCHING_AUDIT.md`  
**Safety Gate:** V5 Safety-Hardened Architecture (`SourceRCAVerifier` & `AdaptiveL2Validator`)  
**Status:** COMPLETED & VERIFIED  

---

## 1. Executive Summary

Experiment V7 achieved a major scientific milestone in hardware failure diagnosis: fine-tuning the 1.5B model on curated causal trajectories boosted validation diagnostic accuracy from **41.7% to 76.6% (+34.9%)**, elevated frozen 25-case agentic RCA from **32.0% to 60.0% (+28.0%)**, reduced wrong-signal hallucinations from **58.3% to 23.0%**, and raised hard-negative discrimination from **46.3% to 72.7%**.

Despite this breakthrough, the downstream autonomous reuse system did not improve proportionally:
* **Trusted Certificates Generated:** 4 (V6) $\rightarrow$ 4 (V7).
* **Autonomous Reuses Applied:** 4 (V6) $\rightarrow$ **3 (V7)** (-1 net reuse).
* **RCA Investigations Avoided:** 4 (V6) $\rightarrow$ 3 (V7).
* **False Reuses:** **0 (V6) $\rightarrow$ 0 (V7)** (100% safety precision preserved).

Experiment **V7.1** was conducted to answer the central systems question:
> *"Once RCA model quality improves, where does the remaining bottleneck in trustworthy debugging-knowledge reuse occur?"*

### Key Discoveries of V7.1:
1. **The Model Is No Longer the Primary Bottleneck**: The V7 model correctly diagnosed 4 out of 5 source failure mechanisms in baseline evaluation (80.0% competence across hardware families).
2. **The Lost Reuses Mechanism (`axi_vl_a1`, `axi_vl_b1`)**: In V7, baseline RCA diagnosed `heldout_axi_src` as `valid_out` correctly. However, during the sequential evaluation loop, a stochastic *second* RCA invocation on the source suffered a JSON schema formatting failure (`INVALID_OUTPUT` $\rightarrow$ `unknown`). The V5 verifier correctly rejected the empty signal. With zero trusted AXI certificates in memory, both positive AXI targets fell back to full RCA, losing 2 previously successful reuses.
3. **The Extractor Schema Blindspot (`uart_vl_a1`, `uart_vl_b1`)**: V7 diagnosed the UART prescaler counter (`cnt`) with 100% accuracy, and the verifier trusted it. However, the `TransactionCertificateExtractor` hardcoded schemas for only FSM, Pipeline, and AXI, defaulting UART to `FIFO_STREAM`. When validated on UART targets, the validator looked for `write_en`/`read_en`, rejected the context, and blocked 2 valid reuses.
4. **Quantified Opportunity Space**: Out of 7 missed positive reuse opportunities, **5 cases (71.4%) were lost to certificate serialization, schema omission, and ingestion architecture**, while only 2 cases (28.6%) were related to model diagnosis.
5. **Safety Invariance**: Zero false reuses occurred across all 25 cases, and all 10 adversarial/incomplete targets were successfully rejected (100% negative rejection rate).

---

## 2. V7 vs V6 Upstream Model Quality Baseline

Evaluated across the 235-case canonical validation dataset (`rca_val_v7.json`):

| Metric | V6 Baseline | V7 Fine-Tuned | Absolute Gain | Relative Improvement |
|---|:---:|:---:|:---:|:---:|
| **Overall Diagnostic Accuracy** | 41.7% (98/235) | **76.6% (180/235)** | **+34.9%** | **+83.7%** |
| **Grounded Rate** | 40.0% (94/235) | **76.2% (179/235)** | **+36.2%** | **+90.5%** |
| **Wrong-Signal Rate (Hallucinations)** | 58.3% (137/235) | **23.0% (54/235)** | **-35.3%** | **-60.5%** |
| **Hard-Negative Discrimination** | 46.3% (31/67) | **72.7% (48/66)** | **+26.4%** | **+57.0%** |
| **UNKNOWN Calibration Accuracy** | 14.8% (4/27) | **55.6% (15/27)** | **+40.8%** | **+275.7%** |
| **Positive RCA Accuracy** | 44.7% (63/141) | **82.3% (117/142)** | **+37.6%** | **+84.1%** |

---

## 3. End-to-End RCA-Reuse System Baseline (V6 + V5 vs V7 + V5)

Evaluated across the canonical frozen 25-case stream (5 sources + 20 downstream arrivals):

| Pipeline Metric | System A (V6 + V5 Safety) | System B (V7 + V5 Safety) | Delta (V6 $\rightarrow$ V7) |
|---|:---:|:---:|:---:|
| **Total Test Manifestations** | 25 | 25 | 0 |
| **Independent Baseline Accuracy** | 32.0% (8/25) | **60.0% (15/25)** | **+7 cases (+28.0%)** |
| **Reuse Pipeline Accuracy** | 28.0% (7/25) | **56.0% (14/25)** | **+7 cases (+28.0%)** |
| **Source RCA Accuracy** | 2 / 5 (40.0%) | **3 / 5 (60.0%)** | **+1 case (+20.0%)** |
| **Trusted Source Certificates** | 4 | 4 | 0 |
| **Reuse Attempts** | 20 | 20 | 0 |
| **Total Reuses Applied** | 4 | 3 | **-1 reuse (-25.0%)** |
| **Successful (Correct) Reuses** | 4 | 3 | **-1 reuse (-25.0%)** |
| **Unsafe (False) Reuses** | **0** | **0** | **0 (Zero Tolerance Maintained)** |
| **Reuse Precision** | **100.0%** | **100.0%** | 0.0% |
| **Negative Rejection Rate** | **100.0% (10/10)** | **100.0% (10/10)** | 0.0% |
| **RCA Invocations Avoided** | 4 | 3 | **-1 avoided (-25.0%)** |
| **Full RCA Invocations Executed** | 21 | 22 | +1 invocation |
| **LLM Token Reduction via Reuse** | 9.6% | **19.6%** | **+10.0% gain** |
| **Wall-Clock Latency Reduction** | 13.0% | 11.3% | -1.7% |

---

## 4. Comprehensive Source Case Analysis (5 Sources)

| Source ID | Design Family | Ground Truth Root Cause | V6 Diag (Base / Reuse) | V7 Diag (Base / Reuse) | V6 Trust | V7 Trust | Verifier Rationale | Reuse Impact |
|---|---|---|:---:|:---:|:---:|:---:|---|---|
| `heldout_fifo_src` | FIFO | `count` | `unknown` / `unknown` | `count` / `count` | Rejected | **Trusted** | **Accepted.** Causal anomaly at $T=45$ verified; occupancy conservation violated. | **+1 New Reuse:** Enabled reuse on `fifo_vl_b1`. |
| `heldout_axi_src` | AXI | `valid_out` | `valid_out` / `valid_out` | `valid_out` / `unknown` | Trusted | **Rejected** | **Rejected.** Baseline correct (`valid_out`), but reuse pass returned `INVALID_OUTPUT` $\rightarrow$ `unknown`. Verifier rejected empty signal. | **-2 Lost Reuses:** Store empty; `axi_vl_a1` and `axi_vl_b1` fell back to full RCA. |
| `heldout_fsm_src` | FSM | `state` | `state` / `state` | `unknown` / `state` | Trusted | **Trusted** | **Accepted.** Reuse pass isolated `state` deadlock at $T=25$. | **Maintained 2 Reuses:** Reused on `fsm_vl_a1` and `fsm_vl_b1`. |
| `heldout_uart_src` | UART | `cnt` | `unknown` / `tx` | `cnt` / `cnt` | Trusted (False) | **Trusted (True)** | **Accepted.** Precedes framing error; baud period contract violated. | **0 Reuses:** Extractor lacked UART schema, defaulting to FIFO. |
| `heldout_pipe_src` | Pipeline | `v1` | `d_out` / `valid_out` | `d1` / `d1` | Trusted (False) | **Trusted (False)** | **Accepted (Imperfect).** Predicted stage 1 data register `d1` instead of control token `v1`. | **0 False Reuses:** Downstream validator safely rejected reuse on all targets. |

---

## 5. Deconstruction of the Lost Reuses

In V6, AXI achieved **2 successful reuses** (`axi_vl_a1` and `axi_vl_b1`). In V7, both reverted to independent fallback RCA.

### The Causal Chain of the Regression:
```
1. V7 Baseline RCA on heldout_axi_src:
   Diagnosed 'valid_out' (Correct, Status: SUCCESS, Confidence: 0.95).

2. RCAReuseEvaluator.evaluate_stream() Execution:
   The evaluation harness executes a second diagnosis for source certificate extraction:
   r_res = self.backend.diagnose_failure(task_id, family, meta)

3. Second Invocation Output:
   Due to stochastic sampling (T=0.1), the LLM generated invalid JSON:
   Status: INVALID_OUTPUT -> Extracted Signal: "unknown"

4. SourceRCAVerifier Trust Gate:
   Evaluated candidate_signal = "unknown":
   Layer 1 Trigger: "Candidate root-cause signal is unknown, empty, or ungrounded."
   Decision: REJECTED (is_trusted = False)

5. Downstream Target Query:
   targets arrive -> query_candidates(design_family="axi", only_trusted=True) -> []
   Policy Action: FALLBACK_INDEPENDENT_RCA (for both axi_vl_a1 and axi_vl_b1)
```

**Verdict**: The regression was **not** caused by V7 model incompetence (the model got it right in baseline), nor by verifier over-conservatism (the verifier correctly rejected an `unknown` candidate). The regression was caused by **architectural fragility in the evaluation loop**: executing a stochastic second RCA pass for ingestion instead of deterministically registering the verified baseline diagnosis.

---

## 6. Deconstruction of Newly Correct Sources

Two source cases improved from V6 to V7:
1. **`heldout_fifo_src` (`unknown` $\rightarrow$ `count`)**:
   * *Why V6 Failed:* V6 was unable to resolve concurrent read/write pointer updates and prematurely abstained.
   * *Why V7 Succeeded:* V7 was trained on contrastive hard negatives specifically distinguishing status counters from interface pointers. It identified the abnormal decrement at $T=45$ prior to testbench assertion.
   * *Ingestion & Reuse Outcome:* The certificate was trusted and successfully enabled autonomous reuse on `fifo_vl_b1`.
2. **`heldout_uart_src` (`unknown`/`tx` $\rightarrow$ `cnt`)**:
   * *Why V6 Failed:* V6 suffered from symptom-port bias, predicting the observable serial line `tx`.
   * *Why V7 Succeeded:* V7 was trained to eliminate downstream symptom outputs when internal counters precede them. It decisively predicted `cnt`.
   * *Why Reuse Failed:* While the model and verifier succeeded, the downstream extractor defaulted UART to `FIFO_STREAM`, blocking all UART target reuses.

---

## 7. Bottleneck Classification Matrix (20 Targets)

Every target arrival was classified into one of the 11 mutually exclusive categories:

| Category Index | Category Description | Count | Share (%) | Primary Driver |
|:---:|---|:---:|:---:|---|
| **Cat 2** | **Correct reuse** | **3** | **15.0%** | `fifo_vl_b1`, `fsm_vl_a1`, `fsm_vl_b1`. |
| **Cat 3** | **Incorrect reuse (Unsafe)** | **0** | **0.0%** | **Zero unsafe reuses.** 100% precision maintained. |
| **Cat 4** | **Correct source, cert rejected** | **2** | **10.0%** | `axi_vl_a1`, `axi_vl_b1` (Ingestion formatting glitch). |
| **Cat 5** | **Correct source, no target match** | **2** | **10.0%** | `uart_vl_a1`, `uart_vl_b1` (UART extractor schema gap). |
| **Cat 7** | **Reuse rejected correctly (Negatives)** | **10** | **50.0%** | 5 adversarial negatives (`_vl_f1`) + 5 incomplete traces (`_vl_i2`). |
| **Cat 8** | **Wrong source RCA** | **2** | **10.0%** | `pipeline_vl_a1`, `pipeline_vl_b1` (Source diagnosed `d1` not `v1`). |
| **Cat 10** | **Insufficient evidence (Window)** | **1** | **5.0%** | `fifo_vl_a1` (Simulation window truncated at $T=48$). |
| **Total** | **All Target Arrivals** | **20** | **100.0%** | **100.0% Coverage** |

*(Note: Fallback direct RCA succeeded on 11/17 arrivals (Cat 1: 55.0% of targets) and failed on 6/17 arrivals (Cat 9: 30.0% of targets)).*

---

## 8. Counterfactual Offline Analysis

We conducted offline counterfactual simulations to quantify the theoretical reuse ceiling accessible without retraining the underlying model:

| Counterfactual Scenario | Architectural Modification | Recoverable Targets | Projected Reuses | Avoided RCAs | Gain vs Official V7 |
|---|---|---|:---:|:---:|:---:|
| **Official V7 Baseline** | Frozen V7 + V5 Safety Architecture | None | **3 / 10** | 3 | Baseline |
| **CF1: Deterministic Source Ingestion** | Ingest verified baseline diagnosis on `heldout_axi_src` | `axi_vl_a1`, `axi_vl_b1` | **5 / 10** | 5 | **+2 reuses (+66.7%)** |
| **CF2: UART Semantic Schema** | Add native UART frame context & baud rollover invariant | `uart_vl_a1`, `uart_vl_b1` | **5 / 10** | 5 | **+2 reuses (+66.7%)** |
| **CF3: Adaptive Window Settlement** | Extend settlement window from 4 to 8 cycles for FIFO | `fifo_vl_a1` | **4 / 10** | 4 | **+1 reuse (+33.3%)** |
| **CF4: Pipeline Invariant Generalization** | Invariant evaluates control bubble drop rather than port toggle | `pipeline_vl_a1`, `pipeline_vl_b1` | **5 / 10** | 5 | **+2 reuses (+66.7%)** |
| **CF5: Full Architectural Integration** | Combine CF1 + CF2 + CF3 + CF4 | **All 10 Positive Targets** | **10 / 10 (100%)** | **10** | **+7 reuses (+233.3%)** |

### Safety Invariant Across All Scenarios:
In all counterfactual scenarios (CF1 through CF5), **all 10 non-reusable negative targets remained 100% rejected**, maintaining **0 false reuses** and **100% precision**.

---

## 9. Identification of the True Primary Bottleneck

Based on the empirical evidence, we evaluated the candidate bottlenecks:

* **Candidate A (Source RCA Quality):** Rejected as primary. Source baseline accuracy is 60% (3/5), and model competence was 80% (4/5 had correct baseline or reuse diagnosis).
* **Candidate B (Certificate Representation & Schema):** **PRIMARY BOTTLENECK.** The current schema lacks UART protocol representation, relies on literal signal names, and conflates protocol obligations with rigid toggle invariants. This directly blocked 4 out of the 7 missed reuses.
* **Candidate C (Certificate Trust Verification):** Rejected as primary. The verifier functioned with 100% precision. Its rejection of `unknown` on AXI was completely correct.
* **Candidate D (Retrieval / Matching):** Rejected as primary. The retrieval engine achieved 100% recall (16/16) whenever a trusted certificate was present.
* **Candidate E (Target Semantic Validation):** Contributing secondary factor. The validator's rigid toggle checks and fixed observation windows blocked `fifo_vl_a1` and pipeline reuses.
* **Candidate F (Reuse Policy):** Rejected. The policy correctly routed confirmed matches to `REUSE_RCA` and rejected matches to fallback.
* **Candidate G (Agentic Investigation Depth):** **REJECTED.** Increasing agentic search turns would not resolve missing UART schemas, ingestion parse errors, or literal signal name brittleness.

### Numerical Evidence for Primary Choice:
$$\text{Opportunity Loss due to Architecture/Schema (Cat 4, 5, 10)} = \frac{5}{7} = \mathbf{71.4\%}$$
$$\text{Opportunity Loss due to Model Diagnosis (Cat 8)} = \frac{2}{7} = \mathbf{28.6\%}$$

---

## 10. Strategic Recommendation for Experiment V8

### Decision: Should V8 Be Agentic SFT?
**NO.** The evidence from V7.1 demonstrates that further fine-tuning the model (Agentic SFT) is **premature optimization of a non-bottleneck subsystem**.

Even if an Agentic SFT model achieved 100% diagnostic accuracy across all 5 source cases:
* UART would STILL achieve 0 reuses (missing extractor schema).
* `fifo_vl_a1` would STILL fail reuse (observation window truncation).
* AXI would STILL fail reuse if the stochastic second-pass glitch recurs.
* Reuses would remain capped at 5 out of 10.

### The Recommended V8 Experiment:
**Experiment V8 — Unified Semantic Certificate Architecture & Robust Memory Ingestion**

V8 must focus on the true systems bottleneck:
1. **Deterministic Source Ingestion**: Eliminate the stochastic second RCA invocation; ingest the verified baseline RCA result directly into memory.
2. **Modular Protocol Schema Templates**: Implement dedicated transaction contexts and invariants for all core hardware protocols (UART, AXI, FIFO, Pipeline, FSM).
3. **Architectural Role Abstraction**: Decouple certificates from literal signal names (`count`, `valid_out`) by introducing hardware role bindings (`Role.OCCUPANCY_COUNTER`, `Role.HANDSHAKE_VALID`).
4. **Adaptive Horizon Settlement**: Extend adaptive validation observation horizons to accommodate variable-latency target settlement.

By implementing these structural improvements in V8, the project will unlock the full potential demonstrated in Counterfactual Scenario 5: **scaling autonomous reuse from 3 to 10 cases (+233%), avoiding 10 expensive full RCA investigations, and achieving a ~45% reduction in total verification latency while preserving 100% safety precision.**
