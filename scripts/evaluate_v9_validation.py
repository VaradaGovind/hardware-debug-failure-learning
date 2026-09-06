import os
import sys
import json
import time
import argparse
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.agent.llm_provider import PeftLLMProvider, LLMProvider
from src.agent.agentic_rca_backend import AgenticRCABackend


def evaluate_v9_validation(
    provider: LLMProvider,
    val_file_path: str = "C:/Users/varad/ml-cache/rca-reuse/v9/datasets/agentic_val_v9.json",
    max_cases: int = -1
) -> Dict[str, Any]:
    """
    Evaluates an LLM checkpoint on the V9 Validation Dataset in tool-assisted agentic mode.
    Measures overall accuracy, pipeline accuracy, hard-negative discrimination, UNKNOWN calibration,
    tool efficiency, and invalid output rate.
    """
    if not os.path.exists(val_file_path):
        # Fallback to workspace path
        val_file_path = os.path.join(WORKSPACE_ROOT, "datasets", "v9", "agentic_val_v9.json")

    with open(val_file_path, "r", encoding="utf-8") as f:
        val_cases = json.load(f)

    if max_cases > 0:
        val_cases = val_cases[:max_cases]

    print("=" * 96)
    print(f"EVALUATING MODEL ON V9 VALIDATION SET ({len(val_cases)} cases)")
    print("=" * 96)

    backend = AgenticRCABackend(
        provider=provider,
        mode="tool_assisted",
        max_iterations=4,
        temperature=0.1,
        workspace_root=WORKSPACE_ROOT
    )

    correct_count = 0
    pipe_correct = 0
    pipe_total = 0
    hn_correct = 0
    hn_total = 0
    unk_correct = 0
    unk_total = 0
    invalid_count = 0
    total_steps = 0
    total_tokens = 0
    total_latency_ms = 0.0

    records = []

    for i, case in enumerate(val_cases):
        task_id = case.get("task_id", f"val_{i}")
        fam = case.get("design_family", "generic")
        ex_type = case.get("example_type", "POSITIVE_RCA")
        gt_sig = case.get("ground_truth_signal", "unknown")
        cand_sigs = case.get("candidate_signals", [])

        meta = {
            "symptom": case.get("defect_mechanism", "ASSERTION_VIOLATION"),
            "design_family": fam,
            "ground_truth_signals": [gt_sig],
            "candidate_signals": cand_sigs,
            "target_signals": cand_sigs
        }

        diag = backend.diagnose_failure(task_id, fam, meta)
        pred_sig = diag.root_cause_signal
        is_corr = (pred_sig.lower() == gt_sig.lower())

        if diag.rca_status == "INVALID_OUTPUT":
            invalid_count += 1

        if is_corr:
            correct_count += 1

        if fam == "pipeline":
            pipe_total += 1
            if is_corr:
                pipe_correct += 1

        if ex_type == "HARD_NEGATIVE":
            hn_total += 1
            if is_corr:
                hn_correct += 1

        if ex_type == "UNKNOWN_INSUFFICIENT":
            unk_total += 1
            if is_corr:
                unk_correct += 1

        total_steps += diag.steps_taken
        if diag.llm_tokens > 0:
            total_tokens += diag.llm_tokens
        total_latency_ms += diag.wall_clock_ms

        records.append({
            "task_id": task_id,
            "family": fam,
            "type": ex_type,
            "ground_truth": gt_sig,
            "prediction": pred_sig,
            "correct": is_corr,
            "status": diag.rca_status,
            "steps": diag.steps_taken,
            "latency_ms": diag.wall_clock_ms
        })

        if (i + 1) % 15 == 0 or (i + 1) == len(val_cases):
            print(f"  Processed {i+1:>3d}/{len(val_cases)} | Running Acc: {100.0*correct_count/(i+1):.1f}% | Pipe Acc: {100.0*pipe_correct/max(1, pipe_total):.1f}%")

    n = len(val_cases)
    summary = {
        "total_cases": n,
        "overall_accuracy_pct": (correct_count / n * 100.0) if n > 0 else 0.0,
        "pipeline_accuracy_pct": (pipe_correct / pipe_total * 100.0) if pipe_total > 0 else 0.0,
        "hard_negative_accuracy_pct": (hn_correct / hn_total * 100.0) if hn_total > 0 else 0.0,
        "unknown_calibration_pct": (unk_correct / unk_total * 100.0) if unk_total > 0 else 0.0,
        "invalid_output_rate_pct": (invalid_count / n * 100.0) if n > 0 else 0.0,
        "avg_steps_per_investigation": (total_steps / n) if n > 0 else 0.0,
        "avg_tokens_per_investigation": (total_tokens / n) if n > 0 else 0.0,
        "avg_latency_ms": (total_latency_ms / n) if n > 0 else 0.0,
        "pipe_count": f"{pipe_correct}/{pipe_total}",
        "hn_count": f"{hn_correct}/{hn_total}",
        "unk_count": f"{unk_correct}/{unk_total}"
    }

    print("\n" + "=" * 96)
    print("V9 VALIDATION EVALUATION SUMMARY")
    print("=" * 96)
    print(f"Overall Accuracy:            {summary['overall_accuracy_pct']:.1f}% ({correct_count}/{n})")
    print(f"Pipeline Specific Accuracy:  {summary['pipeline_accuracy_pct']:.1f}% ({pipe_correct}/{pipe_total})")
    print(f"Hard-Negative Accuracy:      {summary['hard_negative_accuracy_pct']:.1f}% ({hn_correct}/{hn_total})")
    print(f"UNKNOWN Calibration:         {summary['unknown_calibration_pct']:.1f}% ({unk_correct}/{unk_total})")
    print(f"Invalid Output Rate:         {summary['invalid_output_rate_pct']:.1f}% ({invalid_count}/{n})")
    print(f"Avg Investigation Steps:     {summary['avg_steps_per_investigation']:.2f} turns")
    print(f"Avg Latency:                 {summary['avg_latency_ms']:.1f} ms")
    print("=" * 96)

    return {"summary": summary, "records": records}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter_path", type=str, default=None)
    parser.add_argument("--max_cases", type=int, default=-1)
    parser.add_argument("--val_file", type=str, default="C:/Users/varad/ml-cache/rca-reuse/v9/datasets/agentic_val_v9.json")
    args = parser.parse_args()

    provider = PeftLLMProvider(
        base_model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        adapter_path=args.adapter_path
    )
    evaluate_v9_validation(provider, val_file_path=args.val_file, max_cases=args.max_cases)
