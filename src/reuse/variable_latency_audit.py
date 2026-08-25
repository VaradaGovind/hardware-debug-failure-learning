import os
import sys
import json
import hashlib
import pandas as pd
from typing import Dict, Any, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.tools.simulator import VerilogSimulator

def audit_benchmark_integrity(base_dir: str, benchmark_json_path: str) -> Dict[str, Any]:
    with open(benchmark_json_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    rtl_dir = os.path.join(base_dir, "rtl")
    designs_dir = os.path.join(rtl_dir, "designs")
    tb_dir = os.path.join(rtl_dir, "testbenches")
    sim = VerilogSimulator(rtl_dir=rtl_dir)
    
    records = []
    compilation_failures = 0
    missing_vcds = 0
    empty_vcds = 0
    variable_latency_violations = 0

    print("=" * 88)
    print("PHASE 4.3 BENCHMARK PRE-SIMULATION & INTEGRITY AUDIT GATE")
    print("=" * 88)

    for case in cases:
        t_id = case["target_id"]
        tx_class = case.get("transaction_class", "")
        exp_len = case.get("expected_tx_length", 4)
        
        design_path = os.path.join(designs_dir, f"{t_id}.v")
        tb_path = os.path.join(tb_dir, f"{t_id}_tb.v")
        vcd_path = os.path.join(rtl_dir, f"{t_id}.vcd")

        if os.path.exists(vcd_path):
            try:
                os.remove(vcd_path)
            except Exception:
                pass

        res = sim.run_simulation(t_id, case["design"])
        compiled = res.get("compiled", False)
        vcd_path = os.path.join(rtl_dir, f"{t_id}.vcd")
        vcd_exists = os.path.exists(vcd_path)
        
        if not compiled:
            compilation_failures += 1
            status = "COMPILATION_ERROR"
            vcd_size = 0
        else:
            if not vcd_exists:
                missing_vcds += 1
                status = "MISSING_VCD"
                vcd_size = 0
            else:
                vcd_size = os.path.getsize(vcd_path)
                if vcd_size < 100:
                    empty_vcds += 1
                    status = "EMPTY_VCD"
                else:
                    if tx_class in ["CLASS_B_DELAYED", "CLASS_C_MULTI_BEAT", "CLASS_D_STALL_BACKPRESSURE"] and exp_len <= 4:
                        variable_latency_violations += 1
                        status = "LATENCY_THRESHOLD_VIOLATION"
                    else:
                        status = "VALID"

        records.append({
            "target_id": t_id,
            "design": case["design"],
            "transaction_class": tx_class,
            "expected_tx_length": exp_len,
            "compiled": compiled,
            "simulation_success": vcd_exists,
            "vcd_exists": vcd_exists,
            "vcd_size_bytes": vcd_size,
            "integrity_status": status
        })

    df_manifest = pd.DataFrame(records)
    total_cases = len(cases)
    valid_count = (df_manifest["integrity_status"] == "VALID").sum()

    print(f"Total Targets Evaluated:          {total_cases}")
    print(f"Compilation Errors:               {compilation_failures}")
    print(f"Missing VCDs:                     {missing_vcds}")
    print(f"Empty/Corrupt VCDs:               {empty_vcds}")
    print(f"Variable-Latency Violations:      {variable_latency_violations}")
    print(f"100% Valid & Executable Targets:  {valid_count}/{total_cases}")

    all_clean = (compilation_failures == 0 and missing_vcds == 0 and empty_vcds == 0 and variable_latency_violations == 0)
    
    audit_summary = {
        "total_targets": total_cases,
        "valid_targets": int(valid_count),
        "compilation_failures": compilation_failures,
        "missing_vcds": missing_vcds,
        "empty_vcds": empty_vcds,
        "variable_latency_violations": variable_latency_violations,
        "gate_passed": all_clean,
        "manifest_records": records
    }

    manifest_out = os.path.join(base_dir, "results", "transaction_semantic_certs", "variable_latency_stress", "benchmark", "benchmark_integrity_manifest.json")
    with open(manifest_out, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)

    print(f"Integrity manifest saved to: {manifest_out}")
    if not all_clean:
        raise RuntimeError(f"BENCHMARK INTEGRITY GATE FAILED: {compilation_failures} compilation errors, {missing_vcds} missing VCDs.")
    print("BENCHMARK INTEGRITY GATE: PASSED (0 Errors)")
    print("=" * 88)
    return audit_summary

if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bm_json = os.path.join(base, "results", "transaction_semantic_certs", "variable_latency_stress", "benchmark", "heldout_ground_truth.json")
    audit_benchmark_integrity(base, bm_json)
