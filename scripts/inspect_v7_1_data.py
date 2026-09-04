import json
import os

with open("results/cost_analysis/v7_end_to_end_comparison.json", "r", encoding="utf-8") as f:
    data = json.load(f)

v6_map = {r["target_id"]: r for r in data["v6_records"]}
v7_map = {r["target_id"]: r for r in data["v7_records"]}

print("=" * 80)
print("ALL 20 TARGET CASES: REUSE STATUS COMPARISON")
print("=" * 80)

for r in data["v7_records"]:
    if r.get("is_source_manifestation"):
        continue
    tid = r["target_id"]
    fam = r["design_family"]
    gt = r["ground_truth_signal"]
    gt_match = r["ground_truth_match"]
    v6_r = v6_map[tid]
    v7_r = r

    v6_reused = v6_r["reused_prior_rca"]
    v6_corr = v6_r["final_reuse_correct"]
    v6_act = v6_r["reuse_policy_action"]
    v6_dec = v6_r["reuse_validation_decision"]

    v7_reused = v7_r["reused_prior_rca"]
    v7_corr = v7_r["final_reuse_correct"]
    v7_act = v7_r["reuse_policy_action"]
    v7_dec = v7_r["reuse_validation_decision"]

    print(f"{tid:<16} | Fam: {fam:<8} | GT: {gt:<10} | GT Match: {gt_match:<7}")
    print(f"   V6: Reused={v6_reused} (Corr={v6_corr}) Act={v6_act} Dec={v6_dec} Diag={v6_r['final_reuse_diagnosis']}")
    print(f"   V7: Reused={v7_reused} (Corr={v7_corr}) Act={v7_act} Dec={v7_dec} Diag={v7_r['final_reuse_diagnosis']}")
