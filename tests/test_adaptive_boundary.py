import unittest
import os
import json
from src.reuse.adaptive_transaction_boundary import AdaptiveTransactionBoundaryDetector, TransactionSegment
from src.reuse.adaptive_evidence import AdaptiveEvidenceClassifier, EvidenceSufficiencyResult
from src.reuse.adaptive_l2_adapter import AdaptiveL2Adapter
from src.reuse.transaction_semantic_certificate import TransactionSemanticCertificate, TransactionContext, ProtocolObligation

class TestAdaptiveTransactionBoundary(unittest.TestCase):
    def setUp(self):
        self.detector = AdaptiveTransactionBoundaryDetector(quiescence_threshold=2)
        self.classifier = AdaptiveEvidenceClassifier()
        self.adapter = AdaptiveL2Adapter()

    def test_edge_detection(self):
        states = [
            {"clk": 1, "rst_n": 0, "valid": 0},
            {"clk": 1, "rst_n": 1, "valid": 0},
            {"clk": 1, "rst_n": 1, "valid": 1}, # cycle 2: rising
            {"clk": 1, "rst_n": 1, "valid": 1},
            {"clk": 1, "rst_n": 1, "valid": 0}, # cycle 4: falling
        ]
        edges = self.detector.detect_edges(states, "valid")
        self.assertEqual(edges, [(2, "RISING_EDGE"), (4, "FALLING_EDGE")])

    def test_handshake_operators(self):
        states = [
            {"clk": 1, "rst_n": 1, "req": 0, "ack": 0},
            {"clk": 1, "rst_n": 1, "req": 1, "ack": 0}, # stall
            {"clk": 1, "rst_n": 1, "req": 1, "ack": 1}, # accept
            {"clk": 1, "rst_n": 1, "req": 0, "ack": 0},
        ]
        events = self.detector.detect_handshake_events(states, "req", "ack")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_type, "HANDSHAKE_STALL")
        self.assertEqual(events[1].event_type, "HANDSHAKE_ACCEPT")

    def test_state_transition_operator(self):
        states = [
            {"clk": 1, "rst_n": 1, "state": 0},
            {"clk": 1, "rst_n": 1, "state": 1},
            {"clk": 1, "rst_n": 1, "state": 2},
            {"clk": 1, "rst_n": 1, "state": 0},
        ]
        events = self.detector.detect_state_transitions(states, "state")
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].details, {"from": 0, "to": 1})
        self.assertEqual(events[1].details, {"from": 1, "to": 2})
        self.assertEqual(events[2].details, {"from": 2, "to": 0})

    def test_variable_length_segmentation(self):
        # Transaction 1: length 5 (cycles 2-6)
        # Quiescence: cycles 7-9
        # Transaction 2: length 4 (cycles 10-13)
        states = []
        for i in range(20):
            rst = 0 if i < 2 else 1
            if 2 <= i <= 6:
                states.append({"clk": 1, "rst_n": rst, "start": 1 if i == 2 else 0, "state": 1 if i < 5 else 0})
            elif 10 <= i <= 13:
                states.append({"clk": 1, "rst_n": rst, "start": 1 if i == 10 else 0, "state": 2 if i < 13 else 0})
            else:
                states.append({"clk": 1, "rst_n": rst, "start": 0, "state": 0})
                
        segments = self.detector.detect_segments(states, ["start", "state"])
        self.assertEqual(len(segments), 2)
        self.assertGreaterEqual(segments[0].length, 5)
        self.assertGreaterEqual(segments[1].length, 4)

    # -------------------------------------------------------------------------
    # 8 ADVERSARIAL SAFETY TESTS
    # -------------------------------------------------------------------------
    
    def test_adv_1_same_symptom_diff_defect(self):
        """Adversarial 1: Symptom matches but protocol obligation differs."""
        # Certificate expects count to drop when write_en && read_en
        # Waveform has single write only
        states = [
            {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "count": 0, "write_ptr": 0, "read_ptr": 0},
            {"clk": 1, "rst_n": 1, "write_en": 1, "read_en": 0, "count": 1, "write_ptr": 1, "read_ptr": 0},
            {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "count": 1, "write_ptr": 1, "read_ptr": 0},
            {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "count": 1, "write_ptr": 1, "read_ptr": 0},
        ]
        segments = self.detector.detect_segments(states, ["write_en", "read_en", "count"])
        self.assertEqual(len(segments), 1)
        # Initiating event for simultaneous RW was not active in this segment
        suff = self.classifier.classify_sufficiency(states, segments)
        self.assertTrue(suff.is_sufficient_for_validation)

    def test_adv_2_same_trigger_diff_defect(self):
        """Adversarial 2: Trigger occurs but obligation is fulfilled."""
        states = [
            {"clk": 1, "rst_n": 1, "start": 0, "state": 0, "done": 0},
            {"clk": 1, "rst_n": 1, "start": 1, "state": 0, "done": 0},
            {"clk": 1, "rst_n": 1, "start": 0, "state": 1, "done": 0}, # state advanced normally
            {"clk": 1, "rst_n": 1, "start": 0, "state": 0, "done": 1},
        ]
        segments = self.detector.detect_segments(states, ["start", "state", "done"])
        self.assertEqual(len(segments), 1)

    def test_adv_3_same_invariant_diff_semantics(self):
        """Adversarial 3: Same low-level delta in unrelated transaction."""
        states = [
            {"clk": 1, "rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0},
            {"clk": 1, "rst_n": 1, "valid_in": 0, "ready_in": 1, "valid_out": 0},
            {"clk": 1, "rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0},
            {"clk": 1, "rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0},
        ]
        segments = self.detector.detect_segments(states, ["valid_in", "ready_in", "valid_out"])
        suff = self.classifier.classify_sufficiency(states, segments)
        self.assertIn(suff.sufficiency_state, ["TRANSACTION_NEVER_INITIATED", "TRANSACTION_COMPLETED_SUFFICIENT"])

    def test_adv_4_partial_transaction(self):
        """Adversarial 4: Waveform truncated mid-transaction."""
        states = [
            {"clk": 1, "rst_n": 1, "valid_in": 0, "d_in": 0, "valid_out": 0, "d_out": 0},
            {"clk": 1, "rst_n": 1, "valid_in": 1, "d_in": 10, "valid_out": 0, "d_out": 0}, # start
            {"clk": 1, "rst_n": 1, "valid_in": 1, "d_in": 20, "valid_out": 0, "d_out": 0}, # truncated
        ]
        segments = self.detector.detect_segments(states, ["valid_in", "d_in", "valid_out", "d_out"])
        suff = self.classifier.classify_sufficiency(states, segments)
        # Should be flagged as INSUFFICIENT_EVIDENCE
        self.assertEqual(suff.decision_recommendation, "INSUFFICIENT_EVIDENCE")

    def test_adv_5_transaction_with_long_stall(self):
        """Adversarial 5: Transaction stalled for 6 cycles then completed."""
        states = [
            {"clk": 1, "rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0},
            {"clk": 1, "rst_n": 1, "valid_in": 1, "ready_in": 0, "valid_out": 0}, # stall 1
            {"clk": 1, "rst_n": 1, "valid_in": 1, "ready_in": 0, "valid_out": 0}, # stall 2
            {"clk": 1, "rst_n": 1, "valid_in": 1, "ready_in": 0, "valid_out": 0}, # stall 3
            {"clk": 1, "rst_n": 1, "valid_in": 1, "ready_in": 0, "valid_out": 0}, # stall 4
            {"clk": 1, "rst_n": 1, "valid_in": 1, "ready_in": 1, "valid_out": 1}, # accept
            {"clk": 1, "rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0}, # completion
            {"clk": 1, "rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0}, # quiescence
        ]
        segments = self.detector.detect_segments(states, ["valid_in", "ready_in", "valid_out"])
        self.assertEqual(len(segments), 1)
        # Boundary spans the full 6-cycle stall + completion
        self.assertGreaterEqual(segments[0].length, 6)

    def test_adv_6_multiple_transactions_one_waveform(self):
        """Adversarial 6: Multiple discrete transactions separated by quiescence."""
        states = []
        for i in range(25):
            rst = 1
            if 3 <= i <= 6:
                states.append({"clk": 1, "rst_n": rst, "write_en": 1, "count": 1})
            elif 14 <= i <= 18:
                states.append({"clk": 1, "rst_n": rst, "write_en": 1, "count": 2})
            else:
                states.append({"clk": 1, "rst_n": rst, "write_en": 0, "count": 0})
        segments = self.detector.detect_segments(states, ["write_en", "count"])
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].start_cycle, 3)
        self.assertEqual(segments[1].start_cycle, 14)

    def test_adv_7_reset_followed_by_transaction(self):
        """Adversarial 7: Long reset period preceding transaction."""
        states = [
            {"clk": 1, "rst_n": 0, "start": 1, "state": 0},
            {"clk": 1, "rst_n": 0, "start": 1, "state": 0},
            {"clk": 1, "rst_n": 0, "start": 1, "state": 0},
            {"clk": 1, "rst_n": 1, "start": 0, "state": 0},
            {"clk": 1, "rst_n": 1, "start": 1, "state": 1}, # real tx start
            {"clk": 1, "rst_n": 1, "start": 0, "state": 0},
            {"clk": 1, "rst_n": 1, "start": 0, "state": 0},
        ]
        segments = self.detector.detect_segments(states, ["start", "state"])
        self.assertEqual(len(segments), 1)
        self.assertGreaterEqual(segments[0].start_cycle, 4)

    def test_adv_8_back_to_back_transactions(self):
        """Adversarial 8: Back to back transactions without gaps."""
        states = [
            {"clk": 1, "rst_n": 1, "start": 0, "state": 0},
            {"clk": 1, "rst_n": 1, "start": 1, "state": 1},
            {"clk": 1, "rst_n": 1, "start": 1, "state": 2}, # second tx begins
            {"clk": 1, "rst_n": 1, "start": 0, "state": 0},
            {"clk": 1, "rst_n": 1, "start": 0, "state": 0},
        ]
        segments = self.detector.detect_segments(states, ["start", "state"])
        self.assertEqual(len(segments), 1)
        self.assertGreaterEqual(segments[0].length, 3)

if __name__ == "__main__":
    unittest.main()
