# Experiment V9 Scientific Assessment: Comprehensive Verification & Audit Report

**Document Identifier:** `docs/V9_SCIENTIFIC_ASSESSMENT.md`  
**Date:** September 3, 2026  
**Status:** COMPLETED, AUDITED & FROZEN  
**Safety Guarantee:** **0 false reuses were observed on the frozen evaluation.**  
**Baseline Reference:** Experiment V8 (`results/cost_analysis/v8_end_to_end_comparison.json`)  
**Evaluated Artifact:** Experiment V9 (`results/cost_analysis/v9_end_to_end_comparison.json`)  
**Case Transition Verification Artifact:** `results/reports/v9_case_transitions_verified.json`  
**Leakage Verification Artifact:** `results/reports/v9_leakage_verification.json`  

---

## 1. Executive Summary & Verification Purpose

Following the completion of **Experiment V9 (Agentic Supervised Fine-Tuning)**, this audit was conducted to independently verify whether V9 represents a genuine, generalizable scientific breakthrough or a localized pattern memorization.

Entering V9, the established operational baseline was **Experiment V8**, which achieved:
- 68.0% reuse pipeline accuracy (17/25)
- 7/20 autonomous reuses with 100% precision
- 10/10 negative target rejection
- 22.0% token reduction and 24.7% latency reduction
- A single source failure: `heldout_pipe_src` where data register `d1` was chosen instead of control token `v1`.

### Headline Verification Verdict:
1. **The Targeted Case Succeeded**: On `heldout_pipe_src`, V9 successfully flipped the diagnosis from `d1` (incorrect) to **`v1`** (correct), and the V8 safety verifier generated a trusted `PIPELINE_TOKEN` certificate.
2. **Generalization Failed (0/5)**: On the 5-case Pipeline Generalization Suite (unseen 4-stage pipelines, skid buffers, aliased naming conventions), V9 scored **0/5 (0.0%)**.
3. **Training Data RTL Leakage Discovered**: While `heldout_pipe_src` as a task ID was strictly excluded, byte-for-byte identical Verilog RTL was present in the training set under non-heldout benchmark catalog variants (`pipeline_a1.v`, `pipeline_a2.v`, `pipeline_a3.v`). The model memorized the `pipeline_a` token pattern rather than learning autonomous causal reasoning.
4. **Aggregate Regressions in Reuse & Accuracy**: Multi-turn agentic SFT introduced output format fragility (`INVALID_OUTPUT` rate increased to 16%), causing source failures on `heldout_fifo_src` and `heldout_uart_src`. As a result, autonomous reuses dropped from **7/20 in V8 to 4/20 in V9**, and overall stream accuracy dropped from **68.0% in V8 to 44.0% in V9**.
5. **Zero False Reuses Preserved**: The V5 safety architecture held flawlessly: **0 false reuses were observed on the frozen evaluation**, with 100.0% precision (4/4) and 100.0% negative rejection (10/10).

---

## 2. Complete V8 vs. V9 Operational Comparison

All numbers are extracted directly from `results/cost_analysis/v8_end_to_end_comparison.json` and `results/cost_analysis/v9_end_to_end_comparison.json`:

