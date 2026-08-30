import unittest
import os
import json
import tempfile
from src.reuse.certificate_store import CertificateStore, ValidationDecisionReport
from src.reuse.transaction_semantic_certificate import (
    TransactionSemanticCertificate,
    TransactionContext,
    ProtocolObligation
)


class TestCertificateStore(unittest.TestCase):
    """Unit tests for the CertificateStore registry and indexing engine."""

    def setUp(self):
        self.store = CertificateStore()
        
        self.fifo_cert = TransactionSemanticCertificate(
            certificate_id="CERT_FIFO_001",
            source_failure="heldout_fifo_src",
            target_module="fifo",
            target_signals=["count", "write_en", "read_en"],
            defect_mechanism="FIFO_SIMULTANEOUS_RW",
            transaction_context=TransactionContext(
                transaction_type="FIFO_STREAM",
                initiating_event={"write_en": 1, "read_en": 1},
                boundary_signals=["write_en", "read_en"]
            ),
            trigger_spec={"conditions": {"write_en": 1, "read_en": 1}},
            protocol_obligation=ProtocolObligation(
                obligation_type="OCCUPANCY_CONSERVATION",
                initiating_condition={"write_en": 1, "read_en": 1},
                required_contract={"count_stable": True},
                violation_signature={"count_overincrement": 1}
            ),
            state_invariant_spec={"type": "CONSERVATION", "target_register": "count"},
            causal_propagation_spec={"type": "OCCUPANCY_DIVERGENCE"},
            temporal_constraint={"max_latency_cycles": 4},
            expected_observable_consequence="FIFO count overincrements",
            metadata={"design_family": "fifo", "symptom": "Data Mismatch"}
        )

        self.axi_cert = TransactionSemanticCertificate(
            certificate_id="CERT_AXI_001",
            source_failure="heldout_axi_src",
            target_module="axi",
            target_signals=["valid_in", "ready_in", "valid_out", "ready_out"],
            defect_mechanism="AXI_HANDSHAKE_HOLD",
            transaction_context=TransactionContext(
                transaction_type="AXI_HANDSHAKE",
                initiating_event={"valid_in": 1},
                boundary_signals=["valid_in", "ready_in"]
            ),
            trigger_spec={"conditions": {"valid_in": 1}},
            protocol_obligation=ProtocolObligation(
                obligation_type="HANDSHAKE_DATA_STABILITY",
                initiating_condition={"valid_in": 1},
                required_contract={"valid_held": True},
                violation_signature={"premature_drop": 1}
            ),
            state_invariant_spec={"type": "STABILITY", "target_register": "valid_out"},
            causal_propagation_spec={"type": "STALL_PROPAGATION"},
            temporal_constraint={"max_latency_cycles": 4},
            expected_observable_consequence="AXI handshake drop causes timeout",
            metadata={"design_family": "axi", "symptom": "Timeout"}
        )

    def test_registration_and_retrieval(self):
        id1 = self.store.register(self.fifo_cert)
        id2 = self.store.register(self.axi_cert)

        self.assertEqual(id1, "CERT_FIFO_001")
        self.assertEqual(id2, "CERT_AXI_001")
        self.assertEqual(self.store.count(), 2)

        c1 = self.store.get("CERT_FIFO_001")
        self.assertIsNotNone(c1)
        self.assertEqual(c1.target_module, "fifo")

    def test_query_candidates_by_family_and_symptom(self):
        self.store.register(self.fifo_cert)
        self.store.register(self.axi_cert)

        fifo_candidates = self.store.query_candidates(
            design_family="fifo",
            symptom="Data Mismatch",
            observed_signals=["count", "write_en"]
        )
        self.assertEqual(len(fifo_candidates), 1)
        score, cert = fifo_candidates[0]
        self.assertEqual(cert.certificate_id, "CERT_FIFO_001")
        self.assertGreater(score, 1.0)

        axi_candidates = self.store.query_candidates(
            design_family="axi",
            symptom="Timeout",
            observed_signals=["valid_in", "ready_out"]
        )
        self.assertEqual(len(axi_candidates), 1)
        self.assertEqual(axi_candidates[0][1].certificate_id, "CERT_AXI_001")

    def test_query_candidates_no_match(self):
        self.store.register(self.fifo_cert)
        candidates = self.store.query_candidates(design_family="uart")
        self.assertEqual(len(candidates), 0)

    def test_json_save_and_load(self):
        self.store.register(self.fifo_cert)
        self.store.register(self.axi_cert)

        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "cert_store.json")
            self.store.save_to_file(fpath)

            loaded_store = CertificateStore.load_from_file(fpath)
            self.assertEqual(loaded_store.count(), 2)
            c = loaded_store.get("CERT_FIFO_001")
            self.assertIsNotNone(c)
            self.assertEqual(c.defect_mechanism, "FIFO_SIMULTANEOUS_RW")


if __name__ == "__main__":
    unittest.main()
