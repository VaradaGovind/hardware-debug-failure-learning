import os
import sys
import json

COMPARISON_FILE = r"results\cost_analysis\v7_end_to_end_comparison.json"

def main():
    with open(COMPARISON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    transitions = data["case_level_transitions"]

    wrong_to_correct = [t for t in transitions if t["transition"] == "Wrong -> Correct"]
    correct_to_wrong = [t for t in transitions if t["transition"] in ["Correct -> Wrong", "Unknown -> Wrong"]]
    correct_to_correct = [t for t in transitions if t["transition"] == "Correct -> Correct"]
    wrong_to_wrong = [t for t in transitions if t["transition"] in ["Wrong -> Wrong", "Unknown -> Wrong"]]

    print("=" * 105)
    print(f"FROZEN 25-CASE TRANSITION AUDIT (Total: {len(transitions)} cases)")
    print("=" * 105)
    print(f"  - Wrong -> Correct (Newly Correct):     {len(wrong_to_correct)}")
    print(f"  - Correct -> Correct (Maintained):      {len(correct_to_correct)}")
    print(f"  - Correct -> Wrong (Regressions):       {len(correct_to_wrong)}")
    print(f"  - Wrong -> Wrong (Persistent Errors):   {len(wrong_to_wrong)}")
    print("=" * 105)

    print("\n[A] NEWLY CORRECT CASES (V6 Wrong -> V7 Correct):")
    for t in wrong_to_correct:
        print(f"  * Case {t['case_index']:>2} | {t['target_id']:<18} | Family: {t['design_family']:<8} | GT: {t['ground_truth_signal']:<10} | V6: {t['v6_diagnosis']:<10} -> V7: {t['v7_diagnosis']:<10}")

    print("\n[B] REGRESSION CASES (V6 Correct -> V7 Wrong):")
    for t in correct_to_wrong:
        print(f"  * Case {t['case_index']:>2} | {t['target_id']:<18} | Family: {t['design_family']:<8} | GT: {t['ground_truth_signal']:<10} | V6: {t['v6_diagnosis']:<10} -> V7: {t['v7_diagnosis']:<10}")

    print("\n[C] MAINTAINED CORRECT CASES (V6 Correct -> V7 Correct):")
    for t in correct_to_correct:
        print(f"  * Case {t['case_index']:>2} | {t['target_id']:<18} | Family: {t['design_family']:<8} | GT: {t['ground_truth_signal']:<10} | V6: {t['v6_diagnosis']:<10} -> V7: {t['v7_diagnosis']:<10}")

if __name__ == "__main__":
    main()