| Metric Category | Metric Name | Experiment V8 (Control B) | Experiment V9 (Agentic SFT) | Delta / Assessment |
|---|---|:---:|:---:|---|
| **Model / RCA** | Baseline Independent RCA Accuracy | 60.0% (15/25) | 60.0% (15/25) | Parity (15/25) |
| | Reuse Stream Diagnostic Accuracy | **68.0% (17/25)** | 44.0% (11/25) | **-24.0% (Regression)** |
| | Source RCA Accuracy (Reuse Stream) | **80.0% (4/5)** | 60.0% (3/5) | FIFO failed (Invalid Output) |
| | Source RCA Accuracy (Baseline Stream) | 80.0% (4/5) | 80.0% (4/5) | Parity (Pipe solved, UART regressed) |
| | `heldout_pipe_src` Diagnosis | `d1` (FAIL) | **`v1` (CORRECT)** | **Resolved (`d1 → v1`)** |
| | Pipeline Family Accuracy (Baseline) | 40.0% (2/5) | **80.0% (4/5)** | **+40.0% in Baseline** |
| | Pipeline Family Accuracy (Reuse) | 40.0% (2/5) | 60.0% (3/5) | +20.0% in Reuse |
| | FIFO Family Accuracy (Reuse) | **80.0% (4/5)** | 0.0% (0/5) | -80.0% (Format / Schema failure) |
| | AXI Family Accuracy (Reuse) | 60.0% (3/5) | 60.0% (3/5) | Parity |
| | FSM Family Accuracy (Reuse) | 80.0% (4/5) | 60.0% (3/5) | -20.0% |
| | UART Family Accuracy (Reuse) | **80.0% (4/5)** | 40.0% (2/5) | -40.0% (Stochastic hallucination) |
| | Invalid Output Rate | **0.0% (0/25)** | 16.0% (4/25) | **+16.0% formatting fragility** |
| | UNKNOWN Diagnosis Rate | 0.0% (0/25) | 16.0% (4/25) | +16.0% (Fallback to unknown) |
| | Wrong Signal Rate | **32.0% (8/25)** | 40.0% (10/25) | +8.0% |
| **Reuse** | Trusted Source Certificates | **5 / 5 (100.0%)** | 4 / 5 (80.0%) | FIFO ungrounded |
| | Autonomous Reuses Applied | **7 / 20 (35.0%)** | 4 / 20 (20.0%) | **-3 reuses applied** |
| | Correct Autonomous Reuses | **7 / 20 (35.0%)** | 4 / 20 (20.0%) | **-3 correct reuses** |
| | Unsafe Autonomous Reuses (FRR) | **0 / 20 (0.0%)** | **0 / 20 (0.0%)** | **0 false reuses observed** |
| | Reuse Precision | **100.0% (7/7)** | **100.0% (4/4)** | **100.0% preserved** |
| | Negative Target Rejection | **100.0% (10/10)** | **100.0% (10/10)** | **100.0% preserved** |
| | RCA Investigations Avoided | **7** | 4 | -3 avoided investigations |
| | Full RCA Invocations Required | **18** | 21 | +3 invocations required |
| | Target Fallback Rate | **65.0% (13/20)** | 80.0% (16/20) | +15.0% fallback |
| **Efficiency** | Total LLM Tokens (Baseline Stream) | 83,238 | 83,238 (Config proxy) | Parity |
| | Total LLM Tokens (Reuse Stream) | 64,896 | NOT RECORDED | Unavailable in local proxy |
| | Token Reduction | 22.0% | NOT RECORDED | Unavailable in local proxy |
| | Total Wall Latency (Baseline Stream) | 680,277 ms | 627,650 ms | Comparable |
| | Total Wall Latency (Reuse Stream) | 512,519 ms | 699,504 ms | Longer due to agentic tool turns |
| | Latency Reduction | 24.7% | -11.4% | Increased agentic turns |

---

## 3. Complete 25-Case Transition Audit

The verified per-case transition records from `results/reports/v9_case_transitions_verified.json`:

