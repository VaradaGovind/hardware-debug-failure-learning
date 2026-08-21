"""Run a small, non-destructive RTL-to-RCA-reuse smoke experiment.

The fixture is copied into a temporary directory before simulation because the
repository testbenches use absolute VCD dump paths.  The expected defective
FIFO testbench prints ``FAIL`` when it reaches the known manifestation; that
is a valid trace for this smoke test, so compilation and VCD creation are
checked separately from the simulator wrapper's log-based ``success`` flag.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.reuse.adaptive_l2_adapter import AdaptiveL2Adapter
from src.reuse.adaptive_reuse_policy import AdaptiveReusePolicy
from src.reuse.causal_certificate import CausalCertificate, CertificateValidator
from src.reuse.transaction_certificate_extractor import TransactionCertificateExtractor
from src.reuse.transaction_semantic_validator import TransactionSemanticValidator
from src.tools.simulator import VerilogSimulator
from src.tools.waveform import WaveformTool


DESIGN = ROOT / "rtl" / "designs" / "fifo_f2.v"
TESTBENCH = ROOT / "rtl" / "testbenches" / "fifo_f2_tb.v"
SOURCE_CERTIFICATE = (
    ROOT / "examples" / "fixtures" / "certificate_fifo_simultaneous_rw.json"
)

SIGNALS = [
    "clk",
    "rst_n",
    "write_en",
    "read_en",
    "count",
    "full",
    "empty",
    "write_ptr",
    "read_ptr",
]


def _copy_fixture(temp_root: Path) -> Path:
    """Copy the design and rewrite only the temporary testbench VCD path."""

    designs = temp_root / "designs"
    testbenches = temp_root / "testbenches"
    designs.mkdir()
    testbenches.mkdir()

    shutil.copy2(DESIGN, designs / DESIGN.name)
    dump_path = (temp_root / "fifo_f2.vcd").as_posix()
    testbench_text = TESTBENCH.read_text(encoding="utf-8")
    replacement = '$dumpfile("' + dump_path + '")'
    rewritten, count = re.subn(
        r'\$dumpfile\(".*?"\)', replacement, testbench_text, count=1
    )
    if count != 1:
        raise RuntimeError(f"Could not rewrite the VCD path in {TESTBENCH}")
    (testbenches / TESTBENCH.name).write_text(rewritten, encoding="utf-8")
    return temp_root / "fifo_f2.vcd"


def main() -> None:
    if not all(path.exists() for path in (DESIGN, TESTBENCH, SOURCE_CERTIFICATE)):
        missing = [
            str(path)
            for path in (DESIGN, TESTBENCH, SOURCE_CERTIFICATE)
            if not path.exists()
        ]
        raise FileNotFoundError(
            "The local smoke fixture is incomplete; missing: " + ", ".join(missing)
        )

    with tempfile.TemporaryDirectory(prefix="rca_reuse_smoke_") as directory:
        temporary_root = Path(directory)
        vcd_path = _copy_fixture(temporary_root)

        simulation = VerilogSimulator(str(temporary_root)).run_simulation(
            "fifo_f2", "fifo"
        )
        compiled_and_traced = bool(simulation.get("compiled")) and vcd_path.exists()
        if not compiled_and_traced:
            raise RuntimeError(
                "The RTL smoke experiment did not produce a compiled design and VCD: "
                + json.dumps(simulation, default=str)
            )

        waveform = WaveformTool().query_waveform(
            str(vcd_path), SIGNALS, start_time=0, end_time=1000
        )
        if not waveform.get("success"):
            raise RuntimeError(f"Waveform extraction failed: {waveform.get('error')}")

        source_certificate = CausalCertificate.from_dict(
            json.loads(SOURCE_CERTIFICATE.read_text(encoding="utf-8"))
        )
        causal = CertificateValidator().validate_certificate(
            source_certificate, str(vcd_path), DESIGN.read_text(encoding="utf-8")
        )

        transaction_certificate = TransactionCertificateExtractor().extract_from_rca(
            "fifo_f2",
            "fifo",
            {
                "defect_desc": "FIFO simultaneous read/write count update defect",
                "observed_symptom": "count increments during simultaneous read/write",
            },
            [
                "count",
                "write_en",
                "read_en",
                "full",
                "empty",
                "write_ptr",
                "read_ptr",
            ],
        )
        semantic = TransactionSemanticValidator().validate(
            transaction_certificate, str(vcd_path)
        )
        adaptive = AdaptiveL2Adapter().validate_adaptive(
            transaction_certificate, str(vcd_path)
        )
        policy = AdaptiveReusePolicy()

        expected_decisions = ("PASS", "PASS", "PASS")
        observed_decisions = (
            causal.get("decision"),
            semantic.get("decision"),
            adaptive.get("decision"),
        )
        if observed_decisions != expected_decisions:
            raise RuntimeError(
                "The known FIFO reuse fixture changed decisions: "
                + repr(observed_decisions)
            )

        output = {
            "fixture": "fifo_f2",
            "simulator_compiled": bool(simulation.get("compiled")),
            "simulation_execution": "PASS" if bool(simulation.get("compiled")) and vcd_path.exists() else "FAIL",
            "simulation_status": "EXPECTED_FAILURE" if "FAIL" in simulation.get("output", "") else "UNEXPECTED",
            "expected_failure_detected": "FAIL" in simulation.get("output", ""),
            "vcd_extracted": bool(waveform.get("success")),
            "waveform_signals": sorted((waveform.get("data") or {}).keys()),
            "causal_decision": causal.get("decision"),
            "transaction_semantic_decision": semantic.get("decision"),
            "adaptive_decision": adaptive.get("decision"),
            "reuse_policy": policy.decide(adaptive),
            "fallback_policy_for_insufficient_evidence": policy.decide(
                "INSUFFICIENT_EVIDENCE"
            ),
            "explanation": (
                "The fixture intentionally contains a failing FIFO scenario. "
                "The simulator executed cleanly and produced the expected failure trace for RCA-Reuse analysis."
            ),
        }
        print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
