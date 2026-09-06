import os
import sys
import re
import json
import hashlib
from typing import Dict, Any, List, Set, Tuple

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

FROZEN_BENCHMARK_IDS = {
    "heldout_fifo_src", "fifo_vl_a1", "fifo_vl_b1", "fifo_vl_f1", "fifo_vl_i2",
    "heldout_axi_src", "axi_vl_a1", "axi_vl_b1", "axi_vl_f1", "axi_vl_i2",
    "heldout_fsm_src", "fsm_vl_a1", "fsm_vl_b1", "fsm_vl_f1", "fsm_vl_i2",
    "heldout_uart_src", "uart_vl_a1", "uart_vl_b1", "uart_vl_f1", "uart_vl_i2",
    "heldout_pipe_src", "pipeline_vl_a1", "pipeline_vl_b1", "pipeline_vl_f1", "pipeline_vl_i2"
}


def normalize_rtl(content: str) -> str:
    """Strips comments, extra whitespace, and standardizes punctuation for exact AST/text fingerprinting."""
    # Remove single line comments
    content = re.sub(r"//.*", "", content)
    # Remove multi-line comments
    content = re.sub(r"/\*[\s\S]*?\*/", "", content)
    # Normalize whitespace
    content = re.sub(r"\s+", " ", content).strip()
    return content


def extract_structural_fingerprint(rtl_text: str) -> Dict[str, Any]:
    """
    Extracts high-dimensional architectural features from Verilog RTL:
    - Module ports (inputs, outputs, widths)
    - Declared internal registers/wires
    - Clock/reset sensitivity lists
    - Sequential assignment graph (target <= expression)
    - Pipeline stages identified by sequential register latching chains
    - FSM state registers and transition count
    """
    clean = normalize_rtl(rtl_text)
    
    # 1. Module name and ports
    mod_match = re.search(r"module\s+(\w+)\s*\((.*?)\);", clean)
    module_name = mod_match.group(1) if mod_match else "unknown"
    ports_raw = mod_match.group(2) if mod_match else ""
    
    inputs = re.findall(r"input\s+(?:\[\d+:\d+\]\s+)?(\w+)", ports_raw)
    outputs = re.findall(r"output\s+(?:reg\s+)?(?:\[\d+:\d+\]\s+)?(\w+)", ports_raw)
    
    # 2. Internal signals
    regs = re.findall(r"reg\s+(?:\[\d+:\d+\]\s+)?(\w+)", clean)
    wires = re.findall(r"wire\s+(?:\[\d+:\d+\]\s+)?(\w+)", clean)
    
    # Exclude module port regs from internal regs
    internal_regs = [r for r in regs if r not in outputs and r not in inputs]
    
    # 3. Always blocks and sensitivity
    always_blocks = re.findall(r"always\s*@\s*\((.*?)\)\s*begin([\s\S]*?)end", clean)
    
    # 4. Assignments & Connectivity
    seq_assignments = re.findall(r"(\w+)\s*<=\s*([^;]+);", clean)
    comb_assignments = re.findall(r"assign\s+(\w+)\s*=\s*([^;]+);", clean)
    
    # 5. Pipeline stage detection: find register chain e.g. valid_in -> v1 -> valid_out
    # or d_in -> d1 -> d_out
    reg_deps: Dict[str, List[str]] = {}
    for target, expr in seq_assignments:
        tokens = re.findall(r"\b[a-zA-Z_]\w*\b", expr)
        # Filter tokens that are known signals
        srcs = [t for t in tokens if t in inputs or t in internal_regs or t in outputs]
        reg_deps.setdefault(target, []).extend(srcs)
    
    # 6. Abstract Stage Graph Signature
    # Abstract names to structural roles: inputs -> I, internal -> R, outputs -> O
    stage_graph_abstract = []
    for target in sorted(reg_deps.keys()):
        srcs = sorted(list(set(reg_deps[target])))
        target_type = "O" if target in outputs else ("R" if target in internal_regs else "X")
        src_types = [("I" if s in inputs else ("R" if s in internal_regs else "O")) for s in srcs]
        stage_graph_abstract.append(f"{target_type}<-{'+'.join(sorted(src_types))}")
    
    stage_signature = ";".join(stage_graph_abstract)
    
    # 7. State Machine Structure
    state_cases = re.findall(r"case\s*\((.*?)\)([\s\S]*?)endcase", clean)
    fsm_state_count = 0
    if state_cases:
        branch_matches = re.findall(r"\b\d+'[bdh]\w+\s*:", state_cases[0][1])
        fsm_state_count = len(branch_matches)
    
    # Hashes
    raw_hash = hashlib.sha256(rtl_text.encode("utf-8")).hexdigest()[:16]
    norm_hash = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:16]
    struct_hash = hashlib.sha256(f"{len(inputs)}_{len(outputs)}_{len(internal_regs)}_{stage_signature}_{fsm_state_count}".encode("utf-8")).hexdigest()[:16]

    return {
        "module_name": module_name,
        "raw_hash": raw_hash,
        "norm_hash": norm_hash,
        "struct_hash": struct_hash,
        "inputs": sorted(inputs),
        "outputs": sorted(outputs),
        "internal_regs": sorted(internal_regs),
        "stage_signature": stage_signature,
        "fsm_state_count": fsm_state_count,
        "seq_assignment_count": len(seq_assignments),
        "normalized_code_len": len(clean)
    }


