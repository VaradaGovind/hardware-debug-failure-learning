import unittest
import os
import tempfile
from pathlib import Path

from src.reuse.source_rca_verifier import SourceRCAVerifier, SourceVerificationResult
from src.reuse.certificate_store import CertificateStore
from src.reuse.transaction_semantic_certificate import (
    TransactionSemanticCertificate,
    TransactionContext,
    ProtocolObligation
)
from src.tools.simulator import VerilogSimulator


class TestSourceRCAVerifier(unittest.TestCase):
    """
    Unit test suite for the V5 Source RCA Verifier & Certificate Trust Gate.
    """

    def setUp(self):
        self.workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.rtl_dir = os.path.join(self.workspace_root, "rtl")
        self.verifier = SourceRCAVerifier(workspace_root=self.workspace_root)
        self.simulator = VerilogSimulator(self.rtl_dir)

        # Pre-simulate test cases to ensure VCDs exist
        self.simulator.run_simulation("heldout_axi_src", "axi")
        self.simulator.run_simulation("heldout_fifo_src", "fifo")
        self.simulator.run_simulation("heldout_fsm_src", "fsm")
        self.simulator.run_simulation("heldout_uart_src", "uart")
        self.simulator.run_simulation("heldout_pipe_src", "pipeline")

    def test_case_1_correct_candidate_with_strong_evidence(self):
        """
        Test 1: Correct candidate with strong temporal & causal evidence -> VERIFIED.
        In AXI, 'valid_out' drops prematurely while waiting for ready, directly causing assertion failure.
        """
        res = self.verifier.verify(
            task_id="heldout_axi_src",
            design_family="axi",
            candidate_signal="valid_out"
        )
        self.assertEqual(res.status, "VERIFIED")
        self.assertTrue(res.architectural_grounding)
        self.assertTrue(res.temporal_evidence)
        self.assertTrue(res.causal_evidence)
        self.assertTrue(res.confidence > 0.8)

    def test_case_2_passive_input_stimulus_rejection(self):
        """
        Test 2: Passive testbench input signal ('start' in FSM or 'valid_in' in Pipeline)
        with no internal assignment defect -> REJECTED.
        """
        res = self.verifier.verify(
            task_id="heldout_fsm_src",
            design_family="fsm",
            candidate_signal="start"
        )
        self.assertEqual(res.status, "REJECTED")
        self.assertTrue(res.architectural_grounding)
        self.assertFalse(res.is_assigned_in_rtl)
        self.assertFalse(res.causal_evidence)
        self.assertIn("passive testbench input", res.explanation.lower())

    def test_case_3_unknown_or_nonexistent_signal(self):
        """
        Test 3: Non-existent or 'unknown' signal -> REJECTED.
        """
        res_unknown = self.verifier.verify(
            task_id="heldout_fifo_src",
            design_family="fifo",
            candidate_signal="unknown"
        )
        self.assertEqual(res_unknown.status, "REJECTED")
        self.assertFalse(res_unknown.architectural_grounding)

        res_nonexistent = self.verifier.verify(
            task_id="heldout_fifo_src",
            design_family="fifo",
            candidate_signal="fake_signal_xyz"
        )
        self.assertEqual(res_nonexistent.status, "REJECTED")
        self.assertFalse(res_nonexistent.architectural_grounding)

    def test_case_4_causally_conforming_signal_rejection(self):
        """
        Test 4: In FIFO, 'write_ptr' operates normally (incrementing by 1),
        while 'count' violates occupancy conservation -> 'write_ptr' lacks anomaly evidence.
        """
        res_ptr = self.verifier.verify(
            task_id="heldout_fifo_src",
            design_family="fifo",
            candidate_signal="write_ptr"
        )
        # write_ptr should not be verified as the causal defect
        self.assertNotEqual(res_ptr.status, "VERIFIED")

        res_count = self.verifier.verify(
            task_id="heldout_fifo_src",
            design_family="fifo",
            candidate_signal="count"
        )
        self.assertEqual(res_count.status, "VERIFIED")
        self.assertTrue(res_count.invariant_evidence)

    def test_case_5_uart_counter_verified(self):
        """
        Test 5: UART counter 'cnt' exhibits anomalous skip transition -> VERIFIED.
        """
        res = self.verifier.verify(
            task_id="heldout_uart_src",
            design_family="uart",
            candidate_signal="cnt"
        )
        self.assertEqual(res.status, "VERIFIED")
        self.assertTrue(res.temporal_evidence)
        self.assertTrue(res.causal_evidence)

    def test_case_6_certificate_store_trust_filtering(self):
        """
        Test 6: CertificateStore only returns trusted certificates when only_trusted=True.
        """
        store = CertificateStore()

        trusted_cert = TransactionSemanticCertificate(
            certificate_id="CERT_TRUSTED_TEST",
            source_failure="heldout_axi_src",
            target_module="axi",
            target_signals=["valid_in", "ready_in", "valid_out", "ready_out"],
            defect_mechanism="AXI_HANDSHAKE_HOLD",
            transaction_context=TransactionContext(
                transaction_type="HANDSHAKE_TRANSFER",
                initiating_event={"valid_in": 1},
                boundary_signals=["valid_in", "ready_in", "valid_out", "ready_out"],
                active_window_cycles=4
            ),
            trigger_spec={"conditions": {"valid_in": 1}},
            protocol_obligation=ProtocolObligation(
                obligation_type="HANDSHAKE_DATA_STABILITY",
                initiating_condition={"valid_in": 1, "ready_in": 0},
                required_contract={"valid_out_stable": 1},
                violation_signature={"valid_out_dropped": 0},
                temporal_latency=1
            ),
            state_invariant_spec={"type": "STABILITY", "target_register": "valid_out"},
            causal_propagation_spec={"type": "STALL_PROPAGATION"},
            temporal_constraint={"order": "STRICT_CAUSAL_SEQUENCE"},
            expected_observable_consequence="AXI hold violation",
            metadata={"design_family": "axi", "symptom": "Timeout", "is_trusted": True, "root_cause_signal": "valid_out"}
        )

        untrusted_cert = TransactionSemanticCertificate(
            certificate_id="CERT_UNTRUSTED_TEST",
            source_failure="heldout_fsm_src",
            target_module="fsm",
            target_signals=["start", "state", "done"],
            defect_mechanism="FSM_STUCK_STATE",
            transaction_context=TransactionContext(
                transaction_type="CONTROL_STIMULUS",
                initiating_event={"start": 1},
                boundary_signals=["start", "state", "done"],
                active_window_cycles=3
            ),
            trigger_spec={"conditions": {"start": 1}},
            protocol_obligation=ProtocolObligation(
                obligation_type="STATE_TRANSITION_OBLIGATION",
                initiating_condition={"start": 1},
                required_contract={"expected_next_state": 1},
                violation_signature={"stuck_state": 0},
                temporal_latency=1
            ),
            state_invariant_spec={"type": "STATE_TRANSITION", "target_register": "state", "anomaly_state": 0},
            causal_propagation_spec={"type": "STATE_DEADLOCK"},
            temporal_constraint={"order": "STRICT_CAUSAL_SEQUENCE"},
            expected_observable_consequence="FSM stuck state",
            metadata={"design_family": "fsm", "symptom": "Timeout", "is_trusted": False, "root_cause_signal": "start"}
        )

        store.register(trusted_cert)
        store.register(untrusted_cert)

        # Query with only_trusted=True (default)
        trusted_cands = store.query_candidates(design_family="axi", only_trusted=True)
        self.assertEqual(len(trusted_cands), 1)
        self.assertEqual(trusted_cands[0][1].certificate_id, "CERT_TRUSTED_TEST")

        untrusted_cands = store.query_candidates(design_family="fsm", only_trusted=True)
        self.assertEqual(len(untrusted_cands), 0)

        # Query with only_trusted=False returns untrusted cert as well
        all_fsm_cands = store.query_candidates(design_family="fsm", only_trusted=False)
        self.assertEqual(len(all_fsm_cands), 1)


if __name__ == "__main__":
    unittest.main()
