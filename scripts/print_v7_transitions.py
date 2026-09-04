import json

with open("results/cost_analysis/v7_end_to_end_comparison.json", "r") as f:
    data = json.load(f)

print("=" * 105)
print(f"{'Case':<5} {'Target ID':<20} {'Family':<10} {'GT Signal':<12} {'V6 Diagnosis':<14} {'V7 Diagnosis':<14} {'Transition':<20}")
print("=" * 105)

transitions = data["case_level_transitions"]
for t in transitions:
    print(f"{t['case_index']:<5} {t['target_id']:<20} {t['design_family']:<10} {t['ground_truth_signal']:<12} {t['v6_diagnosis']:<14} {t['v7_diagnosis']:<14} {t['transition']:<20}")

print("=" * 105)

# Per family breakdown
fam_counts = {}
for t in transitions:
    fam = t["design_family"]
    fam_counts.setdefault(fam, {"total": 0, "v6_correct": 0, "v7_correct": 0})
    fam_counts[fam]["total"] += 1
    if t["v6_correct"]:
        fam_counts[fam]["v6_correct"] += 1
    if t["v7_correct"]:
        fam_counts[fam]["v7_correct"] += 1

print("\nPer-Family Accuracy Comparison on Frozen 25-Case Stream:")
for fam, stats in sorted(fam_counts.items()):
    v6_p = (stats["v6_correct"] / stats["total"]) * 100
    v7_p = (stats["v7_correct"] / stats["total"]) * 100
    print(f"  - {fam:<12}: V6 = {v6_p:>5.1f}% ({stats['v6_correct']}/{stats['total']}) -> V7 = {v7_p:>5.1f}% ({stats['v7_correct']}/{stats['total']}) | Delta: {v7_p - v6_p:>+5.1f}%")