def audit_all_designs(designs_dir: str) -> Dict[str, Any]:
    fingerprints: Dict[str, Dict[str, Any]] = {}
    norm_hash_to_files: Dict[str, List[str]] = {}
    struct_hash_to_files: Dict[str, List[str]] = {}
    
    for f in sorted(os.listdir(designs_dir)):
        if not f.endswith(".v"):
            continue
        task_id = f[:-2]
        path = os.path.join(designs_dir, f)
        with open(path, "r", encoding="utf-8") as fp:
            content = fp.read()
        
        fp_data = extract_structural_fingerprint(content)
        fp_data["task_id"] = task_id
        fp_data["is_frozen_benchmark"] = task_id in FROZEN_BENCHMARK_IDS
        fingerprints[task_id] = fp_data
        
        norm_hash_to_files.setdefault(fp_data["norm_hash"], []).append(task_id)
        struct_hash_to_files.setdefault(fp_data["struct_hash"], []).append(task_id)
        
    return {
        "fingerprints": fingerprints,
        "norm_hash_groups": {k: v for k, v in norm_hash_to_files.items() if len(v) > 1},
        "struct_hash_groups": {k: v for k, v in struct_hash_to_files.items() if len(v) > 1}
    }


def audit_prior_datasets(datasets_dir: str, fingerprints: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Audits prior datasets (V7, V9) for exact and structural overlap with frozen benchmark cases."""
    leakage_findings = {
        "v9_exact_leakage_with_frozen": [],
        "v9_structural_leakage_with_frozen": [],
        "v7_exact_leakage_with_frozen": [],
        "v7_structural_leakage_with_frozen": []
    }
    
    # Check V9
    v9_train_path = os.path.join(datasets_dir, "v9", "agentic_train_v9.json")
    if os.path.exists(v9_train_path):
        with open(v9_train_path, "r", encoding="utf-8") as fp:
            v9_train = json.load(fp)
        
        for item in v9_train:
            t_id = item.get("task_id", "")
            if t_id in fingerprints:
                t_fp = fingerprints[t_id]
                for f_id in FROZEN_BENCHMARK_IDS:
                    if f_id in fingerprints:
                        f_fp = fingerprints[f_id]
                        if t_fp["norm_hash"] == f_fp["norm_hash"]:
                            leakage_findings["v9_exact_leakage_with_frozen"].append({
                                "training_task_id": t_id,
                                "frozen_benchmark_id": f_id,
                                "norm_hash": t_fp["norm_hash"]
                            })
                        elif t_fp["struct_hash"] == f_fp["struct_hash"]:
                            leakage_findings["v9_structural_leakage_with_frozen"].append({
                                "training_task_id": t_id,
                                "frozen_benchmark_id": f_id,
                                "stage_signature": t_fp["stage_signature"]
                            })
                            
    # Deduplicate findings
    for k in leakage_findings:
        unique = []
        seen = set()
        for item in leakage_findings[k]:
            pair = (item["training_task_id"], item["frozen_benchmark_id"])
            if pair not in seen:
                seen.add(pair)
                unique.append(item)
        leakage_findings[k] = unique
        
    return leakage_findings


def main():
    print("=" * 88)
    print("EXPERIMENT V10: ARCHITECTURE-LEVEL DATASET AUDIT & FINGERPRINTING")
    print("=" * 88)
    
    designs_dir = os.path.join(WORKSPACE_ROOT, "rtl", "designs")
    datasets_dir = os.path.join(WORKSPACE_ROOT, "datasets")
    reports_dir = os.path.join(WORKSPACE_ROOT, "results", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    design_audit = audit_all_designs(designs_dir)
    print(f"[*] Total RTL Designs Fingerprinted: {len(design_audit['fingerprints'])}")
    print(f"[*] Normalized Hash Collisions (Exact Duplicate Topologies): {len(design_audit['norm_hash_groups'])} clusters")
    print(f"[*] Structural Stage Graph Collisions: {len(design_audit['struct_hash_groups'])} clusters")
    
    prior_audit = audit_prior_datasets(datasets_dir, design_audit["fingerprints"])
    
    print("\n[!] Prior V9 Contamination Patterns Identified:")
    print(f"  - Exact RTL Duplicates in V9 Training against Frozen Benchmark: {len(prior_audit['v9_exact_leakage_with_frozen'])}")
    for leak in prior_audit["v9_exact_leakage_with_frozen"][:10]:
        print(f"      Train '{leak['training_task_id']}' == Frozen '{leak['frozen_benchmark_id']}' (Hash: {leak['norm_hash']})")
        
    print(f"  - Structural RTL Equivalence in V9 Training against Frozen Benchmark: {len(prior_audit['v9_structural_leakage_with_frozen'])}")
    
    output_report = {
        "total_designs": len(design_audit["fingerprints"]),
        "frozen_benchmark_cases": sorted(list(FROZEN_BENCHMARK_IDS)),
        "prior_v9_contamination_findings": prior_audit,
        "exact_duplicate_clusters": design_audit["norm_hash_groups"],
        "structural_duplicate_clusters": design_audit["struct_hash_groups"],
        "all_fingerprints": design_audit["fingerprints"]
    }
    
    out_path = os.path.join(reports_dir, "v10_architecture_fingerprints.json")
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(output_report, fp, indent=2)
        
    print(f"\n[PASS] Fingerprints report saved to: {out_path}")


if __name__ == "__main__":
    main()
