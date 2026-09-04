import os
import sys
import json
import hashlib
from collections import Counter, defaultdict

CACHE_DIR = os.environ.get("RCA_REUSE_CACHE_DIR", os.path.expanduser("~/.cache/rca-reuse"))
TRAIN_PATH = os.path.join(CACHE_DIR, "v7", "datasets", "rca_train_v7.json")
VAL_PATH = os.path.join(CACHE_DIR, "v7", "datasets", "rca_val_v7.json")

def audit_dataset():
    with open(TRAIN_PATH, "r", encoding="utf-8") as f:
        train_data = json.load(f)
    with open(VAL_PATH, "r", encoding="utf-8") as f:
        val_data = json.load(f)

    all_data = train_data + val_data
    total_samples = len(all_data)

    print("=" * 96)
    print(f"V7 CANONICAL DATASET SCIENTIFIC AUDIT REPORT (Total Samples: {total_samples})")
    print("=" * 96)

    # 1. Split Counts
    print(f"\n1. SPLIT COUNTS:")
    print(f"   - Train Split:      {len(train_data):>4d} ({len(train_data)/total_samples*100:.1f}%)")
    print(f"   - Validation Split: {len(val_data):>4d} ({len(val_data)/total_samples*100:.1f}%)")

    # 2. Category / Source Dataset Breakdown
    src_counts = Counter(e.get("source_dataset", "UNKNOWN") for e in all_data)
    train_srcs = Counter(e.get("source_dataset", "UNKNOWN") for e in train_data)
    val_srcs = Counter(e.get("source_dataset", "UNKNOWN") for e in val_data)

    print(f"\n2. DATASET ORIGIN / SOURCE BREAKDOWN:")
    for src in sorted(src_counts.keys()):
        tot = src_counts[src]
        tr = train_srcs.get(src, 0)
        vl = val_srcs.get(src, 0)
        print(f"   - {src:<42}: Total = {tot:>4d} ({tot/total_samples*100:>5.1f}%) | Train = {tr:>4d} | Val = {vl:>4d}")

    # Category Mapping (A, B, C, D)
    def map_category(e):
        src = e.get("source_dataset", "")
        etype = e.get("example_type", "")
        if "pr_pattern" in src:
            return "Category A: Real/Open PR Bugs"
        elif etype == "HARD_NEGATIVE":
            return "Category C: Hard Negatives"
        elif etype == "UNKNOWN_INSUFFICIENT":
            return "Category D: UNKNOWN Controls"
        else:
            return "Category B: Simulation-Backed Synth"

    cat_counts = Counter(map_category(e) for e in all_data)
    train_cats = Counter(map_category(e) for e in train_data)
    val_cats = Counter(map_category(e) for e in val_data)

    print(f"\n3. METHODOLOGICAL 4-TIER CATEGORY BREAKDOWN:")
    for cat in sorted(cat_counts.keys()):
        tot = cat_counts[cat]
        tr = train_cats.get(cat, 0)
        vl = val_cats.get(cat, 0)
        print(f"   - {cat:<36}: Total = {tot:>4d} ({tot/total_samples*100:>5.1f}%) | Train = {tr:>4d} | Val = {vl:>4d}")

    # 4. Hardware Design Family Breakdown
    fam_counts = Counter(e.get("design_family", "UNKNOWN") for e in all_data)
    train_fams = Counter(e.get("design_family", "UNKNOWN") for e in train_data)
    val_fams = Counter(e.get("design_family", "UNKNOWN") for e in val_data)

    print(f"\n4. HARDWARE DESIGN FAMILY BREAKDOWN:")
    for fam in sorted(fam_counts.keys()):
        tot = fam_counts[fam]
        tr = train_fams.get(fam, 0)
        vl = val_fams.get(fam, 0)
        print(f"   - {fam:<16}: Total = {tot:>4d} ({tot/total_samples*100:>5.1f}%) | Train = {tr:>4d} | Val = {vl:>4d}")

    # 5. Example Type Breakdown
    type_counts = Counter(e.get("example_type", "UNKNOWN") for e in all_data)
    print(f"\n5. EXAMPLE TYPE BREAKDOWN:")
    for etype in sorted(type_counts.keys()):
        tot = type_counts[etype]
        print(f"   - {etype:<24}: Total = {tot:>4d} ({tot/total_samples*100:>5.1f}%)")

    # 6. Provenance Breakdown
    prov_counts = Counter(e.get("provenance", "UNKNOWN") for e in all_data)
    print(f"\n6. PROVENANCE BREAKDOWN:")
    for prov in sorted(prov_counts.keys()):
        tot = prov_counts[prov]
        print(f"   - {prov:<32}: Total = {tot:>4d} ({tot/total_samples*100:>5.1f}%)")

    # 7. Unique Underlying RTL Designs / Contexts
    # Hash normalized RTL context to find exact unique RTL architectures
    def hash_rtl(rtl_text):
        norm = "".join(rtl_text.split()).lower()
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]

    all_rtl_hashes = set(hash_rtl(e.get("rtl_context", "")) for e in all_data)
    train_rtl_hashes = set(hash_rtl(e.get("rtl_context", "")) for e in train_data)
    val_rtl_hashes = set(hash_rtl(e.get("rtl_context", "")) for e in val_data)
    shared_rtl_hashes = train_rtl_hashes & val_rtl_hashes

    print(f"\n7. UNIQUE UNDERLYING RTL DESIGNS (Code Architectures):")
    print(f"   - Total Unique RTL Codebases: {len(all_rtl_hashes)}")
    print(f"   - Train RTL Codebases:        {len(train_rtl_hashes)}")
    print(f"   - Val RTL Codebases:          {len(val_rtl_hashes)}")
    print(f"   - Shared RTL Across Splits:   {len(shared_rtl_hashes)} ({len(shared_rtl_hashes)/len(val_rtl_hashes)*100:.1f}% of Val RTLs)")

    # 8. Unique Source Cases / Mutations
    all_source_cases = set(e.get("source_case", "") for e in all_data)
    train_source_cases = set(e.get("source_case", "") for e in train_data)
    val_source_cases = set(e.get("source_case", "") for e in val_data)
    shared_source_cases = train_source_cases & val_source_cases

    print(f"\n8. UNIQUE SOURCE CASES / SEED BUG PATTERNS:")
    print(f"   - Total Unique Source Cases:  {len(all_source_cases)}")
    print(f"   - Train Source Cases:         {len(train_source_cases)}")
    print(f"   - Val Source Cases:           {len(val_source_cases)}")
    print(f"   - Shared Source Cases Overlap: {len(shared_source_cases)} (Expected: 0)")

    # 9. Examples Derived Per Source Case (Multiplicity Distribution)
    case_multiplicity = Counter(e.get("source_case", "") for e in all_data)
    mult_distribution = Counter(case_multiplicity.values())
    print(f"\n9. DERIVATION MULTIPLICITY PER SEED BUG PATTERN:")
    for mult, count in sorted(mult_distribution.items()):
        print(f"   - {mult} samples derived per bug case : {count} unique bug patterns")

    # 10. Hard-Negative Structural Sharing
    pos_cases = set(e.get("source_case", "") for e in all_data if e.get("example_type") == "POSITIVE_RCA")
    hn_cases = set(e.get("source_case", "") for e in all_data if e.get("example_type") == "HARD_NEGATIVE")
    shared_pos_hn_cases = pos_cases & hn_cases

    print(f"\n10. STRUCTURAL SHARING (Hard Negatives vs Positive RCA):")
    print(f"   - Positive RCA Source Cases:   {len(pos_cases)}")
    print(f"   - Hard Negative Source Cases: {len(hn_cases)}")
    print(f"   - Shared Seed Cases:          {len(shared_pos_hn_cases)} ({len(shared_pos_hn_cases)/len(hn_cases)*100:.1f}%)")

    audit_summary = {
        "total_samples": total_samples,
        "train_samples": len(train_data),
        "val_samples": len(val_data),
        "category_counts": dict(cat_counts),
        "family_counts": dict(fam_counts),
        "example_type_counts": dict(type_counts),
        "provenance_counts": dict(prov_counts),
        "unique_rtl_designs": len(all_rtl_hashes),
        "train_rtl_designs": len(train_rtl_hashes),
        "val_rtl_designs": len(val_rtl_hashes),
        "shared_rtl_designs": len(shared_rtl_hashes),
        "unique_source_cases": len(all_source_cases),
        "train_source_cases": len(train_source_cases),
        "val_source_cases": len(val_source_cases),
        "shared_source_cases": len(shared_source_cases),
        "case_multiplicity_distribution": dict(mult_distribution),
        "shared_pos_hn_cases": len(shared_pos_hn_cases)
    }

    os.makedirs("results/reports", exist_ok=True)
    with open("results/reports/v7_dataset_audit_metrics.json", "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)

    print("\nDataset audit metrics saved to: results/reports/v7_dataset_audit_metrics.json")

if __name__ == "__main__":
    audit_dataset()
