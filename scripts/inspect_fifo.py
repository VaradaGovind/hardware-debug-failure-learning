import json
import os

with open("results/cost_analysis/v7_end_to_end_comparison.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for r in data["v7_records"]:
    if r["target_id"] in ["heldout_fifo_src", "fifo_vl_a1", "fifo_vl_b1"]:
        print("=" * 60)
        print("Target:", r["target_id"])
        for k, v in r.items():
            if "reuse" in k or "decision" in k or "policy" in k or "signal" in k or "match" in k:
                print(f"  {k}: {v}")
