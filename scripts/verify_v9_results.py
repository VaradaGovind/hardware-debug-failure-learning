import os
import sys
import json
from typing import Dict, Any, List

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
v8_path = os.path.join(WORKSPACE_ROOT, "results", "cost_analysis", "v8_end_to_end_comparison.json")
v9_path = os.path.join(WORKSPACE_ROOT, "results", "cost_analysis", "v9_end_to_end_comparison.json")

with open(v8_path, "r", encoding="utf-8") as f:
    v8_data = json.load(f)

with open(v9_path, "r", encoding="utf-8") as f:
    v9_data = json.load(f)

print("V8 Top-level keys:", list(v8_data.keys()))
print("V9 Top-level keys:", list(v9_data.keys()))

v8_recs = v8_data["v8_records"]
v9_recs = v9_data["records"]

print(f"V8 records count: {len(v8_recs)}")
print(f"V9 records count: {len(v9_recs)}")

# Print 25-case side-by-side comparison
print("\n" + "=" * 110)
print(f"{'Idx':<4} | {'Target ID':<18} | {'Fam':<6} | {'GT':<10} | {'V8 Diag':<10} | {'V9 Diag':<10} | {'V8 Cor':<7} | {'V9 Cor':<7} | {'V8 Re':<6} | {'V9 Re':<6} | {'V8 Decision':<18} | {'V9 Decision':<18}")
print("=" * 110)

case_transitions = []

for idx in range(len(v8_recs)):
    r8 = v8_recs[idx]
    r9 = v9_recs[idx]
    
    t_id = r8["target_id"]
    fam = r8["design_family"]
    gt = r8["ground_truth_signal"]
    
    v8_diag = r8.get("final_reuse_diagnosis", "")
    v9_diag = r9.get("final_reuse_diagnosis", "")
    
    v8_cor = r8.get("final_reuse_correct", False)
    v9_cor = r9.get("final_reuse_correct", False)
    
    v8_reused = r8.get("reused_prior_rca", False)
    v9_reused = r9.get("reused_prior_rca", False)
    
    v8_dec = r8.get("reuse_validation_decision", "")
    v9_dec = r9.get("reuse_validation_decision", "")

    # Base diagnoses
    v8_base_diag = r8.get("baseline_diagnosis", "")
    v9_base_diag = r9.get("baseline_diagnosis", "")
    v8_base_cor = r8.get("baseline_correct", False)
    v9_base_cor = r9.get("baseline_correct", False)

    # Classify transition
    diag_trans = ""
    if not v8_cor and v9_cor:
        diag_trans = "wrong -> correct"
    elif v8_cor and not v9_cor:
        diag_trans = "correct -> wrong"
    elif not v8_cor and not v9_cor:
        diag_trans = "wrong -> wrong"
    else:
        diag_trans = "correct -> correct"

    reuse_trans = ""
    if not v8_reused and v9_reused:
        reuse_trans = "no-reuse -> correct-reuse" if v9_cor else "unsafe reuse"
    elif v8_reused and not v9_reused:
        reuse_trans = "correct-reuse -> no-reuse"
    elif v9_reused and not v9_cor:
        reuse_trans = "unsafe reuse"
    elif not v9_reused and r9.get("ground_truth_match") == "MISMATCH":
        reuse_trans = "correct rejection"
    elif v8_reused and v9_reused:
        reuse_trans = "correct-reuse -> correct-reuse"
    else:
        reuse_trans = "no-reuse -> no-reuse"

    entry = {
        "case_index": idx + 1,
        "target_id": t_id,
        "family": fam,
        "ground_truth": gt,
        "is_source": r8.get("is_source_manifestation", False),
        "v8_baseline_diagnosis": v8_base_diag,
        "v9_baseline_diagnosis": v9_base_diag,
        "v8_baseline_correct": v8_base_cor,
        "v9_baseline_correct": v9_base_cor,
        "v8_reuse_diagnosis": v8_diag,
        "v9_reuse_diagnosis": v9_diag,
        "v8_reuse_correct": v8_cor,
        "v9_reuse_correct": v9_cor,
        "v8_reused": v8_reused,
        "v9_reused": v9_reused,
        "v8_decision": v8_dec,
        "v9_decision": v9_dec,
        "v8_rca_status": r8.get("final_reuse_rca_status", ""),
        "v9_rca_status": r9.get("final_reuse_rca_status", ""),
        "v8_source_verification": r8.get("source_verification_status", ""),
        "v9_source_verification": r9.get("source_verification_status", ""),
        "diagnostic_transition": diag_trans,
        "reuse_transition": reuse_trans
    }
    case_transitions.append(entry)

    print(f"{idx+1:<4} | {t_id:<18} | {fam:<6} | {gt:<10} | {v8_diag:<10} | {v9_diag:<10} | {str(v8_cor):<7} | {str(v9_cor):<7} | {str(v8_reused):<6} | {str(v9_reused):<6} | {v8_dec:<18} | {v9_dec:<18}")

# Save verified case transitions
out_path = os.path.join(WORKSPACE_ROOT, "results", "reports", "v9_case_transitions_verified.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(case_transitions, f, indent=2)

print(f"\nSaved verified case transitions to: {out_path}")
