import json

with open("results/cost_analysis/v7_end_to_end_comparison.json", "r", encoding="utf-8") as f:
    data = json.load(f)

v7_records = data["v7_records"]
sources = [r for r in v7_records if r.get("is_source_manifestation")]
targets = [r for r in v7_records if not r.get("is_source_manifestation")]

print("Sources:", len(sources))
print("Targets:", len(targets))

for idx, r in enumerate(targets, 1):
    tid = r["target_id"]
    fam = r["design_family"]
    gt = r["ground_truth_signal"]
    gt_match = r["ground_truth_match"]
    reused = r["reused_prior_rca"]
    diag = r["final_reuse_diagnosis"]
    corr = r["final_reuse_correct"]
    val_dec = r["reuse_validation_decision"]
    pol = r["reuse_policy_action"]
    fb_exec = r["fallback_rca_executed"]
    base_diag = r["baseline_diagnosis"]
    base_corr = r["baseline_correct"]
    
    # Check source status for this family
    src_r = [s for s in sources if s["design_family"] == fam][0]
    src_trusted = src_r.get("source_certificate_trusted", False)
    src_corr = src_r.get("baseline_correct", False)
    src_diag = src_r.get("baseline_diagnosis", "unknown")
    src_reuse_diag = src_r.get("final_reuse_diagnosis", "unknown")
    
    print(f"Target {idx:>2}: {tid:<16} | Fam: {fam:<8} | GT: {gt:<10} | GT_Match: {gt_match:<8} | Reused: {reused} | Corr: {corr} | ValDec: {val_dec} | BaseCorr: {base_corr} | SrcTrusted: {src_trusted}")
