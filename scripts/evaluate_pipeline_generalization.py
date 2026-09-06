import os
import sys
import json
import argparse
from typing import Dict, Any, List

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.agent.llm_provider import PeftLLMProvider, LLMProvider
from src.agent.agentic_rca_backend import AgenticRCABackend


def evaluate_pipeline_generalization(
    provider: LLMProvider,
    suite_path: str = "C:/Users/varad/ml-cache/rca-reuse/v9/datasets/pipeline_generalization_suite.json"
) -> Dict[str, Any]:
    if not os.path.exists(suite_path):
        suite_path = os.path.join(WORKSPACE_ROOT, "datasets", "v9", "pipeline_generalization_suite.json")

    with open(suite_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print("=" * 96)
    print(f"EVALUATING PIPELINE GENERALIZATION SUITE ({len(cases)} UNSEEN ARCHITECTURES)")
    print("=" * 96)

    backend = AgenticRCABackend(
        provider=provider,
        mode="tool_assisted",
        max_iterations=4,
        temperature=0.1,
        workspace_root=WORKSPACE_ROOT
    )

    correct_count = 0
    records = []

    for idx, case in enumerate(cases):
        task_id = case["task_id"]
        arch = case["architecture"]
        gt = case["ground_truth_signal"]
        dist = case["symptom_distractor"]
        cands = case["candidate_signals"]

        meta = {
            "symptom": case["symptom"],
            "design_family": "pipeline",
            "ground_truth_signals": [gt],
            "candidate_signals": cands,
            "target_signals": cands
        }

        diag = backend.diagnose_failure(task_id, "pipeline", meta)
        pred = diag.root_cause_signal
        is_corr = (pred.lower() == gt.lower())

        if is_corr:
            correct_count += 1

        records.append({
            "task_id": task_id,
            "architecture": arch,
            "ground_truth": gt,
            "distractor": dist,
            "prediction": pred,
            "correct": is_corr,
            "steps": diag.steps_taken,
            "latency_ms": diag.wall_clock_ms
        })

        print(f"  [{idx+1}/{len(cases)}] {task_id:<28} | Arch: {arch:<24} | GT: {gt:<12} | Pred: {pred:<12} | {'PASS' if is_corr else 'FAIL'}")

    acc_pct = (correct_count / len(cases)) * 100.0
    print("-" * 96)
    print(f"Pipeline Generalization Accuracy: {acc_pct:.1f}% ({correct_count}/{len(cases)})")
    print("=" * 96)

    return {
        "accuracy_pct": acc_pct,
        "correct_count": correct_count,
        "total_cases": len(cases),
        "records": records
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter_path", type=str, default="C:/Users/varad/ml-cache/rca-reuse/v9/checkpoints/v9_agentic_sft_lora/best_v9_checkpoint")
    args = parser.parse_args()

    provider = PeftLLMProvider(
        base_model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        adapter_path=args.adapter_path
    )
    evaluate_pipeline_generalization(provider)
