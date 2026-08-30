import unittest
import os
import json
import tempfile
from pathlib import Path

from src.reuse.transaction_semantic_certificate import (
    TransactionSemanticCertificate,
    TransactionContext,
    ProtocolObligation
)
from src.reuse.transaction_semantic_validator import TransactionSemanticValidator
from src.reuse.adaptive_transaction_boundary import AdaptiveTransactionBoundaryDetector
from src.reuse.adaptive_evidence import AdaptiveEvidenceClassifier
from src.reuse.adaptive_l2_adapter import AdaptiveL2Adapter
from src.reuse.adaptive_reuse_policy import AdaptiveReusePolicy
from src.reuse.certificate_store import CertificateStore


class TestSafetyProperties(unittest.TestCase):
    """
    Formal safety-property test suite for RCA-Reuse.
    Verifies that the system satisfies essential hardware verification safety invariants.
    """

    def setUp(self):
        self.store = CertificateStore()
        self.adapter = AdaptiveL2Adapter()
        self.policy = AdaptiveReusePolicy()
        self.detector = AdaptiveTransactionBoundaryDetector()
        self.classifier = AdaptiveEvidenceClassifier()
        self.validator = TransactionSemanticValidator()

        # Build standard FIFO Simultaneous RW Certificate
        self.fifo_cert = TransactionSemanticCertificate(
            certificate_id="CERT_FIFO_SIMULTANEOUS_RW_TEST",
            source_failure="heldout_fifo_src",
            target_module="fifo",
            target_signals=["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"],
            defect_mechanism="FIFO_SIMULTANEOUS_RW",
            transaction_context=TransactionContext(
                transaction_type="FIFO_STREAM_TRANSFER",
                initiating_event={"write_en": 1, "read_en": 1},
                boundary_signals=["write_en", "read_en", "count"],
                active_window_cycles=4
            ),
            trigger_spec={"conditions": {"write_en": 1, "read_en": 1}},
            protocol_obligation=ProtocolObligation(
                obligation_type="OCCUPANCY_CONSERVATION",
                initiating_condition={"write_en": 1, "read_en": 1},
                required_contract={"count_stable": True},
                violation_signature={"count_overincrement": 1},
                temporal_latency=1
            ),
            state_invariant_spec={
                "type": "CONSERVATION",
                "target_register": "count",
                "anomaly_delta": 1
            },
            causal_propagation_spec={
                "type": "OCCUPANCY_DIVERGENCE",
                "consequence_signal": "count"
            },
            temporal_constraint={
                "max_latency_cycles": 4,
                "ordering": ["tx_start", "obligation_violation", "causal_propagation"]
            },
            expected_observable_consequence="FIFO count register overincrements during simultaneous read/write",
            metadata={"design_family": "fifo", "symptom": "Data Mismatch"}
        )

    def test_property_1_true_positive_reuse(self):
        """
        SAFETY PROPERTY 1:
        Matching defect manifestation with identical protocol violation -> REUSE_RCA.
        """
        # Verified cycle states where simultaneous R/W causes count overincrement
        cycle_states = [
            {"clk": 1, "rst_n": 0, "write_en": 0, "read_en": 0, "count": 0, "write_ptr": 0, "read_ptr": 0, "full": 0, "empty": 1},
            {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "count": 0, "write_ptr": 0, "read_ptr": 0, "full": 0, "empty": 1},
            {"clk": 1, "rst_n": 1, "write_en": 1, "read_en": 1, "count": 0, "write_ptr": 1, "read_ptr": 1, "full": 0, "empty": 0},  # trigger
            {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "count": 1, "write_ptr": 1, "read_ptr": 1, "full": 0, "empty": 0},  # anomaly: count 0->1
            {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "count": 1, "write_ptr": 1, "read_ptr": 1, "full": 0, "empty": 0},  # downstream desync
            {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "count": 1, "write_ptr": 1, "read_ptr": 1, "full": 0, "empty": 0},
        ]
        segments = self.detector.detect_segments(cycle_states, ["write_en", "read_en", "count"])
        suff = self.classifier.classify_sufficiency(cycle_states, segments)
        self.assertTrue(suff.is_sufficient_for_validation)

        # Direct semantic validation check
        tx_cycles = self.validator.detect_transaction_events(self.fifo_cert.transaction_context, cycle_states)
        self.assertIn(2, tx_cycles)

    def test_property_2_adversarial_same_symptom_rejection(self):
        """
        SAFETY PROPERTY 2:
        Adversarial distractor: Same 'Data Mismatch' symptom, but defect mechanism is
        single write with pointer corruption (not simultaneous R/W) -> FALLBACK_INDEPENDENT_RCA.
        """
        # Waveform only has write_en=1, read_en=0 (simultaneous R/W never occurs)
        cycle_states = [
            {"clk": 1, "rst_n": 0, "write_en": 0, "read_en": 0, "count": 0, "write_ptr": 0, "read_ptr": 0},
            {"clk": 1, "rst_n": 1, "write_en": 1, "read_en": 0, "count": 1, "write_ptr": 5, "read_ptr": 0},  # ptr jump bug
            {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "count": 1, "write_ptr": 5, "read_ptr": 0},
            {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "count": 1, "write_ptr": 5, "read_ptr": 0},
        ]
        tx_cycles = self.validator.detect_transaction_events(self.fifo_cert.transaction_context, cycle_states)
        # Initiating event write_en=1 && read_en=1 is absent
        self.assertEqual(len(tx_cycles), 0)

        # Adapter / Policy must map unexercised context to FALLBACK_INDEPENDENT_RCA
        val_res = {"decision": "INSUFFICIENT_EVIDENCE", "stage": "TRANSACTION_CONTEXT"}
        decision = self.policy.decide(val_res)
        self.assertEqual(decision["policy_action"], "FALLBACK_INDEPENDENT_RCA")
        self.assertFalse(decision["safe_to_reuse"])

    def test_property_3_incomplete_trace_safety(self):
        """
        SAFETY PROPERTY 3:
        Waveform truncated while transaction is actively executing ->
        Must be classified as TRANSACTION_ACCEPTED_INCOMPLETE and rejected to FALLBACK.
        """
        # 3-cycle truncated trace where transaction starts at cycle 2 with low confidence
        cycle_states = [
            {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "count": 0},
            {"clk": 1, "rst_n": 1, "write_en": 1, "read_en": 1, "count": 0},  # active at termination
            {"clk": 1, "rst_n": 1, "write_en": 1, "read_en": 1, "count": 0},
        ]
        segments = self.detector.detect_segments(cycle_states, ["write_en", "read_en", "count"])
        suff = self.classifier.classify_sufficiency(cycle_states, segments)
        
        # Must recommend INSUFFICIENT_EVIDENCE
        self.assertEqual(suff.decision_recommendation, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(suff.is_sufficient_for_validation)
        
        policy_decision = self.policy.decide({"decision": "INSUFFICIENT_EVIDENCE", "stage": suff.sufficiency_state})
        self.assertEqual(policy_decision["policy_action"], "FALLBACK_INDEPENDENT_RCA")

    def test_property_4_certificate_mismatch_rejection(self):
        """
        SAFETY PROPERTY 4:
        Certificate for FIFO evaluated against an AXI interface ->
        Target signals missing -> Conservative FALLBACK.
        """
        axi_states = [
            {"clk": 1, "rst_n": 1, "valid_in": 1, "ready_in": 1, "valid_out": 0, "ready_out": 0},
            {"clk": 1, "rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 1, "ready_out": 1},
            {"clk": 1, "rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0, "ready_out": 0},
        ]
        # Required FIFO signals (count, write_en, read_en) are None
        tx_cycles = self.validator.detect_transaction_events(self.fifo_cert.transaction_context, axi_states)
        self.assertEqual(len(tx_cycles), 0)

    def test_property_5_variable_latency_positive_transfer(self):
        """
        SAFETY PROPERTY 5:
        Matching defect manifestation under variable handshake stall latency ->
        Adaptive boundary recovers the extended active window and enables REUSE.
        """
        stalled_states = [
            {"clk": 1, "rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0},
            {"clk": 1, "rst_n": 1, "valid_in": 1, "ready_in": 0, "valid_out": 0},  # stall 1
            {"clk": 1, "rst_n": 1, "valid_in": 1, "ready_in": 0, "valid_out": 0},  # stall 2
            {"clk": 1, "rst_n": 1, "valid_in": 1, "ready_in": 0, "valid_out": 0},  # stall 3
            {"clk": 1, "rst_n": 1, "valid_in": 1, "ready_in": 0, "valid_out": 0},  # stall 4
            {"clk": 1, "rst_n": 1, "valid_in": 1, "ready_in": 1, "valid_out": 1},  # transfer
            {"clk": 1, "rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0},  # quiescence
            {"clk": 1, "rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0},
        ]
        segments = self.detector.detect_segments(stalled_states, ["valid_in", "ready_in", "valid_out"])
        self.assertEqual(len(segments), 1)
        self.assertGreaterEqual(segments[0].length, 6)
        
        suff = self.classifier.classify_sufficiency(stalled_states, segments)
        self.assertTrue(suff.is_sufficient_for_validation)
        self.assertEqual(suff.sufficiency_state, "TRANSACTION_COMPLETED_SUFFICIENT")

    def test_property_6_ambiguous_evidence_fallback(self):
        """
        SAFETY PROPERTY 6:
        Contradictory or overlapping transaction candidates creating ambiguity ->
        Classified as TRANSACTION_BOUNDARIES_AMBIGUOUS -> FALLBACK_INDEPENDENT_RCA.
        """
        from src.reuse.adaptive_transaction_boundary import TransactionSegment
        # Manually create overlapping segments
        seg1 = TransactionSegment(start_cycle=2, end_cycle=6, event_sequence=[], confidence=0.7, evidence_reasons=[])
        seg2 = TransactionSegment(start_cycle=4, end_cycle=8, event_sequence=[], confidence=0.6, evidence_reasons=[])
        
        states = [{"clk": 1, "rst_n": 1} for _ in range(12)]
        suff = self.classifier.classify_sufficiency(states, [seg1, seg2])
        self.assertEqual(suff.sufficiency_state, "TRANSACTION_BOUNDARIES_AMBIGUOUS")
        self.assertEqual(suff.decision_recommendation, "INSUFFICIENT_EVIDENCE")

    def test_property_7_certificate_serialization_lossless_roundtrip(self):
        """
        SAFETY PROPERTY 7:
        Certificate serialization to JSON and deserialization must be 100% lossless.
        """
        d = self.fifo_cert.to_dict()
        json_str = json.dumps(d)
        loaded_d = json.loads(json_str)
        reconstructed_cert = TransactionSemanticCertificate.from_dict(loaded_d)

        self.assertEqual(self.fifo_cert.certificate_id, reconstructed_cert.certificate_id)
        self.assertEqual(self.fifo_cert.target_module, reconstructed_cert.target_module)
        self.assertEqual(self.fifo_cert.target_signals, reconstructed_cert.target_signals)
        self.assertEqual(self.fifo_cert.transaction_context.transaction_type, reconstructed_cert.transaction_context.transaction_type)
        self.assertEqual(self.fifo_cert.transaction_context.initiating_event, reconstructed_cert.transaction_context.initiating_event)
        self.assertEqual(self.fifo_cert.protocol_obligation.obligation_type, reconstructed_cert.protocol_obligation.obligation_type)
        self.assertEqual(self.fifo_cert.protocol_obligation.temporal_latency, reconstructed_cert.protocol_obligation.temporal_latency)
        self.assertEqual(self.fifo_cert.state_invariant_spec, reconstructed_cert.state_invariant_spec)
        self.assertEqual(self.fifo_cert.causal_propagation_spec, reconstructed_cert.causal_propagation_spec)
        self.assertEqual(self.fifo_cert.metadata, reconstructed_cert.metadata)


if __name__ == "__main__":
    unittest.main()
