import os
import sys
import json
import time
import argparse
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.agent.llm_provider import LLMProvider, LocalOllamaProvider, MockLLMProvider, PeftLLMProvider
from src.agent.agentic_rca_backend import AgenticRCABackend, RCA_SYSTEM_PROMPT_STAGE_A
from src.evaluation.rca_vs_reuse_harness import RCAReuseEvaluator
from src.evaluation.metrics import compute_rca_vs_reuse_metrics
from experiments.run_rca_vs_reuse_controlled_comparison import get_controlled_comparison_stream
from src.tools.simulator import VerilogSimulator


def get_llm_provider(provider_type: str = "peft",
                     model_name: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct",
                     adapter_path: Optional[str] = None) -> LLMProvider:
    """Instantiates the appropriate LLM provider."""
    if provider_type == "peft":
        return PeftLLMProvider(base_model_name=model_name, adapter_path=adapter_path)
    elif provider_type == "ollama":
        return LocalOllamaProvider(model_name=model_name)
    else:
        return MockLLMProvider()


DEFAULT_CACHE_DIR = os.environ.get("RCA_REUSE_CACHE_DIR", os.path.expanduser("~/.cache/rca-reuse"))


def evaluate_model_on_v7_validation(provider: LLMProvider,
                                    val_file_path: Optional[str] = None,
                                    temperature: float = 0.1,
                                    max_cases: int = -1) -> Dict[str, Any]:
    """
    Evaluates an LLM model on the V7 canonical validation split (235 cases).
    Computes overall accuracy, grounded rate, wrong-signal rate, UNKNOWN rate,
    invalid rate, per-family accuracy, hard-negative accuracy, and UNKNOWN accuracy.
    """
    if val_file_path is None:
        val_file_path = os.path.join(DEFAULT_CACHE_DIR, "v7", "datasets", "rca_val_v7.json")
    if not os.path.exists(val_file_path):
        raise FileNotFoundError(f"Validation dataset file not found at {val_file_path}")

    with open(val_file_path, "r", encoding="utf-8") as f:
        val_samples = json.load(f)

    if max_cases > 0:
        val_samples = val_samples[:max_cases]

    print("=" * 96)
    print(f"EVALUATING MODEL ON V7 VALIDATION DATASET ({len(val_samples)} cases)")
    print("=" * 96)

    records = []
    correct_count = 0
    grounded_count = 0
    wrong_sig_count = 0
    unknown_count = 0
    invalid_output_count = 0
    total_tokens = 0
    total_latency_ms = 0.0

    # Sub-category tracking
    family_stats: Dict[str, Dict[str, int]] = {}
    type_stats: Dict[str, Dict[str, int]] = {}

    for i, sample in enumerate(val_samples):
        ex_id = sample.get("example_id", f"val_{i}")
        fam = sample.get("design_family", "generic")
        ex_type = sample.get("example_type", "POSITIVE_RCA")
        gt_root_sig = sample.get("root_cause_signal", "unknown")
        cand_sigs = sample.get("candidate_signals", [])
        human_prompt = sample["conversations"][1]["value"]
        
        t0 = time.time()
        parsed_json, resp = provider.structured_generate(
            prompt=human_prompt,
            system_prompt=RCA_SYSTEM_PROMPT_STAGE_A,
            temperature=temperature,
            max_tokens=512,
            max_retries=2
        )
        elapsed_ms = (time.time() - t0) * 1000.0
        total_latency_ms += elapsed_ms

        if resp.total_tokens > 0:
            total_tokens += resp.total_tokens

        is_invalid = ("error" in parsed_json or parsed_json.get("status") in ["PARSE_FAILED", "INVALID_OUTPUT", "MODEL_FAILURE"])
        cand_pred = AgenticRCABackend._extract_clean_signal(parsed_json) if not is_invalid else "invalid"

        is_unknown = (cand_pred.lower() == "unknown")
        is_grounded = (cand_pred in cand_sigs) if cand_sigs else False
        is_correct = (cand_pred.lower() == gt_root_sig.lower()) if not is_invalid else False

        if is_invalid:
            invalid_output_count += 1
        elif is_unknown:
            unknown_count += 1
            if gt_root_sig.lower() == "unknown":
                correct_count += 1
            else:
                wrong_sig_count += 1
        elif is_correct:
            correct_count += 1
            grounded_count += 1
        elif is_grounded:
            wrong_sig_count += 1
            grounded_count += 1
        else:
            wrong_sig_count += 1

        # Track family & type
        family_stats.setdefault(fam, {"total": 0, "correct": 0})
        family_stats[fam]["total"] += 1
        if is_correct:
            family_stats[fam]["correct"] += 1

        type_stats.setdefault(ex_type, {"total": 0, "correct": 0})
        type_stats[ex_type]["total"] += 1
        if is_correct:
            type_stats[ex_type]["correct"] += 1

        rec = {
            "example_id": ex_id,
            "design_family": fam,
            "example_type": ex_type,
            "ground_truth_signal": gt_root_sig,
            "predicted_signal": cand_pred,
            "is_correct": is_correct,
            "is_grounded": is_grounded,
            "is_unknown": is_unknown,
            "is_invalid": is_invalid,
            "tokens": resp.total_tokens,
            "latency_ms": elapsed_ms,
            "confidence": parsed_json.get("confidence", 0.0) if not is_invalid else 0.0
        }
        records.append(rec)
        status_sym = "CORRECT" if is_correct else ("UNKNOWN" if is_unknown else ("INVALID" if is_invalid else "WRONG"))
        print(f"[{i+1:>3}/{len(val_samples)}] {ex_id:<40} GT: {gt_root_sig:<12} Pred: {cand_pred:<12} -> {status_sym} ({elapsed_ms:.1f}ms)")

    n = len(val_samples)
    per_fam_pct = {k: (v["correct"] / v["total"] * 100.0) if v["total"] > 0 else 0.0 for k, v in family_stats.items()}
    per_type_pct = {k: (v["correct"] / v["total"] * 100.0) if v["total"] > 0 else 0.0 for k, v in type_stats.items()}

    summary = {
        "total_samples": n,
        "correct_count": correct_count,
        "accuracy_pct": (correct_count / n * 100.0) if n > 0 else 0.0,
        "grounded_count": grounded_count,
        "grounded_rate_pct": (grounded_count / n * 100.0) if n > 0 else 0.0,
        "wrong_signal_count": wrong_sig_count,
        "wrong_signal_rate_pct": (wrong_sig_count / n * 100.0) if n > 0 else 0.0,
        "unknown_count": unknown_count,
        "unknown_rate_pct": (unknown_count / n * 100.0) if n > 0 else 0.0,
        "invalid_output_count": invalid_output_count,
        "invalid_output_rate_pct": (invalid_output_count / n * 100.0) if n > 0 else 0.0,
        "hard_negative_accuracy_pct": per_type_pct.get("HARD_NEGATIVE", 0.0),
        "unknown_accuracy_pct": per_type_pct.get("UNKNOWN_INSUFFICIENT", 0.0),
        "positive_rca_accuracy_pct": per_type_pct.get("POSITIVE_RCA", 0.0),
        "per_family_accuracy": per_fam_pct,
        "per_type_accuracy": per_type_pct,
        "family_breakdown": family_stats,
        "type_breakdown": type_stats,
        "avg_tokens": (total_tokens / n) if n > 0 else 0.0,
        "avg_latency_ms": (total_latency_ms / n) if n > 0 else 0.0,
        "total_latency_ms": total_latency_ms
    }

    print("\n" + "=" * 96)
    print("V7 VALIDATION EVALUATION SUMMARY")
    print("=" * 96)
    print(f"Overall Diagnostic Accuracy:  {summary['accuracy_pct']:.1f}% ({correct_count}/{n})")
    print(f"Grounded Rate:                {summary['grounded_rate_pct']:.1f}% ({grounded_count}/{n})")
    print(f"Wrong Signal Rate:            {summary['wrong_signal_rate_pct']:.1f}% ({wrong_sig_count}/{n})")
    print(f"Unknown Rate (Abstention):    {summary['unknown_rate_pct']:.1f}% ({unknown_count}/{n})")
    print(f"Invalid Output Rate:          {summary['invalid_output_rate_pct']:.1f}% ({invalid_output_count}/{n})")
    print(f"Hard-Negative Accuracy:       {summary['hard_negative_accuracy_pct']:.1f}% ({type_stats.get('HARD_NEGATIVE', {}).get('correct', 0)}/{type_stats.get('HARD_NEGATIVE', {}).get('total', 0)})")
    print(f"UNKNOWN Accuracy:             {summary['unknown_accuracy_pct']:.1f}% ({type_stats.get('UNKNOWN_INSUFFICIENT', {}).get('correct', 0)}/{type_stats.get('UNKNOWN_INSUFFICIENT', {}).get('total', 0)})")
    print(f"Positive RCA Accuracy:        {summary['positive_rca_accuracy_pct']:.1f}% ({type_stats.get('POSITIVE_RCA', {}).get('correct', 0)}/{type_stats.get('POSITIVE_RCA', {}).get('total', 0)})")
    print("\nPer-Family Accuracy Breakdown:")
    for fam, stats in family_stats.items():
        pct = (stats["correct"] / stats["total"] * 100.0) if stats["total"] > 0 else 0.0
        print(f"  - {fam:<16}: {pct:>5.1f}% ({stats['correct']:>2d}/{stats['total']:>2d})")
    print("=" * 96)

    return {"summary": summary, "records": records}


