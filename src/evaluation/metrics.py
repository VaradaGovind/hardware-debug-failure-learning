import json
import os
import pandas as pd
from typing import List, Dict, Any

class MetricsCalculator:
    def __init__(self, raw_results_dir: str):
        self.raw_results_dir = raw_results_dir

    def calculate_metrics(self) -> pd.DataFrame:
        metrics = []
        for file in os.listdir(self.raw_results_dir):
            if file.endswith("_summary.json"):
                with open(os.path.join(self.raw_results_dir, file), "r") as f:
                    summary = json.load(f)
                    run_id = summary["run_id"]
                    agent_type = "unknown"
                    try:
                        with open(os.path.join(self.raw_results_dir, f"{run_id}.jsonl"), "r") as lf:
                            first_step = json.loads(lf.readline())
                            agent_type = first_step["agent"]
                    except:
                        pass
                        
                    metrics.append({
                        "run_id": summary["run_id"],
                        "agent": agent_type,
                        "success": 1 if summary["final_outcome"] == "SUCCESS" else 0,
                        "tool_calls": summary["tool_calls"],
                        "waveform_queries": summary["waveform_queries"]
                    })
        return pd.DataFrame(metrics)

    def calculate_davr(self, baseline_df, constrained_df) -> float:
        """Computes Dead-End Avoidance Rate (DAVR) relative to baseline failures."""
        baseline_fails = baseline_df[baseline_df['success'] == 0]
        constrained_fails = constrained_df[constrained_df['success'] == 0]
        
        if len(baseline_fails) == 0:
            return 0.0
            
        if len(constrained_fails) == 0:
            return 1.0
            
        davr = 1.0 - (len(constrained_fails) / len(baseline_fails))
        return davr