| Case | Target ID | Family | Ground Truth | V8 Diag | V9 Diag | V8 Cor | V9 Cor | V8 Reused | V9 Reused | V8 Decision | V9 Decision | Transition Classification |
|:---:|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **1** | `heldout_fifo_src` | fifo | `count` | `count` | `unknown` | True | False | False | False | SOURCE_ESTABLISHED | SOURCE_ESTABLISHED | **correct → wrong** (Invalid Output) |
| **2** | `fifo_vl_a1` | fifo | `count` | `count` | `read_ptr` | True | False | False | False | FAIL | INSUFFICIENT | **correct → wrong** (Reasoning error) |
| **3** | `fifo_vl_b1` | fifo | `count` | `count` | `read_pointer` | True | False | **True** | **False** | PASS | INSUFFICIENT | **correct-reuse → no-reuse** |
| **4** | `fifo_vl_f1` | fifo | `write_ptr` | `count` | `read_ptr` | False | False | False | False | FAIL | INSUFFICIENT | correct rejection (wrong → wrong) |
| **5** | `fifo_vl_i2` | fifo | `count` | `count` | `unknown` | True | False | False | False | FAIL | INSUFFICIENT | **correct → wrong** (Invalid Output) |
| **6** | `heldout_axi_src` | axi | `valid_out` | `valid_out` | `valid_out` | True | True | False | False | SOURCE_ESTABLISHED | SOURCE_ESTABLISHED | correct → correct |
| **7** | `axi_vl_a1` | axi | `valid_out` | `valid_out` | `valid_out` | True | True | **True** | **True** | PASS | PASS | correct-reuse → correct-reuse |
| **8** | `axi_vl_b1` | axi | `valid_out` | `valid_out` | `valid_out` | True | True | **True** | **True** | PASS | PASS | correct-reuse → correct-reuse |
| **9** | `axi_vl_f1` | axi | `ready_out` | `valid_out` | `valid_out` | False | False | False | False | FAIL | FAIL | correct rejection (wrong → wrong) |
| **10** | `axi_vl_i2` | axi | `valid_out` | `ready_in` | `unknown` | False | False | False | False | FAIL | INSUFFICIENT | correct rejection (wrong → wrong) |
| **11** | `heldout_fsm_src` | fsm | `state` | `state` | `state` | True | True | False | False | SOURCE_ESTABLISHED | SOURCE_ESTABLISHED | correct → correct |
| **12** | `fsm_vl_a1` | fsm | `state` | `state` | `state` | True | True | **True** | **True** | PASS | PASS | correct-reuse → correct-reuse |
| **13** | `fsm_vl_b1` | fsm | `state` | `state` | `state` | True | True | **True** | **True** | PASS | PASS | correct-reuse → correct-reuse |
| **14** | `fsm_vl_f1` | fsm | `done` | `state` | `state` | False | False | False | False | FAIL | FAIL | correct rejection (wrong → wrong) |
| **15** | `fsm_vl_i2` | fsm | `state` | `state` | `start` | True | False | False | False | FAIL | INSUFFICIENT | **correct → wrong** (Guessed stimulus) |
| **16** | `heldout_uart_src` | uart | `cnt` | `cnt` | `tok` | True | False | False | False | SOURCE_ESTABLISHED | SOURCE_ESTABLISHED | **correct → wrong** (Hallucination) |
| **17** | `uart_vl_a1` | uart | `cnt` | `cnt` | `cnt` | True | True | **True** | **False** | PASS | INSUFFICIENT | **correct-reuse → no-reuse** |
| **18** | `uart_vl_b1` | uart | `cnt` | `cnt` | `start` | True | False | **True** | **False** | PASS | INSUFFICIENT | **correct-reuse → no-reuse** |
| **19** | `uart_vl_f1` | uart | `tx` | `cnt` | `cnt` | False | False | False | False | INSUFFICIENT | INSUFFICIENT | correct rejection (wrong → wrong) |
| **20** | `uart_vl_i2` | uart | `cnt` | `cnt` | `cnt` | True | True | False | False | INSUFFICIENT | INSUFFICIENT | correct rejection (correct → correct) |
| **21** | `heldout_pipe_src` | pipe | `v1` | `d1` | `v1` | False | **True** | False | False | SOURCE_ESTABLISHED | SOURCE_ESTABLISHED | **wrong → correct (BREAKTHROUGH)** |
| **22** | `pipeline_vl_a1` | pipe | `v1` | `d1` | `unknown` | False | False | False | False | FAIL | FAIL | wrong → wrong (Invalid Output in fallback)|
| **23** | `pipeline_vl_b1` | pipe | `v1` | `v1` | `v1` | True | True | False | False | FAIL | FAIL | correct → correct |
| **24** | `pipeline_vl_f1` | pipe | `d1` | `v1` | `d1` | False | **True** | False | False | FAIL | FAIL | **wrong → correct** (Hazard separated) |
| **25** | `pipeline_vl_i2` | pipe | `v1` | `v1` | `d1` | True | False | False | False | FAIL | INSUFFICIENT | **correct → wrong** (Truncated trace) |

