import os
import sys
import json
import time
import math
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.agent.llm_provider import PeftLLMProvider
from src.agent.agentic_rca_backend import AgenticRCABackend
from src.evaluation.rca_vs_reuse_harness import RCAReuseEvaluator, RCABackend


def evaluate_suite(backend: AgenticRCABackend, cases: List[Dict[str, Any]], suite_name: str) -> Dict[str, Any]:
    print(f"\n--- Evaluating Suite: {suite_name} ({len(cases)} cases) ---")
    correct = 0
    invalid = 0
    unknown_correct = 0
    unknown_total = 0
    hard_neg_correct = 0
    hard_neg_total = 0
    fam_stats: Dict[str, Dict[str, int]] = {}
    type_stats: Dict[str, Dict[str, int]] = {}
    records = []

    t0 = time.time()
    for idx, case in enumerate(cases):
        t_id = case.get("task_id", f"case_{idx}")
        fam = case.get("design_family", case.get("family", "generic"))
        ex_type = case.get("example_type", "POSITIVE_RCA")
        gt = case.get("ground_truth_signal", "unknown")
        cands = case.get("candidate_signals", [])

        meta = {
            "symptom": case.get("defect_mechanism", case.get("symptom", "ASSERTION_VIOLATION")),
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
        if diag.rca_status in ["INVALID_OUTPUT", "MODEL_OUTPUT_INVALID"]:
            invalid += 1

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

    total = len(cases)
    acc = (correct / total) * 100.0 if total > 0 else 0.0

    z = 1.96
    p = correct / total if total > 0 else 0
    denom = 1 + z**2 / total if total > 0 else 1
    center = (p + z**2 / (2 * total)) / denom if total > 0 else 0
    spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denom if total > 0 else 0
    ci_low = max(0.0, (center - spread) * 100.0)
    ci_high = min(100.0, (center + spread) * 100.0)

    elapsed = time.time() - t0
    print(f"  [{suite_name}] Accuracy: {acc:.1f}% ({correct}/{total}) | Invalid: {invalid} ({invalid/total*100:.1f}%) | Time: {elapsed:.1f}s")

    return {
        "suite_name": suite_name,
        "total_cases": total,
        "overall_accuracy_pct": round(acc, 2),
        "ci_95_pct": [round(ci_low, 1), round(ci_high, 1)],
        "correct_count": correct,
        "invalid_output_rate_pct": round((invalid / total) * 100.0, 2),
        "unknown_accuracy_pct": round((unknown_correct / unknown_total * 100.0) if unknown_total > 0 else 0.0, 2),
        "unknown_counts": f"{unknown_correct}/{unknown_total}",
        "hard_negative_accuracy_pct": round((hard_neg_correct / hard_neg_total * 100.0) if hard_neg_total > 0 else 0.0, 2),
        "hard_negative_counts": f"{hard_neg_correct}/{hard_neg_total}",
        "family_breakdown": {f: {"acc_pct": round(s["correct"]/s["total"]*100.0, 1), "counts": f"{s['correct']}/{s['total']}"} for f, s in fam_stats.items()},
        "type_breakdown": {t: {"acc_pct": round(s["correct"]/s["total"]*100.0, 1), "counts": f"{s['correct']}/{s['total']}"} for t, s in type_stats.items()},
        "records": records
    }


def run_full_v10_study(adapter_path: str, model_label: str = "V10_Model_B_Topological") -> Dict[str, Any]:
    print("=" * 96)
    print(f"EXPERIMENT V10: FULL MULTI-SUITE EVALUATION & V8 REUSE STUDY ({model_label})")
    print("=" * 96)

    # 1. Load Suites
    val_path = os.path.join(WORKSPACE_ROOT, "datasets", "v10", "agentic_val_v10.json")
    gen_path = os.path.join(WORKSPACE_ROOT, "datasets", "v10", "agentic_gen_v10.json")
    pipe_gen_path = os.path.join(WORKSPACE_ROOT, "datasets", "v9", "pipeline_generalization_suite.json")

    with open(val_path, "r", encoding="utf-8") as fp:
        val_cases = json.load(fp)
    with open(gen_path, "r", encoding="utf-8") as fp:
        gen_cases = json.load(fp)
    with open(pipe_gen_path, "r", encoding="utf-8") as fp:
        pipe_gen_cases = json.load(fp)

    # 2. Initialize Provider & Backend
    provider = PeftLLMProvider(
        base_model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        adapter_path=adapter_path
    )
    backend = AgenticRCABackend(
        provider=provider,
        mode="tool_assisted",
        max_iterations=4,
        max_tokens=192,
        temperature=0.1,
        workspace_root=WORKSPACE_ROOT
    )

    # 3. Evaluate Disjoint Validation Suite
    val_res = evaluate_suite(backend, val_cases, "V10_Disjoint_Validation_Suite")

    # 4. Evaluate Unseen Topology Generalization Suites
    gen_res = evaluate_suite(backend, gen_cases, "V10_Unseen_Topology_Suite")
    pipe_gen_res = evaluate_suite(backend, pipe_gen_cases, "V10_Pipeline_Generalization_Suite")

    # 5. Evaluate End-to-End V8 Reuse Stream on Canonical 25-Case Frozen Benchmark
    print("\n--- Running Canonical 25-Case Frozen Benchmark via V8 Reuse Stack ---", flush=True)
    from experiments.run_rca_vs_reuse_controlled_comparison import get_controlled_comparison_stream
    stream = get_controlled_comparison_stream()
    rtl_dir = os.path.join(WORKSPACE_ROOT, "rtl")
    evaluator = RCAReuseEvaluator(backend=backend, rtl_dir=rtl_dir)
    reuse_report = evaluator.evaluate_stream(stream)

    study_summary = {
        "model_label": model_label,
        "adapter_path": adapter_path,
        "v10_disjoint_validation": val_res,
        "v10_unseen_topology_generalization": gen_res,
        "v10_pipeline_generalization": pipe_gen_res,
        "frozen_benchmark_25_case_reuse": reuse_report
    }

    reports_dir = os.path.join(WORKSPACE_ROOT, "results", "reports")
    cost_dir = os.path.join(WORKSPACE_ROOT, "results", "cost_analysis")
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(cost_dir, exist_ok=True)

    out_report = os.path.join(reports_dir, f"{model_label.lower()}_evaluation_report.json")
    with open(out_report, "w", encoding="utf-8") as fp:
        json.dump(study_summary, fp, indent=2)

    out_cost = os.path.join(cost_dir, f"{model_label.lower()}_end_to_end_comparison.json")
    with open(out_cost, "w", encoding="utf-8") as fp:
        json.dump(reuse_report, fp, indent=2)

    sa = reuse_report.get("safety_and_accuracy_metrics", {})
    op = reuse_report.get("operational_metrics", {})

    print("\n" + "=" * 96, flush=True)
    print(f"V10 STUDY COMPLETED FOR {model_label}:", flush=True)
    print(f"  - Validation Accuracy:             {val_res['overall_accuracy_pct']:.1f}%", flush=True)
    print(f"  - Unseen Topology Generalization:  {gen_res['overall_accuracy_pct']:.1f}%", flush=True)
    print(f"  - Pipeline Generalization (5-Case):{pipe_gen_res['overall_accuracy_pct']:.1f}%", flush=True)
    print(f"  - Frozen Benchmark Stream Accuracy:{sa.get('reuse_accuracy_pct', 0.0):.1f}%", flush=True)
    print(f"  - Autonomous Reuses Applied:       {sa.get('autonomous_reuses', 0)}/20", flush=True)
    print(f"  - Unsafe False Reuses Observed:    {sa.get('false_positive_reuses', 0)}/20", flush=True)
    print(f"  - Avoided Investigations:          {sa.get('avoided_investigations', 0)}", flush=True)
    print(f"  - Token Savings:                   {op.get('savings_pct_tokens', 0.0):.1f}%", flush=True)
    print(f"  - Latency Savings:                 {op.get('savings_pct_wall_clock', 0.0):.1f}%", flush=True)
    print("=" * 96, flush=True)

    return study_summary


if __name__ == "__main__":
    adapter = "C:/Users/varad/ml-cache/rca-reuse/v10/checkpoints/v10_model_b_topological_lora/best_v10_checkpoint"
    label = "V10_Model_B_Topological"
    if len(sys.argv) > 1:
        adapter = sys.argv[1]
    if len(sys.argv) > 2:
        label = sys.argv[2]
    run_full_v10_study(adapter, label)
