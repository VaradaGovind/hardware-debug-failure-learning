import json

with open("results/cost_analysis/v7_end_to_end_comparison.json", "r", encoding="utf-8") as f:
    data = json.load(f)

v6_map = {r["target_id"]: r for r in data["v6_records"]}
v7_map = {r["target_id"]: r for r in data["v7_records"]}

src_ids = [r["target_id"] for r in data["v7_records"] if r.get("is_source_manifestation")]

print("SOURCE CASES DETAILED COMPARISON:")
for sid in src_ids:
    v6_r = v6_map[sid]
    v7_r = v7_map[sid]
    print("=" * 60)
    print(f"Source: {sid} | Family: {v7_r['design_family']} | GT: {v7_r['ground_truth_signal']}")
    print(f"  V6 Baseline: diag={v6_r['baseline_diagnosis']} (corr={v6_r['baseline_correct']}) status={v6_r.get('baseline_rca_status')}")
    print(f"  V6 Reuse Source RCA: diag={v6_r['final_reuse_diagnosis']} (corr={v6_r['final_reuse_correct']}) status={v6_r.get('final_reuse_rca_status')}")
    print(f"  V6 Source Trusted: {v6_r.get('source_certificate_trusted')} | Reason: {v6_r.get('source_verification_reason')}")
    print(f"  V7 Baseline: diag={v7_r['baseline_diagnosis']} (corr={v7_r['baseline_correct']}) status={v7_r.get('baseline_rca_status')}")
    print(f"  V7 Reuse Source RCA: diag={v7_r['final_reuse_diagnosis']} (corr={v7_r['final_reuse_correct']}) status={v7_r.get('final_reuse_rca_status')}")
    print(f"  V7 Source Trusted: {v7_r.get('source_certificate_trusted')} | Reason: {v7_r.get('source_verification_reason')}")