### Transition Summary Counts:
- **wrong → correct**: **2 cases** (`heldout_pipe_src`, `pipeline_vl_f1` — both in Pipeline family!)
- **correct → wrong**: **8 cases** (Cases 1, 2, 3, 5, 15, 16, 18, 25)
- **correct → correct**: **9 cases** (Cases 6, 7, 8, 11, 12, 13, 20, 23)
- **wrong → wrong**: **6 cases** (Cases 4, 9, 10, 14, 19, 22)
- **no-reuse → correct-reuse**: **0 cases**
- **correct-reuse → no-reuse**: **3 cases** (`fifo_vl_b1`, `uart_vl_a1`, `uart_vl_b1`)
- **unsafe reuse**: **0 cases (0.0% false reuse rate)**
- **correct rejection**: **10 cases (100.0% negative rejection rate)**

---

## 4. Why `heldout_pipe_src` Did Not Unlock Downstream Reuse

Although `heldout_pipe_src` was solved and generated a verified `PIPELINE_TOKEN` certificate, targets `pipeline_vl_a1` and `pipeline_vl_b1` fell back to independent RCA.

The reason was determined by inspecting the frozen V8 adapter code (`src/reuse/v8_protocol_adapters.py:624`):
```python
# Check for control token drop during stall
token_drop_cycles = []
for i in range(1, len(cycle_states)):
    prev_s = cycle_states[i - 1]
    curr_s = cycle_states[i]
    if prev_s.get("rst_n", 1) == 0:
        continue

    # Stall drop condition
    if prev_s.get("valid_in") == 1 and curr_s.get(token_sig) == 0:
        token_drop_cycles.append(i)

if not token_drop_cycles:
    return {
        "decision": "FAIL",
        "stage": "PROTOCOL_OBLIGATION",
        "reason": f"Pipeline control token '{token_sig}' was correctly preserved during stall; defect absent."
    }
```
In `pipeline_vl_b1_tb.v`, the stimulus applied `valid_in = 1` for 10ns, and deasserted `valid_in = 0` at $T=40$. When posedge clock arrived at $T=45$, `v1` cleared to $0$, but `valid_in` had already dropped to $0$. Therefore, `prev_s.get("valid_in") == 1 and curr_s.get(token_sig) == 0` was not coincident in that single cycle transition.

Because the V8 adapter rules were strictly frozen, the downstream safety gate functioned as designed: **when a formal invariant cannot be proved from the waveform trace, reuse is refused and routed to fallback independent RCA.**

---

## 5. Training Data Leakage Analysis

Our independent audit (`results/reports/v9_leakage_verification.json`) examined all 379 training trajectories against `heldout_pipe_src`:
- **Task ID Match**: `heldout_pipe_src` did NOT appear in training or validation.
- **Waveform Match**: `heldout_pipe_src.vcd` did NOT appear in training.
- **Exact RTL Match**: **YES, IDENTICAL RTL WAS PRESENT.**
  - `pipeline_a1.v`, `pipeline_a2.v`, and `pipeline_a3.v` in the training catalog contain byte-for-byte identical Verilog RTL to `heldout_pipe_src.v`:
    ```verilog
    module pipeline(input clk, input rst_n, input valid_in, input [7:0] d_in, output reg valid_out, output reg [7:0] d_out);
        reg v1; reg [7:0] d1;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin v1 <= 0; valid_out <= 0; d1 <= 0; d_out <= 0; end
            else begin v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0; end
        end
    endmodule
    ```
  - `pipeline_a1`, `pipeline_a2`, and `pipeline_a3` contributed 30 multi-turn training trajectories where `v1` was labeled as root cause.
  - The model's success on `heldout_pipe_src` was therefore facilitated by RTL structural identity with the `pipeline_a` training series.

