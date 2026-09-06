# V10.1 Manual Case Studies: Side-by-Side Trajectory Forensics

This document presents side-by-side behavioral case studies comparing the **Frozen V8 Baseline**, **V10 Model A (Generic SFT)**, and **V10 Model B (Topology-Generalized SFT)** on identical prompts, tool environments, and decoding settings.

Data source: `results/reports/v10_1_behavioral_comparison.json`.

---

## Case Study 1: V8 Success / Model A & B Failure — `heldout_pipe_src` (Pipeline Stall Bubble)

- **Target Architecture**: `heldout_pipe_src` (Frozen 25-Case Benchmark Source)
- **Failure Symptom**: Data lost on downstream stage during backpressure stall
- **Candidate Signals**: `clk`, `rst_n`, `in_val`, `in_dat`, `v1`, `d1`, `v2`, `d2`, `out_val`, `out_dat`
- **Ground Truth Root Cause**: `v1` (Stage 1 Valid Token)

### Trajectory Comparison:

| Model | Step 1 Action | Tool Called / Args | Step 2 Action | Final Prediction | Correct? | Behavioral Failure Mechanism |
|---|---|---|---|---|---|---|
| **V8** | `conclude` | None | None (Terminated) | `v1` | **YES** | V8 correctly diagnosed `v1` based on its V7/V8 single-turn representation. |
| **Model A** | `conclude` | None | None (Terminated) | `clk` | **NO** | Prematurely concluded at Step 1 without inspecting RTL or waveforms; hallucinated clock as root cause. |
| **Model B** | `conclude` | None | None (Terminated) | `unknown` | **NO** | Prematurely concluded at Step 1; defaulted to `unknown` due to negative-rejection bias. |

**Forensic Insight**: Neither Model A nor Model B attempted to call `read_rtl_file` or `get_waveform_summary`. Both models terminated immediately on Step 1 because 100% of `tool_call` tokens had been truncated from their training data.

---

## Case Study 2: V8 Success / Model A & B Failure — `heldout_fifo_src` (FIFO Simultaneous RW)

- **Target Architecture**: `heldout_fifo_src` (Frozen 25-Case Benchmark Source)
- **Failure Symptom**: Counter underflow/overflow assertion failure on simultaneous read/write
- **Candidate Signals**: `clk`, `rst_n`, `write_en`, `read_en`, `count`, `write_ptr`, `read_ptr`
- **Ground Truth Root Cause**: `count` (Internal Occupancy Counter)

### Trajectory Comparison:

| Model | Step 1 Action | Tool Called / Args | Step 2 Action | Final Prediction | Correct? | Behavioral Failure Mechanism |
|---|---|---|---|---|---|---|
| **V8** | `tool_call` | `read_rtl_file({"task_id": "heldout_fifo_src"})` | `conclude` (`count`) | `count` | **YES** | V8 investigated the RTL, observed the simultaneous R/W counter update condition, and correctly concluded `count`. |
| **Model A** | `conclude` | None | None (Terminated) | `write_enable` | **NO** | Premature Step 1 termination; hallucinated undeclared port `write_enable` (signal in RTL is `write_en`). |
| **Model B** | `conclude` | None | None (Terminated) | `unknown` | **NO** | Premature Step 1 termination; defaulted to `unknown`. |

**Forensic Insight**: V8 executed a legitimate multi-step investigation (calling `read_rtl_file`, processing the response, and outputting the correct signal). Model A and Model B completely failed to invoke tools and guessed blindly or abstained.

---

## Case Study 3: V8 Success / Model A & B Failure — `heldout_axi_src` (AXI Handshake Hold)

- **Target Architecture**: `heldout_axi_src` (Frozen 25-Case Benchmark Source)
- **Failure Symptom**: Handshake stability violation (valid dropped before ready)
- **Candidate Signals**: `aclk`, `aresetn`, `wvalid`, `wready`, `wdata`, `bvalid`, `bready`
- **Ground Truth Root Cause**: `wvalid`

### Trajectory Comparison:

| Model | Step 1 Action | Tool Called / Args | Step 2 Action | Final Prediction | Correct? | Behavioral Failure Mechanism |
|---|---|---|---|---|---|---|
| **V8** | `tool_call` | `read_rtl_file({"task_id": "heldout_axi_src"})` | `conclude` (`wvalid`) | `wvalid` | **YES** | Multi-step investigation; identified `wvalid` hold violation. |
| **Model A** | `conclude` | None | None (Terminated) | `held_out` | **NO** | Hallucinated non-existent signal `held_out` extracted from the task ID name string. |
| **Model B** | `conclude` | None | None (Terminated) | `unknown` | **NO** | Premature Step 1 termination; defaulted to `unknown`. |

**Forensic Insight**: Model A extracted lexical tokens from the task ID (`heldout` $\rightarrow$ `held_out`) because it was deprived of the RTL declarations during truncated training.

---

## Case Study 4: Disjoint Validation Architecture — `v10_val_pipe_3stage_split`

- **Target Architecture**: `v10_val_pipe_3stage_split` (Held-Out Disjoint Pipeline)
- **Failure Symptom**: Stage token dropped during backpressure stall
- **Candidate Signals**: `clk`, `rst_n`, `p_in_val`, `p_in_dat`, `p1_val`, `p1_dat`, `p2_val`, `p2_dat`, `p_out_val`
- **Ground Truth Root Cause**: `p1_val`