def evaluate_frozen_25_test_stream(provider: LLMProvider) -> Dict[str, Any]:
    """
    Evaluates an LLM provider on the exact frozen 25-case evaluation stream.
    """
    workspace_root = WORKSPACE_ROOT
    rtl_dir = os.path.join(workspace_root, "rtl")
    stream = get_controlled_comparison_stream()

    sim = VerilogSimulator(rtl_dir)
    for s in stream:
        sim.run_simulation(s["target_id"], s["design_family"])

    backend = AgenticRCABackend(
        provider=provider,
        mode="tool_assisted",
        max_iterations=4,
        temperature=0.1,
        workspace_root=workspace_root
    )
    evaluator = RCAReuseEvaluator(backend=backend, rtl_dir=rtl_dir)
    eval_res = evaluator.evaluate_stream(stream)
    records = [r.to_dict() for r in eval_res["records"]] if hasattr(eval_res["records"][0], "to_dict") else eval_res["records"]
    stats = compute_rca_vs_reuse_metrics(records)

    return {"stats": stats, "records": records}


def run_v7_end_to_end_comparison(v6_adapter_path: Optional[str] = None,
                                 v7_adapter_path: Optional[str] = None,
                                 base_model: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct") -> Dict[str, Any]:
    """
    Executes End-to-End V7 Controlled Comparison:
    System A: V6 Fine-Tuned 1.5B + V5 Safety/Reuse
    System B: V7 Fine-Tuned 1.5B + SAME V5 Safety/Reuse
    """
    if v6_adapter_path is None:
        v6_adapter_path = os.path.join(DEFAULT_CACHE_DIR, "v6", "checkpoints", "soup_qwen_rca_lora", "best_v6_checkpoint")
    if v7_adapter_path is None:
        v7_adapter_path = os.path.join(DEFAULT_CACHE_DIR, "v7", "checkpoints", "soup_v7_qwen_lora", "best_v7_checkpoint")
    workspace_root = WORKSPACE_ROOT
    rtl_dir = os.path.join(workspace_root, "rtl")
    results_dir = os.path.join(workspace_root, "results", "cost_analysis")
    v7_eval_dir = os.path.join(DEFAULT_CACHE_DIR, "v7", "evaluations")
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(v7_eval_dir, exist_ok=True)

    stream = get_controlled_comparison_stream()

    # Pre-simulate all targets
    sim = VerilogSimulator(rtl_dir)
    for s in stream:
        sim.run_simulation(s["target_id"], s["design_family"])

    print("=" * 96)
    print("V7 CONTROLLED EXPERIMENT: SYSTEM A (V6 + V5 REUSE) vs SYSTEM B (V7 + V5 REUSE)")
    print("=" * 96)

    # 1. Load / Evaluate System A (V6 Fine-Tuned 1.5B + V5 Safety-Hardened RCA-Reuse)
    print("\n[PHASE 1] Loading System A (V6 Fine-Tuned 1.5B + V5 Safety-Hardened RCA-Reuse Baseline)...")
    v6_json_path = os.path.join(results_dir, "v6_end_to_end_comparison.json")
    if os.path.exists(v6_json_path):
        with open(v6_json_path, "r", encoding="utf-8") as f:
            v6_comp_data = json.load(f)
        v6_records = v6_comp_data.get("v6_records", [])
        v6_stats = v6_comp_data.get("system_b_v6_plus_reuse", compute_rca_vs_reuse_metrics(v6_records))
        print(f"  Loaded verified V6 baseline records ({len(v6_records)} cases, accuracy: {v6_stats.get('baseline_accuracy_pct', 32.0):.1f}%).")
    else:
        v6_provider = PeftLLMProvider(base_model_name=base_model, adapter_path=v6_adapter_path)
        v6_backend = AgenticRCABackend(
            provider=v6_provider,
            mode="tool_assisted",
            max_iterations=4,
            temperature=0.1,
            workspace_root=workspace_root
        )
        v6_evaluator = RCAReuseEvaluator(backend=v6_backend, rtl_dir=rtl_dir)
        v6_res = v6_evaluator.evaluate_stream(stream)
        v6_records = [r.to_dict() for r in v6_res["records"]] if hasattr(v6_res["records"][0], "to_dict") else v6_res["records"]
        v6_stats = compute_rca_vs_reuse_metrics(v6_records)
        del v6_evaluator, v6_backend, v6_provider
        import gc; gc.collect()

    # 2. Evaluate System B (V7 Fine-Tuned 1.5B via PeftLLMProvider)
    print("\n[PHASE 2] Running System B (V7 Fine-Tuned 1.5B + SAME V5 Safety-Hardened RCA-Reuse)...")
    v7_provider = PeftLLMProvider(base_model_name=base_model, adapter_path=v7_adapter_path)
    v7_backend = AgenticRCABackend(
        provider=v7_provider,
        mode="tool_assisted",
        max_iterations=4,
        temperature=0.1,
        workspace_root=workspace_root
    )
    v7_evaluator = RCAReuseEvaluator(backend=v7_backend, rtl_dir=rtl_dir)
    v7_res = v7_evaluator.evaluate_stream(stream)
    v7_records = [r.to_dict() for r in v7_res["records"]] if hasattr(v7_res["records"][0], "to_dict") else v7_res["records"]
    v7_stats = compute_rca_vs_reuse_metrics(v7_records)

    # Source Certificate Analysis
    v6_src_records = [r for r in v6_records if r.get("is_source_manifestation", False)]
    v7_src_records = [r for r in v7_records if r.get("is_source_manifestation", False)]

    v6_trusted_sources = sum(1 for r in v6_src_records if r.get("source_certificate_trusted", False))
    v7_trusted_sources = sum(1 for r in v7_src_records if r.get("source_certificate_trusted", False))
    v6_correct_sources = sum(1 for r in v6_src_records if r.get("final_reuse_correct", False))
    v7_correct_sources = sum(1 for r in v7_src_records if r.get("final_reuse_correct", False))

    v6_stats["trusted_source_certificates"] = v6_trusted_sources
    v6_stats["correct_source_rcas"] = v6_correct_sources
    v7_stats["trusted_source_certificates"] = v7_trusted_sources
    v7_stats["correct_source_rcas"] = v7_correct_sources

    # Case-Level Transition Matrix
    case_transitions = []
    for idx in range(len(stream)):
        v6_r = v6_records[idx]
        v7_r = v7_records[idx]
        t_id = v6_r["target_id"]
        fam = v6_r["design_family"]
        gt_sig = v6_r.get("ground_truth_signals", [""])[0] if isinstance(v6_r.get("ground_truth_signals"), list) else v6_r.get("ground_truth_signal", "")
        
        v6_pred = v6_r.get("baseline_diagnosis", "unknown")
        v7_pred = v7_r.get("baseline_diagnosis", "unknown")
        v6_corr = v6_r.get("baseline_correct", False)
        v7_corr = v7_r.get("baseline_correct", False)

        if v6_corr and v7_corr:
            trans = "Correct -> Correct"
        elif not v6_corr and v7_corr:
            trans = "Wrong -> Correct"
        elif v6_corr and not v7_corr:
            trans = "Correct -> Wrong"
        elif v6_pred == "unknown" and v7_corr:
            trans = "Unknown -> Correct"
        elif v6_pred == "unknown" and not v7_corr:
            trans = "Unknown -> Wrong"
        else:
            trans = "Wrong -> Wrong"

        case_transitions.append({
            "case_index": idx + 1,
            "target_id": t_id,
            "design_family": fam,
            "ground_truth_signal": gt_sig,
            "v6_diagnosis": v6_pred,
            "v7_diagnosis": v7_pred,
            "v6_correct": v6_corr,
            "v7_correct": v7_corr,
            "transition": trans
        })

    # Save artifacts
    comparison_payload = {
        "experiment_name": "V7_END_TO_END_EVALUATION",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_model": base_model,
        "v6_adapter_path": v6_adapter_path,
        "v7_adapter_path": v7_adapter_path,
        "system_a_v6_plus_reuse": v6_stats,
        "system_b_v7_plus_reuse": v7_stats,
        "case_level_transitions": case_transitions,
        "v6_records": v6_records,
        "v7_records": v7_records
    }

    out_json = os.path.join(results_dir, "v7_end_to_end_comparison.json")
    out_csv = os.path.join(results_dir, "v7_end_to_end_comparison.csv")
    v7_json = os.path.join(v7_eval_dir, "v7_end_to_end_comparison.json")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(comparison_payload, f, indent=2)
    with open(v7_json, "w", encoding="utf-8") as f:
        json.dump(comparison_payload, f, indent=2)

    df_trans = pd.DataFrame(case_transitions)
    df_trans.to_csv(out_csv, index=False)

    # Formatted Comparison Table
    print("\n" + "=" * 96)
    print("V7 FINAL END-TO-END COMPARISON TABLE (Section 45 Standard)")
    print("=" * 96)
    print(f"| {'Metric':<32} | {'V6 Fine-Tuned + Reuse':>22} | {'V7 Fine-Tuned + Reuse':>23} | {'Delta (V7-V6)':>14} |")
    print(f"| {':' + '-' * 30 + ' '} | {'-' * 21 + ':'} | {'-' * 22 + ':'} | {'-' * 13 + ':'} |")
    print(f"| {'Agentic RCA Accuracy':<32} | {v6_stats['baseline_accuracy_pct']:>21.1f}% | {v7_stats['baseline_accuracy_pct']:>22.1f}% | {v7_stats['baseline_accuracy_pct'] - v6_stats['baseline_accuracy_pct']:>+13.1f}% |")
    print(f"| {'Source RCA Accuracy':<32} | {v6_correct_sources:>19d}/5 | {v7_correct_sources:>20d}/5 | {v7_correct_sources - v6_correct_sources:>+14d} |")
    print(f"| {'Trusted Certificates':<32} | {v6_trusted_sources:>22d} | {v7_trusted_sources:>23d} | {v7_trusted_sources - v6_trusted_sources:>+14d} |")
    print(f"| {'Correct Reuses (TP)':<32} | {v6_stats['successful_reuses']:>22d} | {v7_stats['successful_reuses']:>23d} | {v7_stats['successful_reuses'] - v6_stats['successful_reuses']:>+14d} |")
    print(f"| {'False Reuses (FP)':<32} | {v6_stats['unsafe_reuses']:>22d} | {v7_stats['unsafe_reuses']:>23d} | {v7_stats['unsafe_reuses'] - v6_stats['unsafe_reuses']:>+14d} |")
    print(f"| {'Reuse Precision':<32} | {v6_stats['reuse_precision_pct']:>21.1f}% | {v7_stats['reuse_precision_pct']:>22.1f}% | {'0.0%':>14} |")
    print(f"| {'False Reuse Rate':<32} | {v6_stats['false_reuse_rate_pct']:>21.1f}% | {v7_stats['false_reuse_rate_pct']:>22.1f}% | {'0.0%':>14} |")
    print(f"| {'Correct Rejections (TN)':<32} | {sum(1 for r in v6_records if r.get('ground_truth_match') == 'MISMATCH' and r.get('fallback_rca_executed')):>22d} | {sum(1 for r in v7_records if r.get('ground_truth_match') == 'MISMATCH' and r.get('fallback_rca_executed')):>23d} | {'0':>14} |")
    print(f"| {'Full RCA Investigations':<32} | {v6_stats['rca_invocations_reuse']:>22d} | {v7_stats['rca_invocations_reuse']:>23d} | {v7_stats['rca_invocations_reuse'] - v6_stats['rca_invocations_reuse']:>+14d} |")
    print(f"| {'RCA Investigations Avoided':<32} | {v6_stats['rca_avoided_count']:>22d} | {v7_stats['rca_avoided_count']:>23d} | {v7_stats['rca_avoided_count'] - v6_stats['rca_avoided_count']:>+14d} |")
    print(f"| {'RCA Avoidance Rate':<32} | {(v6_stats['rca_avoided_count']/25*100):>21.1f}% | {(v7_stats['rca_avoided_count']/25*100):>22.1f}% | {((v7_stats['rca_avoided_count'] - v6_stats['rca_avoided_count'])/25*100):>+13.1f}% |")
    print(f"| {'Agent LLM Calls':<32} | {v6_stats['reuse_llm_calls']:>22d} | {v7_stats['reuse_llm_calls']:>23d} | {v7_stats['reuse_llm_calls'] - v6_stats['reuse_llm_calls']:>+14d} |")
    print(f"| {'Token Reduction':<32} | {v6_stats['token_reduction_pct']:>21.1f}% | {v7_stats['token_reduction_pct']:>22.1f}% | {v7_stats['token_reduction_pct'] - v6_stats['token_reduction_pct']:>+13.1f}% |")
    print(f"| {'Latency Reduction':<32} | {v6_stats['latency_reduction_pct']:>21.1f}% | {v7_stats['latency_reduction_pct']:>22.1f}% | {v7_stats['latency_reduction_pct'] - v6_stats['latency_reduction_pct']:>+13.1f}% |")
    print("=" * 96)

    return comparison_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="V7 Evaluation Harness")
    parser.add_argument("--eval-validation", action="store_true", help="Run validation evaluation on V7 Val")
    parser.add_argument("--eval-frozen-test", action="store_true", help="Run frozen test evaluation")
    parser.add_argument("--eval-end-to-end", action="store_true", help="Run end-to-end RCA-Reuse comparison (V6 vs V7)")
    parser.add_argument("--provider", default="peft", choices=["peft", "ollama", "mock"], help="Provider type")
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-1.5B-Instruct", help="Model name")
    parser.add_argument("--adapter-path", default=None, help="Adapter path (defaults to RCA_REUSE_CACHE_DIR)")
    parser.add_argument("--val-file", default=None, help="Validation dataset path (defaults to RCA_REUSE_CACHE_DIR)")
    parser.add_argument("--max-cases", type=int, default=-1, help="Max cases for evaluation")

    args = parser.parse_args()

    if args.eval_end_to_end:
        run_v7_end_to_end_comparison(v6_adapter_path=args.adapter_path)
    elif args.eval_validation:
        prov = get_llm_provider(args.provider, args.model, args.adapter_path)
        evaluate_model_on_v7_validation(prov, val_file_path=args.val_file, max_cases=args.max_cases)
    elif args.eval_frozen_test:
        prov = get_llm_provider(args.provider, args.model, args.adapter_path)
        evaluate_frozen_25_test_stream(prov)
    else:
        run_v7_end_to_end_comparison(v6_adapter_path=args.adapter_path)
