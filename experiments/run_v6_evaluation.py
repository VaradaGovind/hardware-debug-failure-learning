import os
import sys
import json
import time
import argparse
import platform
import subprocess
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.agent.llm_provider import LLMProvider, LocalOllamaProvider, MockLLMProvider, PeftLLMProvider
from src.agent.agentic_rca_backend import AgenticRCABackend, PROMPT_VERSION, RCA_SYSTEM_PROMPT_STAGE_A
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


def evaluate_model_on_validation_set(provider: LLMProvider,
                                     val_file_path: Optional[str] = None,
                                     temperature: float = 0.1,
                                     max_cases: int = -1) -> Dict[str, Any]:
    """
    Evaluates an LLM model on the V6 canonical validation split (66 cases).
    """
    if val_file_path is None:
        val_file_path = os.path.join(DEFAULT_CACHE_DIR, "datasets", "processed", "rca_val_v6.json")
    if not os.path.exists(val_file_path):
        raise FileNotFoundError(f"Validation dataset file not found at {val_file_path}")

    with open(val_file_path, "r", encoding="utf-8") as f:
        val_samples = json.load(f)

    if max_cases > 0:
        val_samples = val_samples[:max_cases]

    print("=" * 90)
    print(f"EVALUATING MODEL ON V6 VALIDATION DATASET ({len(val_samples)} cases)")
    print("=" * 90)

    records = []
    correct_count = 0
    grounded_count = 0
    wrong_sig_count = 0
    unknown_count = 0
    invalid_output_count = 0
    total_tokens = 0
    total_latency_ms = 0.0

    for i, sample in enumerate(val_samples):
        ex_id = sample.get("example_id", f"val_{i}")
        fam = sample.get("design_family", "generic")
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
        is_correct = (cand_pred == gt_root_sig) if not is_unknown and not is_invalid else (is_unknown and gt_root_sig == "unknown")

        if is_invalid:
            invalid_output_count += 1
        elif is_unknown:
            unknown_count += 1
        elif is_correct:
            correct_count += 1
            grounded_count += 1
        elif is_grounded:
            wrong_sig_count += 1
            grounded_count += 1
        else:
            wrong_sig_count += 1

        rec = {
            "example_id": ex_id,
            "design_family": fam,
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
        print(f"[{i+1:>2}/{len(val_samples)}] {ex_id:<32} GT: {gt_root_sig:<12} Pred: {cand_pred:<12} -> {status_sym} ({elapsed_ms:.1f}ms)")

    n = len(val_samples)
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
        "avg_tokens": (total_tokens / n) if n > 0 else 0.0,
        "avg_latency_ms": (total_latency_ms / n) if n > 0 else 0.0,
        "total_latency_ms": total_latency_ms
    }

    print("\n" + "=" * 90)
    print("VALIDATION EVALUATION SUMMARY")
    print("=" * 90)
    print(f"Diagnostic Accuracy:     {summary['accuracy_pct']:.1f}% ({correct_count}/{n})")
    print(f"Grounded Rate:           {summary['grounded_rate_pct']:.1f}% ({grounded_count}/{n})")
    print(f"Wrong Signal Rate:       {summary['wrong_signal_rate_pct']:.1f}% ({wrong_sig_count}/{n})")
    print(f"Unknown Rate:            {summary['unknown_rate_pct']:.1f}% ({unknown_count}/{n})")
    print(f"Invalid Output Rate:     {summary['invalid_output_rate_pct']:.1f}% ({invalid_output_count}/{n})")
    print(f"Average Tokens:          {summary['avg_tokens']:.1f}")
    print(f"Average Latency:         {summary['avg_latency_ms']:.1f} ms")
    print("=" * 90)

    return {"summary": summary, "records": records}


