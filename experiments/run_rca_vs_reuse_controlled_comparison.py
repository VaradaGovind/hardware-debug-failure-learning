import os
import sys
import json
import time
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.simulator import VerilogSimulator
from src.evaluation.rca_vs_reuse_harness import (
    DeterministicProxyRCABackend,
    RCAReuseEvaluator
)


def get_controlled_comparison_stream() -> list:
    """
    Defines a rigorous 25-case paired arrival stream across 5 hardware families:
    For each family:
      - 1 Source Manifestation (establishes initial RCA and certificate)
      - 2 Positive Targets (variable latency / stall variations of same bug)
      - 1 Adversarial Negative Target (same symptom, different underlying bug)
      - 1 Incomplete Trace Target (truncated waveform, insufficient evidence)
    """
    stream = [
        # 1. FIFO Family Stream
        {
            "target_id": "heldout_fifo_src",
            "design_family": "fifo",
            "defect_mechanism": "FIFO_SIMULTANEOUS_RW",
            "is_source": True,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["count"],
            "symptom": "Data Mismatch",
            "target_signals": ["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"]
        },
        {
            "target_id": "fifo_vl_a1",
            "design_family": "fifo",
            "defect_mechanism": "FIFO_SIMULTANEOUS_RW",
            "is_source": False,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["count"],
            "symptom": "Data Mismatch",
            "target_signals": ["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"]
        },
        {
            "target_id": "fifo_vl_b1",
            "design_family": "fifo",
            "defect_mechanism": "FIFO_SIMULTANEOUS_RW",
            "is_source": False,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["count"],
            "symptom": "Data Mismatch",
            "target_signals": ["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"]
        },
        {
            "target_id": "fifo_vl_f1",
            "design_family": "fifo",
            "defect_mechanism": "FIFO_PTR_OVERFLOW",
            "is_source": False,
            "ground_truth_match": "MISMATCH",
            "ground_truth_signals": ["write_ptr"],
            "symptom": "Data Mismatch",
            "target_signals": ["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"]
        },
        {
            "target_id": "fifo_vl_i2",
            "design_family": "fifo",
            "defect_mechanism": "FIFO_SIMULTANEOUS_RW",
            "is_source": False,
            "ground_truth_match": "MISMATCH",  # Incomplete evidence must not be reused
            "ground_truth_signals": ["count"],
            "symptom": "Data Mismatch",
            "target_signals": ["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"]
        },

        # 2. AXI Family Stream
        {
            "target_id": "heldout_axi_src",
            "design_family": "axi",
            "defect_mechanism": "AXI_HANDSHAKE_HOLD",
            "is_source": True,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["valid_out"],
            "symptom": "Timeout",
            "target_signals": ["valid_in", "ready_in", "valid_out", "ready_out"]
        },
        {
            "target_id": "axi_vl_a1",
            "design_family": "axi",
            "defect_mechanism": "AXI_HANDSHAKE_HOLD",
            "is_source": False,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["valid_out"],
            "symptom": "Timeout",
            "target_signals": ["valid_in", "ready_in", "valid_out", "ready_out"]
        },
        {
            "target_id": "axi_vl_b1",
            "design_family": "axi",
            "defect_mechanism": "AXI_HANDSHAKE_HOLD",
            "is_source": False,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["valid_out"],
            "symptom": "Timeout",
            "target_signals": ["valid_in", "ready_in", "valid_out", "ready_out"]
        },
        {
            "target_id": "axi_vl_f1",
            "design_family": "axi",
            "defect_mechanism": "AXI_EARLY_READY",
            "is_source": False,
            "ground_truth_match": "MISMATCH",
            "ground_truth_signals": ["ready_out"],
            "symptom": "Timeout",
            "target_signals": ["valid_in", "ready_in", "valid_out", "ready_out"]
        },
        {
            "target_id": "axi_vl_i2",
            "design_family": "axi",
            "defect_mechanism": "AXI_HANDSHAKE_HOLD",
            "is_source": False,
            "ground_truth_match": "MISMATCH",
            "ground_truth_signals": ["valid_out"],
            "symptom": "Timeout",
            "target_signals": ["valid_in", "ready_in", "valid_out", "ready_out"]
        },

        # 3. FSM Family Stream
        {
            "target_id": "heldout_fsm_src",
            "design_family": "fsm",
            "defect_mechanism": "FSM_STUCK_STATE",
            "is_source": True,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["state"],
            "symptom": "Stuck State",
            "target_signals": ["state", "start", "done"]
        },
        {
            "target_id": "fsm_vl_a1",
            "design_family": "fsm",
            "defect_mechanism": "FSM_STUCK_STATE",
            "is_source": False,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["state"],
            "symptom": "Stuck State",
            "target_signals": ["state", "start", "done"]
        },
        {
            "target_id": "fsm_vl_b1",
            "design_family": "fsm",
            "defect_mechanism": "FSM_STUCK_STATE",
            "is_source": False,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["state"],
            "symptom": "Stuck State",
            "target_signals": ["state", "start", "done"]
        },
        {
            "target_id": "fsm_vl_f1",
            "design_family": "fsm",
            "defect_mechanism": "FSM_OUTPUT_TIMING",
            "is_source": False,
            "ground_truth_match": "MISMATCH",
            "ground_truth_signals": ["done"],
            "symptom": "Stuck State",
            "target_signals": ["state", "start", "done"]
        },
        {
            "target_id": "fsm_vl_i2",
            "design_family": "fsm",
            "defect_mechanism": "FSM_STUCK_STATE",
            "is_source": False,
            "ground_truth_match": "MISMATCH",
            "ground_truth_signals": ["state"],
            "symptom": "Stuck State",
            "target_signals": ["state", "start", "done"]
        },

        # 4. UART Family Stream
        {
            "target_id": "heldout_uart_src",
            "design_family": "uart",
            "defect_mechanism": "UART_BAUD_DIVIDER",
            "is_source": True,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["cnt"],
            "symptom": "Bad Output",
            "target_signals": ["cnt", "start", "tx"]
        },
        {
            "target_id": "uart_vl_a1",
            "design_family": "uart",
            "defect_mechanism": "UART_BAUD_DIVIDER",
            "is_source": False,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["cnt"],
            "symptom": "Bad Output",
            "target_signals": ["cnt", "start", "tx"]
        },
        {
            "target_id": "uart_vl_b1",
            "design_family": "uart",
            "defect_mechanism": "UART_BAUD_DIVIDER",
            "is_source": False,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["cnt"],
            "symptom": "Bad Output",
            "target_signals": ["cnt", "start", "tx"]
        },
        {
            "target_id": "uart_vl_f1",
            "design_family": "uart",
            "defect_mechanism": "UART_STOP_BIT_GEN",
            "is_source": False,
            "ground_truth_match": "MISMATCH",
            "ground_truth_signals": ["tx"],
            "symptom": "Bad Output",
            "target_signals": ["cnt", "start", "tx"]
        },
        {
            "target_id": "uart_vl_i2",
            "design_family": "uart",
            "defect_mechanism": "UART_BAUD_DIVIDER",
            "is_source": False,
            "ground_truth_match": "MISMATCH",
            "ground_truth_signals": ["cnt"],
            "symptom": "Bad Output",
            "target_signals": ["cnt", "start", "tx"]
        },

        # 5. PIPELINE Family Stream
        {
            "target_id": "heldout_pipe_src",
            "design_family": "pipeline",
            "defect_mechanism": "PIPE_STALL_BUBBLE",
            "is_source": True,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["v1"],
            "symptom": "Data Loss",
            "target_signals": ["valid_in", "d_in", "v1", "d1", "valid_out", "d_out"]
        },
        {
            "target_id": "pipeline_vl_a1",
            "design_family": "pipeline",
            "defect_mechanism": "PIPE_STALL_BUBBLE",
            "is_source": False,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["v1"],
            "symptom": "Data Loss",
            "target_signals": ["valid_in", "d_in", "v1", "d1", "valid_out", "d_out"]
        },
        {
            "target_id": "pipeline_vl_b1",
            "design_family": "pipeline",
            "defect_mechanism": "PIPE_STALL_BUBBLE",
            "is_source": False,
            "ground_truth_match": "MATCH",
            "ground_truth_signals": ["v1"],
            "symptom": "Data Loss",
            "target_signals": ["valid_in", "d_in", "v1", "d1", "valid_out", "d_out"]
        },
        {
            "target_id": "pipeline_vl_f1",
            "design_family": "pipeline",
            "defect_mechanism": "PIPE_FORWARD_HAZARD",
            "is_source": False,
            "ground_truth_match": "MISMATCH",
            "ground_truth_signals": ["d1"],
            "symptom": "Data Loss",
            "target_signals": ["valid_in", "d_in", "v1", "d1", "valid_out", "d_out"]
        },
        {
            "target_id": "pipeline_vl_i2",
            "design_family": "pipeline",
            "defect_mechanism": "PIPE_STALL_BUBBLE",
            "is_source": False,
            "ground_truth_match": "MISMATCH",
            "ground_truth_signals": ["v1"],
            "symptom": "Data Loss",
            "target_signals": ["valid_in", "d_in", "v1", "d1", "valid_out", "d_out"]
        }
    ]
    return stream


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rtl_dir = os.path.join(base_dir, "rtl")
    cost_dir = os.path.join(base_dir, "results", "cost_analysis")
    log_dir = os.path.join(cost_dir, "logs")
    os.makedirs(cost_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    print("=" * 88)
    print("CONTROLLED EXPERIMENTAL COMPARISON: INDEPENDENT FULL RCA vs. RCA-REUSE")
    print("=" * 88)

    # 1. Pre-simulate all targets to ensure valid VCDs
    print("\n[STEP 1] Pre-simulating RTL Targets via Icarus Verilog...")
    stream = get_controlled_comparison_stream()
    sim = VerilogSimulator(rtl_dir)
    for item in stream:
        t_id = item["target_id"]
        fam = item["design_family"]
        res = sim.run_simulation(t_id, fam)
        vcd_p = os.path.join(rtl_dir, f"{t_id}.vcd")
        if not os.path.exists(vcd_p):
            raise RuntimeError(f"Simulation failed to generate VCD for {t_id}")
    print(f"  Pre-simulation verified: {len(stream)}/{len(stream)} targets compiled and traced.")

    # 2. Instantiate Deterministic Proxy Backend and Evaluator
    print("\n[STEP 2] Initializing Deterministic Proxy RCA Backend & Evaluator...")
    backend = DeterministicProxyRCABackend(rtl_dir=rtl_dir, log_dir=log_dir, seed=42, budget=12)
    evaluator = RCAReuseEvaluator(backend=backend, rtl_dir=rtl_dir)

    # 3. Execute Paired Controlled Stream Evaluation
    print(f"\n[STEP 3] Executing Paired Evaluation on {len(stream)} Failure Manifestations...")
    results = evaluator.evaluate_stream(stream)

    # 4. Save Structured Machine-Readable Results
    json_out = os.path.join(cost_dir, "rca_vs_reuse_controlled_comparison.json")
    csv_out = os.path.join(cost_dir, "rca_vs_reuse_controlled_comparison.csv")
    
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    df_records = pd.DataFrame(results["records"])
    df_records.to_csv(csv_out, index=False)
    print(f"  Results written to:\n    {json_out}\n    {csv_out}")

    # 5. Display Summary Metrics Table
    op = results["operational_metrics"]
    sa = results["safety_and_accuracy_metrics"]
    meta = results["evaluation_metadata"]

    print("\n" + "=" * 88)
    print("CONTROLLED COMPARISON RESULTS SUMMARY")
    print("=" * 88)
    print(f"Evaluation Backend:                 {meta['backend_type']} (ModelB Causal Agent)")
    print(f"Token Accounting:                   {meta['llm_token_accounting']}")
    print(f"Total Failure Manifestations:       {meta['total_stream_length']} (5 Sources + 20 Targets)")
    print("-" * 88)
    print("OPERATIONAL METRICS COMPARISON:")
    print(f"  Full RCA Invocations:             Baseline: {op['baseline_full_rca_invocations']:>3}  |  RCA-Reuse: {op['reuse_pipeline_full_rca_invocations']:>3}  (Avoided: {op['baseline_full_rca_invocations'] - op['reuse_pipeline_full_rca_invocations']})")
    print(f"  Reuse Attempts:                   {op['reuse_attempts']:>3}")
    print(f"  Successful Reuses:                {op['successful_reuses']:>3} / {op['reuse_attempts']}")
    print(f"  Fallback RCA Executions:          {op['fallback_rca_executions']:>3}  (Fallback Rate: {op['fallback_rate']*100:.1f}%)")
    print(f"  Simulator Invocations:            Baseline: {op['baseline_simulator_invocations']:>3}  |  RCA-Reuse: {op['reuse_simulator_invocations']:>3}")
    print(f"  Waveform Queries / Extractions:   Baseline: {op['baseline_waveform_queries']:>3}  |  RCA-Reuse: {op['reuse_waveform_queries']:>3}")
    print(f"  Certificate Validation Ops:       {op['certificate_validation_operations']:>3}")
    print(f"  Total Tool Calls / Operations:    Baseline: {op['baseline_tool_calls']:>3}  |  RCA-Reuse: {op['reuse_total_tool_calls']:>3}")
    print(f"  Total Search Compression Ratio:   {op['search_compression_ratio']:.2f}x")
    print(f"  Total Work Reduction:             {op['total_work_reduction']*100:.1f}%")
    print(f"  Wall-Clock Time:                  Baseline: {op['baseline_wall_clock_ms']:.1f} ms  |  RCA-Reuse: {op['reuse_wall_clock_ms']:.1f} ms")
    print("-" * 88)
    print("SAFETY & DIAGNOSTIC ACCURACY:")
    print(f"  Diagnosis Correctness:            Baseline: {sa['baseline_diagnosis_correctness']*100:.1f}%  |  RCA-Reuse: {sa['reuse_pipeline_diagnosis_correctness']*100:.1f}%")
    print(f"  Reuse Precision:                  {sa['reuse_precision']*100:.1f}%")
    print(f"  Unsafe Reuse Rate (FRR):          {sa['false_reuse_rate']*100:.1f}%  (Count: {sa['unsafe_reuses']})")
    print(f"  Positive Transfer (Recall):       {sa['positive_transfer_recall']*100:.1f}%  (Count: {sa['true_positive_reuses']}/10)")
    print(f"  Negative Rejection Rate:          {sa['negative_rejection_rate']*100:.1f}%  (Count: {sa['true_negative_fallbacks']}/10)")
    print("=" * 88)


if __name__ == "__main__":
    main()