### Trajectory Comparison:

| Model | Step 1 Action | Tool Called / Args | Step 2 Action | Final Prediction | Correct? | Behavioral Failure Mechanism |
|---|---|---|---|---|---|---|
| **V8** | `conclude` | None | None (Terminated) | `p1_val` | **YES** | Recognized naming pattern `p1_val` as Stage 1 valid token and correctly diagnosed. |
| **Model A** | `conclude` | None | None (Terminated) | `clk` | **NO** | Defaulted to passive clock input `clk` without tool query. |
| **Model B** | `conclude` | None | None (Terminated) | `p2_val` | **NO** | Defaulted to downstream Stage 2 distractor `p2_val`. |

**Forensic Insight**: Neither Model A nor Model B queried waveforms to establish the earliest causal cycle ($T=35$).

---

## Case Study 5: Paired Hard Negative — `v10_pipe_3stage_hazard`

- **Target Architecture**: `v10_pipe_3stage_hazard` (RAW Hazard Forwarding Defect)
- **Failure Symptom**: RAW hazard operand corruption vs control token bubble
- **Candidate Signals**: `clk`, `rst_n`, `in_valid`, `in_payload`, `stage1_vld`, `stage2_vld`, `fwd_data`, `op_reg`, `out_valid`, `out_payload`
- **Ground Truth Root Cause**: `fwd_data` (Data Register Hazard, NOT control token drop)
- **Competing Distractor**: `stage1_vld`

### Trajectory Comparison:

| Model | Step 1 Action | Tool Called / Args | Step 2 Action | Final Prediction | Correct? | Behavioral Failure Mechanism |
|---|---|---|---|---|---|---|
| **V8** | `tool_call` | `read_rtl_file(...)` | `conclude` (`fwd_data`) | `fwd_data` | **YES** | Read RTL, checked hazard logic, correctly identified data forwarding path. |
| **Model A** | `conclude` | None | None (Terminated) | `fwd_data` | **YES** | Memorized in-distribution training label string `fwd_data`. |
| **Model B** | `conclude` | None | None (Terminated) | `op_reg` | **NO** | Picked competing operand register `op_reg` without tool verification. |

**Forensic Insight**: Model A got this right solely because `v10_pipe_3stage_hazard` was part of its training set and `fwd_data` was the surviving suffix. Model B was confused by the competing `op_reg` hard-negative pairs.

---

## Case Study 6: Authentic UNKNOWN Case — `v10_val_fifo_ring_buf` (Truncated Trace)

- **Target Architecture**: `v10_val_fifo_ring_buf` (Truncated Simulation Abort)
- **Failure Symptom**: Simulation trace terminated before initiating transaction
- **Candidate Signals**: `clk`, `rst_n`, `push_cmd`, `pop_cmd`, `data_in`, `head_idx`, `tail_idx`, `items_avail`
- **Ground Truth Root Cause**: `unknown` (Insufficient Evidence)

### Trajectory Comparison:

| Model | Step 1 Action | Tool Called / Args | Step 2 Action | Final Prediction | Correct? | Behavioral Failure Mechanism |
|---|---|---|---|---|---|---|
| **V8** | `tool_call` | `get_waveform_summary(...)` | `conclude` (`items_avail`) | `items_avail` | **NO** | V8 lacks explicit UNKNOWN training; hallucinated `items_avail` rather than abstaining. |
| **Model A** | `conclude` | None | None (Terminated) | `data_out` | **NO** | Hallucinated output port `data_out` without checking waveform. |
| **Model B** | `conclude` | None | None (Terminated) | `unknown` | **YES** | Correctly output `unknown` (driven by its heavy UNKNOWN/negative bias). |

**Forensic Insight**: Model B succeeded here ONLY because of its strong bias toward predicting `unknown`. When evaluated on positive cases, this same bias caused catastrophic failure (predicting `unknown` on 75%+ of valid cases).

---

## Summary of Trajectory Behavioral Patterns

| Behavioral Characteristic | Frozen V8 Baseline | V10 Model A (Generic) | V10 Model B (Topological) |
|---|---|---|---|
| **Invoked Tools at Step 1** | **15 / 20 (75.0%)** | **0 / 20 (0.0%)** | **0 / 20 (0.0%)** |
| **Terminated Immediately at Step 1** | 5 / 20 (25.0%) | **20 / 20 (100.0%)** | **20 / 20 (100.0%)** |
| **Average Steps Taken** | **2.05 steps** | **1.00 steps** | **1.00 steps** |
| **Undeclared Signal Hallucinations** | 3 / 20 (15.0%) | 7 / 20 (35.0%) | 3 / 20 (15.0%) |
| **Unjustified `unknown` Abstentions** | 0 / 20 (0.0%) | 4 / 20 (20.0%) | **11 / 20 (55.0%)** |

**Conclusion**: Models A and B did NOT fail at complex temporal reasoning or candidate discrimination. They failed at **Step 1 Tool Selection**, terminating immediately in 100% of cases because the context truncation bug deleted all `tool_call` tokens during fine-tuning.