def compute_rca_vs_reuse_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes rigorous statistical and operational metrics for paired RCA vs. RCA-Reuse evaluations.
    Safely handles boundary conditions (zero reuse, zero failures, token availability).
    """
    total_manifestations = len(records)
    if total_manifestations == 0:
        return {
            "total_manifestations": 0,
            "status": "EMPTY_RECORDS"
        }

    sources = [r for r in records if r.get("is_source_manifestation", r.get("is_source", False))]
    targets = [r for r in records if not r.get("is_source_manifestation", r.get("is_source", False))]
    
    # Baseline Metrics
    baseline_correct = sum(1 for r in records if r.get("baseline_correct", r.get("baseline_rca_correct", False)))
    baseline_ops = sum(r.get("baseline_tool_calls", 0) for r in records)
    baseline_tokens = sum(r.get("baseline_llm_tokens", 0) for r in records if r.get("baseline_llm_tokens", -1) >= 0)
    baseline_llm_calls = sum(r.get("baseline_llm_calls", 0) for r in records)
    baseline_wall_ms = sum(r.get("baseline_wall_clock_ms", 0.0) for r in records)
    
    # Reuse Metrics
    reuse_correct = sum(1 for r in records if r.get("final_reuse_correct", r.get("reuse_pipeline_correct", False)))
    reuse_ops = sum(r.get("reuse_tool_calls", r.get("reuse_total_ops", 0)) for r in records)
    reuse_tokens = sum(r.get("reuse_llm_tokens", 0) for r in records if r.get("reuse_llm_tokens", -1) >= 0)
    reuse_llm_calls = sum(r.get("reuse_llm_calls", 0) for r in records)
    reuse_wall_ms = sum(r.get("reuse_wall_clock_ms", 0.0) for r in records)
    
    # Target Arrival Breakdown
    reuse_attempts = len(targets)
    successful_reuses = sum(1 for r in targets if r.get("reused_prior_rca", False) and r.get("final_reuse_correct", False))
    unsafe_reuses = sum(1 for r in targets if r.get("reused_prior_rca", False) and not r.get("final_reuse_correct", False))
    total_reuses_applied = sum(1 for r in targets if r.get("reused_prior_rca", False))
    fallbacks = sum(1 for r in targets if r.get("fallback_rca_executed", False))
    
    # Theoretical ground-truth reusable opportunities (MATCH vs MISMATCH)
    true_reusable = sum(1 for r in targets if r.get("ground_truth_match") == "MATCH")
    true_non_reusable = len(targets) - true_reusable

    # Rates with safe division
    baseline_acc = (baseline_correct / total_manifestations) * 100.0 if total_manifestations > 0 else 0.0
    reuse_acc = (reuse_correct / total_manifestations) * 100.0 if total_manifestations > 0 else 0.0
    
    reuse_precision = (successful_reuses / total_reuses_applied) * 100.0 if total_reuses_applied > 0 else 100.0
    false_reuse_rate = (unsafe_reuses / total_reuses_applied) * 100.0 if total_reuses_applied > 0 else 0.0
    fallback_rate = (fallbacks / reuse_attempts) * 100.0 if reuse_attempts > 0 else 0.0
    
    positive_transfer = (successful_reuses / true_reusable) * 100.0 if true_reusable > 0 else 0.0
    correct_rejections = sum(1 for r in targets if r.get("ground_truth_match") == "MISMATCH" and r.get("fallback_rca_executed", False))
    negative_rejection_rate = (correct_rejections / true_non_reusable) * 100.0 if true_non_reusable > 0 else 100.0

    # Compression & Work Reduction
    scr = (baseline_ops / reuse_ops) if reuse_ops > 0 else 1.0
    work_reduction_pct = ((baseline_ops - reuse_ops) / baseline_ops) * 100.0 if baseline_ops > 0 else 0.0
    rca_avoided = total_manifestations - (len(sources) + fallbacks)
    
    token_reduction_pct = ((baseline_tokens - reuse_tokens) / baseline_tokens) * 100.0 if baseline_tokens > 0 else 0.0
    llm_call_reduction_pct = ((baseline_llm_calls - reuse_llm_calls) / baseline_llm_calls) * 100.0 if baseline_llm_calls > 0 else 0.0
    latency_reduction_pct = ((baseline_wall_ms - reuse_wall_ms) / baseline_wall_ms) * 100.0 if baseline_wall_ms > 0 else 0.0

    return {
        "total_manifestations": total_manifestations,
        "source_cases": len(sources),
        "target_arrivals": len(targets),
        "baseline_correct_count": baseline_correct,
        "baseline_accuracy_pct": baseline_acc,
        "reuse_pipeline_correct_count": reuse_correct,
        "reuse_pipeline_accuracy_pct": reuse_acc,
        "rca_invocations_baseline": total_manifestations,
        "rca_invocations_reuse": len(sources) + fallbacks,
        "rca_avoided_count": rca_avoided,
        "reuse_attempts": reuse_attempts,
        "total_reuses_applied": total_reuses_applied,
        "successful_reuses": successful_reuses,
        "unsafe_reuses": unsafe_reuses,
        "fallback_count": fallbacks,
        "fallback_rate_pct": fallback_rate,
        "reuse_precision_pct": reuse_precision,
        "false_reuse_rate_pct": false_reuse_rate,
        "positive_transfer_pct": positive_transfer,
        "negative_rejection_rate_pct": negative_rejection_rate,
        "baseline_total_ops": baseline_ops,
        "reuse_total_ops": reuse_ops,
        "search_compression_ratio": scr,
        "work_reduction_pct": work_reduction_pct,
        "baseline_llm_tokens": baseline_tokens,
        "reuse_llm_tokens": reuse_tokens,
        "token_reduction_pct": token_reduction_pct,
        "baseline_llm_calls": baseline_llm_calls,
        "reuse_llm_calls": reuse_llm_calls,
        "llm_call_reduction_pct": llm_call_reduction_pct,
        "baseline_wall_ms": baseline_wall_ms,
        "reuse_wall_ms": reuse_wall_ms,
        "latency_reduction_pct": latency_reduction_pct
    }

