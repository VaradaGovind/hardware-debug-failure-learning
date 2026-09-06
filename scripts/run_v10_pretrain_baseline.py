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


def run_pretrain_baseline():
    print("=" * 88)
    print("EXPERIMENT V10: PRE-TRAIN BASELINE EVALUATION ON FULL V10 VALIDATION SUITE")
    print("=" * 88)

    val_path = os.path.join(WORKSPACE_ROOT, "datasets", "v10", "agentic_val_v10.json")
    reports_dir = os.path.join(WORKSPACE_ROOT, "results", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    with open(val_path, "r", encoding="utf-8") as fp:
        val_cases = json.load(fp)

    v7_adapter = "C:/Users/varad/ml-cache/rca-reuse/v7/checkpoints/soup_v7_qwen_lora/best_v7_checkpoint"

    print(f"[*] Base Model: Qwen/Qwen2.5-Coder-1.5B-Instruct")
    print(f"[*] Baseline Adapter: {v7_adapter}")
    print(f"[*] Total Held-Out Disjoint Validation Cases: {len(val_cases)}")

    provider = PeftLLMProvider(
        base_model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        adapter_path=v7_adapter
    )

    backend = AgenticRCABackend(
        provider=provider,
        mode="tool_assisted",
        max_iterations=4,
        max_tokens=192,
        temperature=0.1,
        workspace_root=WORKSPACE_ROOT
    )

    correct_count = 0
    invalid_count = 0
    unknown_correct = 0
    unknown_total = 0
    hard_neg_correct = 0
    hard_neg_total = 0
    fam_stats: Dict[str, Dict[str, int]] = {}
    type_stats: Dict[str, Dict[str, int]] = {}
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
            correct_count += 1
        if diag.rca_status == "INVALID_OUTPUT":
            invalid_count += 1

        if gt.lower() == "unknown":
            unknown_total += 1
            if is_corr:
                unknown_correct += 1

        if ex_type == "HARD_NEGATIVE":
            hard_neg_total += 1
            if is_corr:
                hard_neg_correct += 1

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
            print(f"  [Progress] {idx+1}/{len(val_cases)} | Acc: {correct_count/(idx+1)*100:.1f}% | Elapsed: {elapsed:.1f}s")

    total = len(val_cases)
    acc = (correct_count / total) * 100.0 if total > 0 else 0.0

    # Wilson 95% CI
    z = 1.96
    p = correct_count / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denom
    ci_low = max(0.0, (center - spread) * 100.0)
    ci_high = min(100.0, (center + spread) * 100.0)

    report = {
        "model_label": "Frozen_V8_Operational_Baseline",
        "adapter_path": v7_adapter,
        "total_cases": total,
        "overall_accuracy_pct": round(acc, 2),
        "ci_95_pct": [round(ci_low, 1), round(ci_high, 1)],
        "correct_count": correct_count,
        "invalid_output_rate_pct": round((invalid_count / total) * 100.0, 2),
        "unknown_accuracy_pct": round((unknown_correct / unknown_total * 100.0) if unknown_total > 0 else 0.0, 2),
        "unknown_counts": f"{unknown_correct}/{unknown_total}",
        "hard_negative_accuracy_pct": round((hard_neg_correct / hard_neg_total * 100.0) if hard_neg_total > 0 else 0.0, 2),
        "hard_negative_counts": f"{hard_neg_correct}/{hard_neg_total}",
        "family_breakdown": {f: {"acc_pct": round(s["correct"]/s["total"]*100.0, 1), "counts": f"{s['correct']}/{s['total']}"} for f, s in fam_stats.items()},
        "type_breakdown": {t: {"acc_pct": round(s["correct"]/s["total"]*100.0, 1), "counts": f"{s['correct']}/{s['total']}"} for t, s in type_stats.items()},
        "records": records
    }

    out_file = os.path.join(reports_dir, "v10_pretrain_validation_baseline.json")
    with open(out_file, "w", encoding="utf-8") as fp:
        json.dump(report, fp, indent=2)

    print("\n" + "=" * 88)
    print("PRE-TRAIN BASELINE RESULTS ON V10 VALIDATION SET:")
    print("=" * 88)
    print(f"Overall Accuracy:       {acc:.1f}% (95% CI: {ci_low:.1f}% - {ci_high:.1f}%)")
    print(f"Pipeline Accuracy:      {report['family_breakdown'].get('pipeline', {}).get('acc_pct', 0.0)}%")
    print(f"Invalid Output Rate:    {report['invalid_output_rate_pct']:.1f}%")
    print(f"UNKNOWN Accuracy:       {report['unknown_accuracy_pct']:.1f}%")
    print(f"Report saved to:        {out_file}")


if __name__ == "__main__":
    run_pretrain_baseline()