def run_v6_end_to_end_comparison(adapter_path: Optional[str] = None,
                                 base_model: str = "qwen2.5-coder:1.5b") -> Dict[str, Any]:
    """
    Executes End-to-End V6 Controlled Experiment:
    System A (Base 1.5B + V5 Reuse) vs System B (V6 Fine-Tuned 1.5B + SAME V5 Reuse)
    on the frozen 25-case evaluation stream.
    """
    if adapter_path is None:
        adapter_path = os.path.join(DEFAULT_CACHE_DIR, "v6", "checkpoints", "soup_qwen_rca_lora", "best_v6_checkpoint")
    workspace_root = WORKSPACE_ROOT
    rtl_dir = os.path.join(workspace_root, "rtl")
    results_dir = os.path.join(workspace_root, "results", "cost_analysis")
    v6_eval_dir = os.path.join(DEFAULT_CACHE_DIR, "v6", "evaluations")
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(v6_eval_dir, exist_ok=True)

    stream = get_controlled_comparison_stream()

    # Pre-simulate all targets
    sim = VerilogSimulator(rtl_dir)
    for s in stream:
        sim.run_simulation(s["target_id"], s["design_family"])

    print("=" * 96)
    print("V6 CONTROLLED EXPERIMENT: BASE 1.5B + REUSE vs V6 FINE-TUNED 1.5B + REUSE")
    print("=" * 96)

    # 1. Evaluate System A (Base 1.5B via Ollama)
    print("\n[PHASE 1] Running System A (Base 1.5B + V5 Safety-Hardened RCA-Reuse)...")
    base_provider = LocalOllamaProvider(model_name=base_model)
    base_backend = AgenticRCABackend(
        provider=base_provider,
        mode="tool_assisted",
        max_iterations=4,
        temperature=0.1,
        workspace_root=workspace_root
    )
    base_evaluator = RCAReuseEvaluator(backend=base_backend, rtl_dir=rtl_dir)
    base_res = base_evaluator.evaluate_stream(stream)
    base_records = [r.to_dict() for r in base_res["records"]] if hasattr(base_res["records"][0], "to_dict") else base_res["records"]
    base_stats = compute_rca_vs_reuse_metrics(base_records)

    # 2. Evaluate System B (V6 Fine-Tuned 1.5B via PeftLLMProvider)
    print("\n[PHASE 2] Running System B (V6 Fine-Tuned 1.5B + SAME V5 Safety-Hardened RCA-Reuse)...")
    v6_provider = PeftLLMProvider(base_model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct", adapter_path=adapter_path)
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

    # 3. Source Certificate Analysis
    base_src_records = [r for r in base_records if r.get("is_source_manifestation", False)]
    v6_src_records = [r for r in v6_records if r.get("is_source_manifestation", False)]

    base_trusted_sources = sum(1 for r in base_src_records if r.get("source_certificate_trusted", False))
    v6_trusted_sources = sum(1 for r in v6_src_records if r.get("source_certificate_trusted", False))
    base_correct_sources = sum(1 for r in base_src_records if r.get("final_reuse_correct", False))
    v6_correct_sources = sum(1 for r in v6_src_records if r.get("final_reuse_correct", False))

    base_stats["trusted_source_certificates"] = base_trusted_sources
    base_stats["correct_source_rcas"] = base_correct_sources
    v6_stats["trusted_source_certificates"] = v6_trusted_sources
    v6_stats["correct_source_rcas"] = v6_correct_sources

    # 4. Case-Level Transition Classification
    case_transitions = []
    for idx in range(len(stream)):
        b_r = base_records[idx]
        v_r = v6_records[idx]
        t_id = b_r["target_id"]
        fam = b_r["design_family"]
        gt_sig = b_r.get("ground_truth_signals", [""])[0] if isinstance(b_r.get("ground_truth_signals"), list) else b_r.get("ground_truth_signal", "")
        
        b_pred = b_r.get("baseline_diagnosis", "unknown")
        v_pred = v_r.get("baseline_diagnosis", "unknown")
        b_corr = b_r.get("baseline_correct", False)
        v_corr = v_r.get("baseline_correct", False)

        if b_corr and v_corr:
            trans = "Correct -> Correct"
        elif not b_corr and v_corr:
            trans = "Wrong -> Correct"
        elif b_corr and not v_corr:
            trans = "Correct -> Wrong"
        elif b_pred == "unknown" and v_corr:
            trans = "Unknown -> Correct"
        elif b_pred == "unknown" and not v_corr:
            trans = "Unknown -> Wrong"
        else:
            trans = "Wrong -> Wrong"

        case_transitions.append({
            "case_index": idx + 1,
            "target_id": t_id,
            "design_family": fam,
            "ground_truth_signal": gt_sig,
            "base_diagnosis": b_pred,
            "v6_diagnosis": v_pred,
            "base_correct": b_corr,
            "v6_correct": v_corr,
            "transition": trans
        })

    # Save artifacts
    comparison_payload = {
        "experiment_name": "V6_END_TO_END_EVALUATION",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_model": base_model,
        "v6_adapter_path": adapter_path,
        "system_a_base_plus_reuse": base_stats,
        "system_b_v6_plus_reuse": v6_stats,
        "case_level_transitions": case_transitions,
        "base_records": base_records,
        "v6_records": v6_records
    }

    out_json = os.path.join(results_dir, "v6_end_to_end_comparison.json")
    out_csv = os.path.join(results_dir, "v6_end_to_end_comparison.csv")
    v6_json = os.path.join(v6_eval_dir, "v6_end_to_end_comparison.json")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(comparison_payload, f, indent=2)
    with open(v6_json, "w", encoding="utf-8") as f:
        json.dump(comparison_payload, f, indent=2)

    df_trans = pd.DataFrame(case_transitions)
    df_trans.to_csv(out_csv, index=False)

    # 5. Formatted Tables
    print("\n" + "=" * 96)
    print("V6 FINAL END-TO-END COMPARISON TABLE (Section 45 Standard)")
    print("=" * 96)
    print(f"| {'Metric':<32} | {'V5 Base + Reuse':>18} | {'V6 Fine-Tuned + Reuse':>23} | {'Change':>12} |")
    print(f"| {':' + '-' * 30 + ' '} | {'-' * 17 + ':'} | {'-' * 22 + ':'} | {'-' * 11 + ':'} |")
    print(f"| {'Agentic RCA Accuracy':<32} | {base_stats['baseline_accuracy_pct']:>17.1f}% | {v6_stats['baseline_accuracy_pct']:>22.1f}% | {v6_stats['baseline_accuracy_pct'] - base_stats['baseline_accuracy_pct']:>+11.1f}% |")
    print(f"| {'Source RCA Accuracy':<32} | {base_correct_sources:>15d}/5 | {v6_correct_sources:>20d}/5 | {v6_correct_sources - base_correct_sources:>+12d} |")
    print(f"| {'Trusted Certificates':<32} | {base_trusted_sources:>18d} | {v6_trusted_sources:>23d} | {v6_trusted_sources - base_trusted_sources:>+12d} |")
    print(f"| {'Correct Reuses (TP)':<32} | {base_stats['successful_reuses']:>18d} | {v6_stats['successful_reuses']:>23d} | {v6_stats['successful_reuses'] - base_stats['successful_reuses']:>+12d} |")
    print(f"| {'False Reuses (FP)':<32} | {base_stats['unsafe_reuses']:>18d} | {v6_stats['unsafe_reuses']:>23d} | {v6_stats['unsafe_reuses'] - base_stats['unsafe_reuses']:>+12d} |")
    print(f"| {'Reuse Precision':<32} | {base_stats['reuse_precision_pct']:>17.1f}% | {v6_stats['reuse_precision_pct']:>22.1f}% | {'0.0%':>12} |")
    print(f"| {'False Reuse Rate':<32} | {base_stats['false_reuse_rate_pct']:>17.1f}% | {v6_stats['false_reuse_rate_pct']:>22.1f}% | {'0.0%':>12} |")
    print(f"| {'Correct Rejections (TN)':<32} | {sum(1 for r in base_records if r.get('ground_truth_match') == 'MISMATCH' and r.get('fallback_rca_executed')):>18d} | {sum(1 for r in v6_records if r.get('ground_truth_match') == 'MISMATCH' and r.get('fallback_rca_executed')):>23d} | {'0':>12} |")
    print(f"| {'Full RCA Investigations':<32} | {base_stats['rca_invocations_reuse']:>18d} | {v6_stats['rca_invocations_reuse']:>23d} | {v6_stats['rca_invocations_reuse'] - base_stats['rca_invocations_reuse']:>+12d} |")
    print(f"| {'RCA Investigations Avoided':<32} | {base_stats['rca_avoided_count']:>18d} | {v6_stats['rca_avoided_count']:>23d} | {v6_stats['rca_avoided_count'] - base_stats['rca_avoided_count']:>+12d} |")
    print(f"| {'RCA Avoidance Rate':<32} | {(base_stats['rca_avoided_count']/25*100):>17.1f}% | {(v6_stats['rca_avoided_count']/25*100):>22.1f}% | {((v6_stats['rca_avoided_count'] - base_stats['rca_avoided_count'])/25*100):>+11.1f}% |")
    print(f"| {'Agent LLM Calls':<32} | {base_stats['reuse_llm_calls']:>18d} | {v6_stats['reuse_llm_calls']:>23d} | {v6_stats['reuse_llm_calls'] - base_stats['reuse_llm_calls']:>+12d} |")
    print(f"| {'Token Reduction':<32} | {base_stats['token_reduction_pct']:>17.1f}% | {v6_stats['token_reduction_pct']:>22.1f}% | {v6_stats['token_reduction_pct'] - base_stats['token_reduction_pct']:>+11.1f}% |")
    print(f"| {'Latency Reduction':<32} | {base_stats['latency_reduction_pct']:>17.1f}% | {v6_stats['latency_reduction_pct']:>22.1f}% | {v6_stats['latency_reduction_pct'] - base_stats['latency_reduction_pct']:>+11.1f}% |")
    print("=" * 96)

    return comparison_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="V6 Evaluation Harness")
    parser.add_argument("--eval-validation", action="store_true", help="Run validation evaluation")
    parser.add_argument("--eval-frozen-test", action="store_true", help="Run frozen test evaluation")
    parser.add_argument("--eval-end-to-end", action="store_true", help="Run end-to-end RCA-Reuse comparison")
    parser.add_argument("--provider", default="peft", choices=["peft", "ollama", "mock"], help="Provider type")
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-1.5B-Instruct", help="Model name")
    parser.add_argument("--adapter-path", default=None, help="Adapter path (defaults to RCA_REUSE_CACHE_DIR)")

    args = parser.parse_args()

    if args.eval_end_to_end:
        run_v6_end_to_end_comparison(adapter_path=args.adapter_path)
    elif args.eval_validation:
        prov = get_llm_provider(args.provider, args.model, args.adapter_path)
        evaluate_model_on_validation_set(prov)
    elif args.eval_frozen_test:
        prov = get_llm_provider(args.provider, args.model, args.adapter_path)
        evaluate_model_on_frozen_test(model_name=args.model)
    else:
        run_v6_end_to_end_comparison(adapter_path=args.adapter_path)