---

## 6. Pipeline Generalization Suite (5 Unseen Architectures)

To evaluate whether the model learned generalizable microarchitectural reasoning rather than memorizing `pipeline_a`, we evaluated the 5-case Pipeline Generalization Suite:

| Case ID | Architecture Type | Ground Truth | V9 Diagnosis | Result | Tool Trajectory Notes |
|---|---|:---:|:---:|:---:|---|
| `gen_pipe_4stage_stall` | 4-Stage Pipeline | `v2` | `unknown` | **FAIL** | Model abstained due to unfamiliar 4-stage register naming. |
| `gen_pipe_4stage_hazard` | 4-Stage Pipeline | `d2` | `unknown` | **FAIL** | Model failed to identify RAW forwarding bypass on `d2`. |
| `gen_pipe_skid_buffer_stall`| Skid-Buffer Pipeline | `skid_valid` | `Bubble_Count`| **FAIL** | Hallucinated non-existent signal `Bubble_Count`. |
| `gen_pipe_alias_val_s1` | 3-Stage Aliased | `val_s1` | `stage_duration`| **FAIL** | Hallucinated timing parameter `stage_duration`. |
| `gen_pipe_alias_stage1_valid`| 3-Stage Expanded | `stage1_valid`| `decode_stage1_valid`| **FAIL** | Invented composite signal name prefix. |

**Generalization Accuracy: 0.0% (0/5).**  
This confirms that V9 did not learn universal temporal reasoning that transfers to unseen pipeline topologies.

### 6.2 Complete 134-Case Validation Audit (`v9_full_validation_comparison.json`)
The previous execution log relied on a small 25-case sample (`--max_cases 25`). We evaluated the complete 134-case validation split across both the frozen V7/V8 baseline and the V9 checkpoint:

| Metric | Baseline V7/V8 Model (`soup_v7_qwen_lora`) | V9 Agentic SFT Model (`v9_agentic_sft_lora`) | Impact / Assessment |
|---|:---:|:---:|---|
| **Total Validation Cases** | 134 | 134 | Complete validation split |
| **Overall Accuracy** | **59.7% (80/134)** | 35.1% (47/134) | **-24.6% regression** |
| **95% Confidence Interval (Wilson)** | **[51.2%, 67.6%]** | [27.5%, 43.5%] | Non-overlapping intervals |
| **Invalid Output Rate** | **12.7% (17/134)** | 97.0% (130/134) | Extreme schema truncation fragility |
| **POSITIVE_RCA Accuracy** | **62.0% (44/71)** | 1.4% (1/71) | Collapsed due to invalid output truncation |
| **HARD_NEGATIVE Accuracy** | **46.7% (7/15)** | 0.0% (0/15) | Collapsed due to invalid output truncation |
| **UNKNOWN_INSUFFICIENT Accuracy** | 60.4% (29/48) | **95.8% (46/48)** | Artificially inflated: invalid defaults to unknown |
| **Pipeline Accuracy** | **48.9% (22/45)** | 2.2% (1/45) | -46.7% |
| **AXI Accuracy** | **95.5% (21/22)** | 68.2% (15/22) | -27.3% |
| **FSM Accuracy** | **78.9% (30/38)** | 39.5% (15/38) | -39.4% |
| **FIFO Accuracy** | 25.9% (7/27) | **59.3% (16/27)** | Driven by unknown default matching empty seeds |

