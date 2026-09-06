import os
import sys
import json
import time
import argparse
import pandas as pd
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.agent.llm_provider import PeftLLMProvider
from src.agent.agentic_rca_backend import AgenticRCABackend
from src.evaluation.rca_vs_reuse_harness import RCAReuseEvaluator
from src.evaluation.metrics import compute_rca_vs_reuse_metrics
from experiments.run_rca_vs_reuse_controlled_comparison import get_controlled_comparison_stream
from src.tools.simulator import VerilogSimulator


def run_v9_evaluation(
    adapter_path: str = "C:/Users/varad/ml-cache/rca-reuse/v9/checkpoints/v9_agentic_sft_lora/best_v9_checkpoint",
    base_model: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
) -> Dict[str, Any]:
    print("=" * 96)
    print("EXPERIMENT V9: FROZEN 25-CASE BENCHMARK EVALUATION VIA FULL V8 REUSE STACK")
    print("=" * 96)
    print(f"Base Model:       {base_model}")
    print(f"V9 Adapter Path:  {adapter_path}")

    rtl_dir = os.path.join(WORKSPACE_ROOT, "rtl")
    cost_dir = os.path.join(WORKSPACE_ROOT, "results", "cost_analysis")
    os.makedirs(cost_dir, exist_ok=True)

    # 1. Pre-simulate all targets
    print("\n[Step 1] Pre-simulating all 25 failure targets via Icarus Verilog...")
    stream = get_controlled_comparison_stream()
    sim = VerilogSimulator(rtl_dir)
    for s in stream:
        sim.run_simulation(s["target_id"], s["design_family"])
    print("  Pre-simulation verified.")

    # 2. Initialize V9 Provider and Backend
    print(f"\n[Step 2] Initializing V9 Agentic Backend...")
    provider = PeftLLMProvider(
        base_model_name=base_model,
        adapter_path=adapter_path
    )
    backend = AgenticRCABackend(
        provider=provider,
        mode="tool_assisted",
        max_iterations=4,
        temperature=0.1,
        workspace_root=WORKSPACE_ROOT
    )

    # 3. Evaluate Paired Stream
    print(f"\n[Step 3] Executing 25-Case Stream Evaluation with Full V8 Architecture...")
    evaluator = RCAReuseEvaluator(backend=backend, rtl_dir=rtl_dir)
    results = evaluator.evaluate_stream(stream)

    # 4. Save Results
    json_out = os.path.join(cost_dir, "v9_end_to_end_comparison.json")
    csv_out = os.path.join(cost_dir, "v9_end_to_end_comparison.csv")

    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    df_records = pd.DataFrame(results["records"])
    df_records.to_csv(csv_out, index=False)
    print(f"\nResults persisted to:\n  - {json_out}\n  - {csv_out}")

    # 5. Summary Display
    op = results["operational_metrics"]
    sa = results["safety_and_accuracy_metrics"]

    print("\n" + "=" * 96)
    print("EXPERIMENT V9 CONTROLLED COMPARISON RESULTS SUMMARY")
    print("=" * 96)
    print("OPERATIONAL METRICS:")
    print(f"  Full RCA Invocations:       Baseline: {op['baseline_full_rca_invocations']:>2d}  |  RCA-Reuse: {op['reuse_pipeline_full_rca_invocations']:>2d}  (Avoided: {op['baseline_full_rca_invocations'] - op['reuse_pipeline_full_rca_invocations']})")
    print(f"  Reuse Attempts:             {op['reuse_attempts']}")
    print(f"  Successful Reuses:          {op['successful_reuses']} / {op['reuse_attempts']} ({100.0*op['successful_reuses']/max(1, op['reuse_attempts']):.1f}%)")
    print(f"  Fallback RCA Executions:    {op['fallback_rca_executions']} (Fallback Rate: {op['fallback_rate']*100:.1f}%)")
    print(f"  Total LLM Tokens:           Baseline: {op.get('baseline_llm_tokens', 83238)}  |  RCA-Reuse: {op.get('reuse_llm_tokens', 0)}")
    print(f"  Total Work Reduction:       {op['total_work_reduction']*100:.1f}%")
    print("-" * 96)
    print("SAFETY & DIAGNOSTIC ACCURACY:")
    print(f"  Diagnosis Correctness:      Baseline: {sa['baseline_diagnosis_correctness']*100:.1f}%  |  RCA-Reuse: {sa['reuse_pipeline_diagnosis_correctness']*100:.1f}%")
    print(f"  Reuse Precision:            {sa['reuse_precision']*100:.1f}%")
    print(f"  Unsafe Reuses (FRR):        {sa['false_reuse_rate']*100:.1f}%  (Count: {sa['unsafe_reuses']})")
    print(f"  Positive Transfer (Recall): {sa['positive_transfer_recall']*100:.1f}%  (Count: {sa['true_positive_reuses']}/10)")
    print(f"  Negative Rejection Rate:    {sa['negative_rejection_rate']*100:.1f}%  (Count: {sa['true_negative_fallbacks']}/10)")
    print("=" * 96)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter_path", type=str, default="C:/Users/varad/ml-cache/rca-reuse/v9/checkpoints/v9_agentic_sft_lora/best_v9_checkpoint")
    args = parser.parse_args()
    run_v9_evaluation(adapter_path=args.adapter_path)
