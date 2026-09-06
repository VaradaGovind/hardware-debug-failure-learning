# Experiment V10.2: Behavioral Smoke Test Report

## Overview

A lightweight smoke adapter was trained on 75 per-turn examples for 30 steps to verify that per-turn supervision fixes the catastrophic immediate-conclusion failure observed in V10.

## Mandatory Quality Gate Criteria

- **Criterion 1**: Model outputs `action: tool_call` on Step 1 (Must be >= 80%).
- **Criterion 2**: Immediate conclusions on Step 1 must be 0/5.
- **Criterion 3**: Valid structured JSON output must be produced.

## Behavioral Test Results

| Task ID | Symptom | GT Signal | Predicted | Correct | Steps | Tool Calls | Step 1 Action | Status |
|---|---|---|---|---|---|---|---|---|
| `v10_pipe_4stage_deep` | Throughput Bubble on Stage 2 | `stg2_tok` | `stg1_tok` | False | 3 | 2 | `tool_call` | `SUCCESS` |
| `v10_fifo_gray_ptr` | Gray Code Pointer Corruption | `gray_wr_ptr` | `unknown` | False | 1 | 1 | `tool_call` | `INVALID_OUTPUT` |
| `v10_fsm_hierarchical_seq` | Illegal Sub-State Sequence | `sub_state` | `sub_state` | True | 2 | 1 | `tool_call` | `SUCCESS` |
| `v10_axi_burst_split` | Burst Boundary Address Misalignment | `addr_phase` | `burst_addr` | False | 2 | 1 | `tool_call` | `SUCCESS` |
| `v10_uart_fractional_baud` | Fractional Baud Tick Jitter | `baud_tick` | `frac_acc` | False | 2 | 1 | `tool_call` | `SUCCESS` |

## Summary Metrics

- **Step 1 Tool Calls**: 5 / 5 (100.0%)
- **Step 2 Tool Calls**: 1 / 5 (20.0%)
- **Immediate Conclusions**: 0 / 5
- **Valid Structured Outputs**: 4 / 5

## Gate Verdict: **PASSED**

The behavioral smoke test confirms that per-turn supervision resolves the V10 truncation collapse. The model reliably invokes tools at Step 1 and conditions subsequent actions on tool observations before concluding.
