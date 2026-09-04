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
fifo_items = [s for s in stream if s["design_family"] == "fifo"]

for item in fifo_items:
    sim.run_simulation(item["target_id"], "fifo")

extractor = TransactionCertificateExtractor()
store = CertificateStore()

src_item = fifo_items[0]
cert = extractor.extract_from_rca(
    src_item["target_id"], src_item["design_family"],
    {"defect_desc": f"{src_item['defect_mechanism']} defect", "observed_symptom": src_item["symptom"]},
    src_item["target_signals"]
)
cert.metadata["design_family"] = src_item["design_family"]
cert.metadata["symptom"] = src_item["symptom"]
cert.metadata["root_cause_signal"] = "count"
cert.metadata["is_trusted"] = True

store.register(cert)

for item in fifo_items[1:]:
    tid = item["target_id"]
    vcd_path = os.path.join(rtl_dir, f"{tid}.vcd")
    candidates = store.query_candidates(design_family="fifo", symptom=item["symptom"], observed_signals=item["target_signals"], only_trusted=True)
    if not candidates:
        print(f"Target {tid}: No candidates!")
        continue
    cand_cert = candidates[0][1]
    report = store.validate_and_decide(cand_cert, vcd_path, target_id=tid)
    print(f"Target {tid}: raw={report.raw_validator_decision}, policy={report.policy_action}, reason={report.decision_reason}, suff={report.sufficiency_state}")