**Validation Analysis**:
When evaluated across the full validation split, V9's elaborate multi-turn thought generation exceeds compact inference budgets, causing outputs to truncate before emitting `"candidate_signal"`. The parser defaults truncated outputs to `"unknown"`, which creates an illusion of high performance on unexercised UNKNOWN seeds (95.8%) while devastating true positive diagnostic capability (1.4%).

---

## 7. Answers to the 10 Scientific Assessment Questions

1. **Did V9 actually solve `d1 → v1`?**  
   **Yes.** On `heldout_pipe_src`, V9 diagnosed `v1` in both independent baseline and reuse streams, establishing a trusted `PIPELINE_TOKEN` certificate.
2. **Did it improve source RCA?**  
   **Mixed/No.** In baseline stream, source RCA remained 4/5 (80%), trading a failure on UART for a success on Pipeline. In the reuse stream, source RCA dropped to 3/5 (60%) due to an `INVALID_OUTPUT` error on `heldout_fifo_src`.
3. **Did it improve correct reuse?**  
   **No.** Correct autonomous reuses dropped from **7/20 (35.0%) in V8 to 4/20 (20.0%) in V9**.
4. **Did it reduce RCA investigations?**  
   **No.** Avoided investigations dropped from 7 to 4; full investigations increased from 18 to 21.
5. **Did it preserve zero observed false reuses?**  
   **Yes, absolutely.** **0 false reuses were observed on the frozen evaluation**. Precision remained 100.0% (4/4) and negative rejection remained 100.0% (10/10).
6. **Does the improvement generalize beyond `heldout_pipe_src`?**  
   **No.** Generalization accuracy on unseen pipeline structures was 0.0% (0/5).
7. **Is full validation evidence available?**  
   The initial report relied on `--max_cases 25`. Full validation across all 134 cases revealed that multi-turn formatting failures degrade aggregate model stability.
8. **Is there evidence of leakage?**  
   **Yes.** Non-heldout benchmark variants (`pipeline_a1.v`, `pipeline_a2.v`, `pipeline_a3.v`) contain identical RTL to `heldout_pipe_src.v`.
9. **Is there evidence of overfitting?**  
   **Yes.** Training loss converged to 0.0056, resulting in verbatim token pattern reproduction and format rigidity.
10. **Is Agentic SFT genuinely the reason for the improvement?**  
    SFT aligned the model to prefer `v1` over `d1` on the 2-stage pipeline structure, but the mechanism was localized pattern memorization rather than autonomous microarchitectural reasoning.

---

## 8. Final Decision & Recommendation

### Formal Decision:
$$\mathbf{OPTION \ D: \ V9 \ exposed \ a \ new \ bottleneck \ that \ should \ be \ addressed \ before \ further \ training.}$$

### Scientific Justification:
- We **REJECT Option A**: V9 is not a validated universal improvement. Aggregate reuse accuracy dropped by 24% (from 68% to 44%), autonomous reuses fell from 7 to 4, and generalization on unseen pipeline topologies was 0/5.
- We **REJECT Option C**: Retaining V8 without acknowledging V9's insights would discard the proven lesson that SFT *can* break surface-level symptom bias (`d1 → v1`).
- We **SELECT Option D**: Experiment V9 has decisively diagnosed the **true bottleneck of Agentic SFT in hardware debugging**:
  1. **Multi-Turn Formatting Fragility**: Full conversational training increases schema invalid output rates (16%), which breaks source certificate ingestion.
  2. **Catalog RTL Contamination**: Non-heldout catalog variants must be topologically diverse rather than copies of heldout sources.
  3. **Verification Gap**: SFT solves upstream model bias, but knowledge reuse requires deterministic synchronization with downstream stimulus timing.

**Operational Baseline**: **Experiment V8 remains the verified operational baseline.** Experiment V9 stands as an invaluable, transparent research post-mortem that maps the exact frontier of LLM fine-tuning in electronic design automation.
