import os
import sys
import json
import time
import math
from typing import Dict, Any, List

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.agent.llm_provider import PeftLLMProvider
from src.agent.agentic_rca_backend import AgenticRCABackend


def evaluate_checkpoint_on_val(adapter_path: str, model_label: str, val_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    print("=" * 80)
    print(f"EVALUATING {model_label} ON COMPLETE VALIDATION SET ({len(val_cases)} cases)")
    print("=" * 80)

    provider = PeftLLMProvider(
        base_model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        adapter_path=adapter_path
    )

    backend = AgenticRCABackend(
        provider=provider,
        mode="tool_assisted",
        max_iterations=4,
        max_tokens=192,  # Compact budget for tool/conclude JSON
        temperature=0.1,
        workspace_root=WORKSPACE_ROOT
    )

    correct = 0
    invalid = 0
    fam_stats = {}
    type_stats = {}
    records = []

    t0 = time.time()
    for idx, case in enumerate(val_cases):
        t_id = case.get("task_id", f"val_{idx}")
        fam = case.get("design_family", "generic")
        ex_type = case.get("example_type", "POSITIVE_RCA")
        gt = case.get("ground_truth_signal", "unknown")
        cands = case.get("candidate_signals", [])

        meta = {
            "symptom": case.get("defect_mechanism", "ASSERTION_VIOLATION"),
            "design_family": fam,
            "ground_truth_signals": [gt],
            "candidate_signals": cands,
            "target_signals": cands
        }

        diag = backend.diagnose_failure(t_id, fam, meta)
        pred = diag.root_cause_signal
        is_corr = (pred.lower() == gt.lower())

        if is_corr:
            correct += 1
        if diag.rca_status == "INVALID_OUTPUT":
            invalid += 1

        fam_stats.setdefault(fam, {"total": 0, "correct": 0})
        fam_stats[fam]["total"] += 1
        if is_corr:
            fam_stats[fam]["correct"] += 1

        type_stats.setdefault(ex_type, {"total": 0, "correct": 0})
        type_stats[ex_type]["total"] += 1
        if is_corr:
            type_stats[ex_type]["correct"] += 1

        records.append({
            "task_id": t_id,
            "family": fam,
            "type": ex_type,
            "ground_truth": gt,
            "prediction": pred,
            "correct": is_corr,
            "status": diag.rca_status,
            "steps": diag.steps_taken
        })

        if (idx + 1) % 20 == 0 or (idx + 1) == len(val_cases):
            elapsed = time.time() - t0
            print(f"  [{model_label}] Processed {idx+1}/{len(val_cases)} | Acc: {correct/(idx+1)*100:.1f}% | Elapsed: {elapsed:.1f}s")

    total = len(val_cases)
    acc = (correct / total) * 100.0 if total > 0 else 0.0
    
    # Calculate Wilson 95% confidence interval
    z = 1.96
    p = correct / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denom
    ci_low = max(0.0, (center - spread) * 100.0)
    ci_high = min(100.0, (center + spread) * 100.0)

    summary = {
        "model_label": model_label,
        "total_cases": total,
        "overall_accuracy_pct": acc,
        "ci_95_pct": [round(ci_low, 1), round(ci_high, 1)],
        "correct_count": correct,
        "invalid_output_rate_pct": (invalid / total) * 100.0,
        "family_breakdown": {f: {"acc_pct": round(s["correct"]/s["total"]*100.0, 1), "counts": f"{s['correct']}/{s['total']}"} for f, s in fam_stats.items()},
        "type_breakdown": {t: {"acc_pct": round(s["correct"]/s["total"]*100.0, 1), "counts": f"{s['correct']}/{s['total']}"} for t, s in type_stats.items()},
        "records": records
    }
    return summary


def run_full_comparison():
    val_path = os.path.join(WORKSPACE_ROOT, "datasets", "v9", "agentic_val_v9.json")
    with open(val_path, "r", encoding="utf-8") as f:
        val_cases = json.load(f)

    v7_adapter = "C:/Users/varad/ml-cache/rca-reuse/v7/checkpoints/soup_v7_qwen_lora/best_v7_checkpoint"
    v9_adapter = "C:/Users/varad/ml-cache/rca-reuse/v9/checkpoints/v9_agentic_sft_lora/best_v9_checkpoint"

    res_v7 = evaluate_checkpoint_on_val(v7_adapter, "V7_V8_Baseline", val_cases)
    res_v9 = evaluate_checkpoint_on_val(v9_adapter, "V9_Agentic_SFT", val_cases)

    comparison = {
        "validation_set_size": len(val_cases),
        "v7_v8_baseline": res_v7,
        "v9_agentic_sft": res_v9
    }

    out_file = os.path.join(WORKSPACE_ROOT, "results", "reports", "v9_full_validation_comparison.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    print("\n" + "=" * 80)
    print("FULL VALIDATION COMPARISON SUMMARY (134 CASES)")
    print("=" * 80)
    print(f"Baseline Overall Accuracy: {res_v7['overall_accuracy_pct']:.1f}% (95% CI: {res_v7['ci_95_pct'][0]}% - {res_v7['ci_95_pct'][1]}%)")
    print(f"V9 SFT Overall Accuracy:   {res_v9['overall_accuracy_pct']:.1f}% (95% CI: {res_v9['ci_95_pct'][0]}% - {res_v9['ci_95_pct'][1]}%)")
    print(f"Baseline Invalid Rate:     {res_v7['invalid_output_rate_pct']:.1f}%")
    print(f"V9 SFT Invalid Rate:       {res_v9['invalid_output_rate_pct']:.1f}%")
    print("\nSaved full validation comparison to:", out_file)


if __name__ == "__main__":
    run_full_comparison()
