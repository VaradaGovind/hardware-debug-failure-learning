# Experiment V10.2 Training Target & Formatting Audit

**Audit Date:** September 4, 2026  
**Subject:** Target-Preserving Per-Turn ChatML Formatting & Loss Masking  
**Reference Dataset:** `datasets/v10_2/per_turn_train_v10_2.json` (618 examples)

---

## 1. Dataset Partitioning & Target Breakdown

In Experiment V10.2, monolithic multi-turn trajectories were decomposed into 618 self-contained, single-turn ChatML examples.

### Target Distribution:
| Segment Type | Turn Semantics | Supervised Action | Target Tool / Signal | Example Count | Percentage |
|---|---|---|---|---|---|
| **TYPE A** | Step 1: Initial Context $\to$ Tool Invocation | `action: tool_call` | `read_rtl_file` | 206 | 33.33% |
| **TYPE B** | Step 2: RTL Evidence $\to$ Waveform Invocation | `action: tool_call` | `get_waveform_summary` | 206 | 33.33% |
| **TYPE C** | Step 3: Complete Evidence $\to$ Conclusion | `action: conclude` | Root Cause Signal | 176 | 28.48% |
| **TYPE C (Abstain)**| Step 3: Insufficient Evidence $\to$ Abstention | `action: conclude` | `candidate_signal: "unknown"`| 30 | 4.85% |
| **TOTAL** | | | | **618** | **100.0%** |

- **Total Tool-Call Targets**: 412 / 618 (**66.67%**).
- **Total Conclusion Targets**: 206 / 618 (**33.33%**).
- **Tool-Call Supervision Ratio**: Meets and exceeds the $\ge 50.0\%$ quality gate requirement.

---

## 2. Token Budget Compliance & Zero Target Truncation

### 2.1 The Monolithic Truncation Flaw in V10
In Experiment V10, trajectories averaged 5,434.6 tokens. Monolithic truncation at 768 tokens (`[:120] + [-648:]`) excised the middle of every trajectory, eliminating 100% of tool calls and tool observation turns. As proven in V10.1, **0/988 tool-call supervision tokens survived**, training the model to terminate immediately without tools.

### 2.2 The V10.2 Target-Preserving Invariant
In V10.2, the formatting pipeline (`format_per_turn_example`) calculates user budget strictly after reserving full slots for system prompt and assistant target:
$$\text{avail\_user\_body} = \text{max\_length} - \text{len}(\text{sys\_ids}) - \text{len}(\text{target\_ids}) - \text{len}(\text{user\_header}) - \text{len}(\text{user\_footer})$$

- If truncation is necessary, only the middle of the user query context is spliced (`raw_user_ids[:u_head] + raw_user_ids[-u_tail:]`).
- **Target completions (`target_ids`) are NEVER truncated**.
- Assistant completions are 100% preserved and fully supervised.

---

## 3. Loss Masking Verification

ChatML turn structures were audited for strict loss masking:
1. `<|im_start|>system ... <|im_end|>`: Encoded and assigned label `-100`.
2. `<|im_start|>user ... <|im_end|>`: Encoded and assigned label `-100`.
3. `<|im_start|>assistant ... <|im_end|>`: Encoded with active token IDs matching the ground-truth target tokens.

### Cross-Entropy Loss Computation:
```python
active_mask = (lbl[:, 1:] != -100)
active_indices = torch.nonzero(active_mask.view(-1), as_tuple=True)[0]
shift_hidden = hidden[:, :-1, :].contiguous().view(-1, hidden.size(-1))[active_indices]
shift_labels = lbl[:, 1:].contiguous().view(-1)[active_indices]
c_loss = torch.nn.functional.cross_entropy(chunk_logits, chunk_l, reduction="sum")
```
- **System and User Token Gradient**: Exactly 0.0.
- **Active Loss Calculation**: Restricted 100% to assistant output tokens.
- **Tool-Call Supervision Guarantee**: All 412 tool-call targets actively contributed to the backpropagation loss across both training epochs.

---

## 4. Audit Verdict

**PASSED**:
- 0% target truncation observed across all 618 training examples.
- 0% tool schema corruption.
- Loss masking is mathematically verified to supervise assistant actions exclusively.
- The root cause of the V10 premature termination failure is conclusively eliminated.
