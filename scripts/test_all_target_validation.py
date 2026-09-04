import os
import sys
import json

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, WORKSPACE_ROOT)

from src.reuse.certificate_store import CertificateStore
from src.reuse.transaction_certificate_extractor import TransactionCertificateExtractor
from src.tools.simulator import VerilogSimulator
from experiments.run_rca_vs_reuse_controlled_comparison import get_controlled_comparison_stream

rtl_dir = os.path.join(WORKSPACE_ROOT, "rtl")
sim = VerilogSimulator(rtl_dir)

stream = get_controlled_comparison_stream()

# Pre-simulate all targets
for s in stream:
    sim.run_simulation(s["target_id"], s["design_family"])

extractor = TransactionCertificateExtractor()

# We will run for each family
families = ["fifo", "axi", "fsm", "uart", "pipeline"]

gt_root_causes = {
    "fifo": "count",
    "axi": "valid_out",
    "fsm": "state",
    "uart": "cnt",
    "pipeline": "v1"
}

results = {}

for fam in families:
    fam_items = [s for s in stream if s["design_family"] == fam]
    src_item = fam_items[0]
    target_items = fam_items[1:]

    spec_override = {"obl_type": "STALL_DRAINAGE_PRESERVATION"} if fam == "pipeline" else None
    cert = extractor.extract_from_rca(
        src_item["target_id"], src_item["design_family"],
        {"defect_desc": f"{src_item['defect_mechanism']} defect", "observed_symptom": src_item["symptom"]},
        src_item["target_signals"],
        spec_override=spec_override
    )
    cert.metadata["design_family"] = src_item["design_family"]
    cert.metadata["symptom"] = src_item["symptom"]
    cert.metadata["root_cause_signal"] = gt_root_causes[fam]
    cert.metadata["is_trusted"] = True

    store = CertificateStore()
    store.register(cert)

    fam_res = []
    for t in target_items:
        tid = t["target_id"]
        vcd_path = os.path.join(rtl_dir, f"{tid}.vcd")
        candidates = store.query_candidates(design_family=fam, symptom=t["symptom"], observed_signals=t["target_signals"], only_trusted=True)
        if not candidates:
            fam_res.append({
                "target_id": tid,
                "ground_truth_match": t["ground_truth_match"],
                "candidate_found": False,
                "decision": "NO_CANDIDATES",
                "policy": "FALLBACK",
                "reason": "Candidate query returned 0 matches"
            })
            continue
        cand_cert = candidates[0][1]
        report = store.validate_and_decide(cand_cert, vcd_path, target_id=tid)
        fam_res.append({
            "target_id": tid,
            "ground_truth_match": t["ground_truth_match"],
            "candidate_found": True,
            "decision": report.raw_validator_decision,
            "policy": report.policy_action,
            "reason": report.decision_reason,
            "suff_state": report.sufficiency_state
        })
    results[fam] = fam_res

print(json.dumps(results, indent=2))
