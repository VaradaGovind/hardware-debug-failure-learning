import os
import sys
import json
import argparse
import pandas as pd
from typing import List, Dict, Any

# Ensure repository root is on sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.tools.simulator import VerilogSimulator
from src.agent.llm_provider import LocalOllamaProvider, MockLLMProvider
from src.agent.agentic_rca_backend import AgenticRCABackend, PROMPT_VERSION
from src.evaluation.rca_vs_reuse_harness import RCAReuseEvaluator
from src.evaluation.metrics import compute_rca_vs_reuse_metrics
from experiments.run_rca_vs_reuse_controlled_comparison import get_controlled_comparison_stream


import platform
import subprocess
import datetime


def get_git_info(workspace_root: str) -> Dict[str, str]:
    """Extracts git commit hash and branch name."""
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=workspace_root).decode().strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=workspace_root).decode().strip()
        return {"commit_hash": commit, "branch": branch}
    except Exception:
        return {"commit_hash": "UNKNOWN", "branch": "UNKNOWN"}


def run_experiment(provider_type: str = "ollama",
                   model_name: str = "qwen2.5-coder:1.5b",
                   mode: str = "tool_assisted",
                   max_iterations: int = 4,
                   temperature: float = 0.1,
                   smoke: bool = False) -> Dict[str, Any]:
    """Executes controlled comparison using the Agentic RCA backend."""
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    rtl_dir = os.path.join(workspace_root, "rtl")
    results_dir = os.path.join(workspace_root, "results", "cost_analysis")
    os.makedirs(results_dir, exist_ok=True)
    git_info = get_git_info(workspace_root)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("=" * 88)
    print(f"CONTROLLED EXPERIMENTAL COMPARISON: BASELINE AGENTIC RCA vs. AGENTIC RCA + RCA-REUSE")
    print("=" * 88)
    print(f"Git Commit:      {git_info['commit_hash'][:8]} (branch: {git_info['branch']})")
    print(f"Provider:        {provider_type.upper()}")
    print(f"Model:           {model_name}")
    print(f"Mode:            {mode}")
    print(f"Max Iterations:  {max_iterations}")
    print(f"Temperature:     {temperature}")
    print(f"Smoke Test:      {smoke}")
    print(f"Timestamp:       {timestamp}")
    print("=" * 88)

    # 1. Pre-simulate RTL Targets
    print("\n[STEP 1] Pre-simulating RTL Targets via Icarus Verilog...")
    simulator = VerilogSimulator(rtl_dir)
    stream = get_controlled_comparison_stream()
    if smoke:
        stream = stream[:5]  # 1 source + 4 targets

    for item in stream:
        simulator.run_simulation(item["target_id"], item["design_family"])
    print(f"  Pre-simulation verified: {len(stream)}/{len(stream)} targets compiled and traced.")

    # 2. Instantiate LLM Provider and Agentic RCA Backend
    print("\n[STEP 2] Initializing Agentic RCA Backend & Evaluator...")
    if provider_type == "ollama":
        provider = LocalOllamaProvider(model_name=model_name)
    else:
        provider = MockLLMProvider(default_signal="count")

    backend = AgenticRCABackend(
        provider=provider,
        mode=mode,
        max_iterations=max_iterations,
        temperature=temperature,
        workspace_root=workspace_root
    )

    evaluator = RCAReuseEvaluator(
        backend=backend,
        rtl_dir=rtl_dir
    )

    # 3. Execute Paired Stream Evaluation
    print(f"\n[STEP 3] Executing Paired Evaluation on {len(stream)} Failure Manifestations...")
    eval_res = evaluator.evaluate_stream(stream)
    record_dicts = eval_res["records"]

    # 4. Compute Statistical Metrics
    stats = compute_rca_vs_reuse_metrics(record_dicts)

    # 5. Save Artifacts with Experiment Lock Metadata
    json_path = os.path.join(results_dir, "agentic_rca_vs_reuse_controlled_comparison.json")
    csv_path = os.path.join(results_dir, "agentic_rca_vs_reuse_controlled_comparison.csv")

    output_payload = {
        "experiment_lock": {
            "git_commit": git_info["commit_hash"],
            "git_branch": git_info["branch"],
            "timestamp": timestamp,
            "os_platform": platform.platform(),
            "python_version": platform.python_version(),
            "provider": provider_type,
            "model_name": model_name,
            "mode": mode,
            "max_iterations": max_iterations,
            "temperature": temperature,
            "prompt_version": PROMPT_VERSION,
            "smoke": smoke,
            "dataset_identifier": "hardware_rca_paired_stream_v1_25cases"
        },
        "metrics_summary": stats,
        "records": record_dicts
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    df = pd.DataFrame(record_dicts)
    df.to_csv(csv_path, index=False)

    print(f"  Results written to:\n    {json_path}\n    {csv_path}")

    # 6. Print Formatted Section 25 Table
    n = stats["total_manifestations"]
    base_corr = stats["baseline_correct_count"]
    reuse_corr = stats["reuse_pipeline_correct_count"]
    base_inv = stats["rca_invocations_baseline"]
    reuse_inv = stats["rca_invocations_reuse"]
    avoided_inv = stats["rca_avoided_count"]
    avoid_rate = (avoided_inv / base_inv * 100.0) if base_inv > 0 else 0.0
    
    base_calls = stats["baseline_llm_calls"]
    reuse_calls = stats["reuse_llm_calls"]
    diff_calls = base_calls - reuse_calls
    
    base_tools = stats["baseline_total_ops"]
    reuse_tools = stats["reuse_total_ops"]
    diff_tools = base_tools - reuse_tools
    
    base_lat = stats["baseline_wall_ms"]
    reuse_lat = stats["reuse_wall_ms"]
    diff_lat = base_lat - reuse_lat
    
    base_avg_lat = base_lat / n if n > 0 else 0.0
    reuse_avg_lat = reuse_lat / n if n > 0 else 0.0
    diff_avg_lat = base_avg_lat - reuse_avg_lat

    corr_reuses = stats["successful_reuses"]
    false_reuses = stats["unsafe_reuses"]
    reuse_prec = stats["reuse_precision_pct"]
    corr_rejections = int(sum(1 for r in record_dicts if r.get("ground_truth_match") == "MISMATCH" and r.get("fallback_rca_executed", False)))
    missed_reuses = int(sum(1 for r in record_dicts if r.get("ground_truth_match") == "MATCH" and not r.get("is_source_manifestation", False) and r.get("fallback_rca_executed", False)))

    print("\n" + "=" * 90)
    print("SCIENTIFIC CONTROLLED COMPARISON TABLE (Section 25 Standard)")
    print("=" * 90)
    print(f"| {'Metric':<28} | {'Agentic RCA':>18} | {'Agentic RCA + RCA-Reuse':>25} | {'Difference':>16} |")
    print(f"| {':' + '-' * 26 + ' '} | {'-' * 17 + ':'} | {'-' * 24 + ':'} | {'-' * 15 + ':'} |")
    print(f"| {'Total Failures':<28} | {n:>18d} | {n:>25d} | {'0':>16} |")
    print(f"| {'Correct Diagnoses':<28} | {base_corr:>18d} | {reuse_corr:>25d} | {reuse_corr - base_corr:>+16d} |")
    print(f"| {'Diagnostic Correctness':<28} | {stats['baseline_accuracy_pct']:>17.1f}% | {stats['reuse_pipeline_accuracy_pct']:>24.1f}% | {stats['reuse_pipeline_accuracy_pct'] - stats['baseline_accuracy_pct']:>+15.1f}% |")
    print(f"| {'Full RCA Investigations':<28} | {base_inv:>18d} | {reuse_inv:>25d} | {-avoided_inv:>+16d} |")
    print(f"| {'RCA Investigations Avoided':<28} | {'N/A':>18} | {avoided_inv:>25d} | {avoided_inv:>+16d} |")
    print(f"| {'RCA Avoidance Rate':<28} | {'0.0%':>18} | {avoid_rate:>24.1f}% | {avoid_rate:>+15.1f}% |")
    print(f"| {'Agent Calls':<28} | {base_calls:>18d} | {reuse_calls:>25d} | {-diff_calls:>+16d} |")
    print(f"| {'Tool Calls':<28} | {base_tools:>18d} | {reuse_tools:>25d} | {diff_tools:>+16d} |")
    print(f"| {'Total Latency':<28} | {base_lat:>15.1f} ms | {reuse_lat:>22.1f} ms | {-diff_lat:>+13.1f} ms |")
    print(f"| {'Average Latency':<28} | {base_avg_lat:>15.1f} ms | {reuse_avg_lat:>22.1f} ms | {-diff_avg_lat:>+13.1f} ms |")
    print(f"| {'Correct Reuses':<28} | {'N/A':>18} | {corr_reuses:>25d} | {corr_reuses:>+16d} |")
    print(f"| {'False Reuses':<28} | {'N/A':>18} | {false_reuses:>25d} | {false_reuses:>+16d} |")
    print(f"| {'Reuse Precision':<28} | {'N/A':>18} | {reuse_prec:>24.1f}% | {'N/A':>16} |")
    print(f"| {'Correct Rejections':<28} | {'N/A':>18} | {corr_rejections:>25d} | {corr_rejections:>+16d} |")
    print(f"| {'Missed Reuses':<28} | {'N/A':>18} | {missed_reuses:>25d} | {missed_reuses:>+16d} |")
    print("=" * 90)

    return output_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run controlled comparison: Baseline Agentic RCA vs. Agentic RCA + RCA-Reuse.")
    parser.add_argument("--provider", choices=["ollama", "mock"], default="ollama", help="LLM provider")
    parser.add_argument("--model", default="qwen2.5-coder:1.5b", help="Model name")
    parser.add_argument("--mode", choices=["direct", "tool_assisted"], default="tool_assisted", help="Agent mode")
    parser.add_argument("--max-iterations", type=int, default=4, help="Max agent tool iterations")
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--smoke", action="store_true", help="Run 5-case smoke test")

    args = parser.parse_args()
    run_experiment(
        provider_type=args.provider,
        model_name=args.model,
        mode=args.mode,
        max_iterations=args.max_iterations,
        temperature=args.temperature,
        smoke=args.smoke
    )
