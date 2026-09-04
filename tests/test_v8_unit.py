import pytest
import os
import sys

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.reuse.v8_semantic_roles import HardwareRole, RoleClass, SignalDirection, SemanticRoleNormalizer
from src.reuse.v8_unified_certificate import (
    V8UnifiedCertificate, RootCauseIdentity, FailureMechanism,
    TemporalBehavior, EvidenceArtifact, RejectedAlternative,
    TrustAuditMetadata, HardwareInvariant, ProtocolObligationSpec,
    CertificateTrustStatus, CausalRelation
)
from src.reuse.v8_protocol_adapters import ProtocolRegistry, UartProtocolAdapter, FifoProtocolAdapter
from src.reuse.v8_deterministic_ingestion import DeterministicSourceIngestion, IngestionStatus
from src.reuse.v8_adaptive_settlement import EvidenceAwareSettlementEngine, SettlementTerminationReason
from src.reuse.v8_certificate_store import V8CertificateStore


def test_semantic_role_normalizer():
    # 1. FIFO signals
    role, r_class = SemanticRoleNormalizer.normalize_signal("count", design_family="fifo")
    assert role == HardwareRole.OCCUPANCY_TRACKER
    assert r_class == RoleClass.STATUS

    role_alias, _ = SemanticRoleNormalizer.normalize_signal("fifo_count", design_family="fifo")
    assert role_alias == HardwareRole.OCCUPANCY_TRACKER
    assert SemanticRoleNormalizer.are_roles_compatible(role, role_alias)

    # 2. UART signals
    role_uart, _ = SemanticRoleNormalizer.normalize_signal("cnt", design_family="uart")
    assert role_uart == HardwareRole.BAUD_PRESCALER

    role_baud, _ = SemanticRoleNormalizer.normalize_signal("baud_cnt", design_family="uart")
    assert role_baud == HardwareRole.BAUD_PRESCALER
    assert SemanticRoleNormalizer.are_roles_compatible(role_uart, role_baud)

    # 3. Incompatibility check
    ptr_role, _ = SemanticRoleNormalizer.normalize_signal("write_ptr", design_family="fifo")
    assert ptr_role == HardwareRole.POINTER
    assert not SemanticRoleNormalizer.are_roles_compatible(role, ptr_role)


def test_v8_unified_certificate_serialization():
    rc = RootCauseIdentity(
        signal_name="count",
        normalized_role=HardwareRole.OCCUPANCY_TRACKER,
        role_class=RoleClass.STATUS,
        module_name="fifo",
        bit_width=4
    )
    obl = ProtocolObligationSpec(
        obligation_name="OCCUPANCY_CONSERVATION",
        precondition={"write_en": 1, "read_en": 1},
        required_postcondition={"count_delta": 0},
        violation_signature={"count_delta_nonzero": 1}
    )
    mech = FailureMechanism(
        violated_invariant=HardwareInvariant.OCCUPANCY_CONSERVATION,
        protocol_obligation=obl,
        causal_mechanism_name="FIFO_SIMULTANEOUS_RW_COUNTER_CORRUPTION",
        upstream_antecedent="count",
        downstream_symptom="Data Mismatch"
    )
    temp = TemporalBehavior(
        initiating_event={"write_en": 1, "read_en": 1},
        trigger_condition={"write_en": 1, "read_en": 1}
    )
    ev = EvidenceArtifact(
        first_anomaly_cycle=45,
        testbench_assertion_message="empty assertion failed"
    )
    tm = TrustAuditMetadata(
        trust_status=CertificateTrustStatus.TRUSTED,
        source_rca_confidence=0.95
    )

    cert = V8UnifiedCertificate(
        certificate_id="V8_TEST_CERT_001",
        source_case_id="heldout_fifo_src",
        design_family="fifo",
        root_cause=rc,
        mechanism=mech,
        temporal=temp,
        evidence=ev,
        trust_metadata=tm,
        target_signals=["count", "write_en", "read_en"]
    )

    cert_dict = cert.to_dict()
    assert cert_dict["certificate_id"] == "V8_TEST_CERT_001"
    assert cert_dict["root_cause"]["normalized_role"] == "OCCUPANCY_TRACKER"
    assert cert_dict["trust_metadata"]["trust_status"] == "TRUSTED"

    # Round trip
    reconstructed = V8UnifiedCertificate.from_dict(cert_dict)
    assert reconstructed.certificate_id == cert.certificate_id
    assert reconstructed.root_cause.normalized_role == HardwareRole.OCCUPANCY_TRACKER
    assert reconstructed.mechanism.violated_invariant == HardwareInvariant.OCCUPANCY_CONSERVATION


def test_protocol_registry():
    supported = ProtocolRegistry.list_supported_families()
    for fam in ["fifo", "axi", "fsm", "uart", "pipeline"]:
        assert fam in supported
        adapter = ProtocolRegistry.get_adapter(fam)
        assert adapter is not None
        assert adapter.family_name == fam


def test_deterministic_source_ingestion_statuses():
    ingestion = DeterministicSourceIngestion(workspace_root=WORKSPACE_ROOT)

    # 1. Test MODEL_OUTPUT_INVALID
    res_inv = ingestion.ingest_source_manifestation(
        source_case_id="test_case_1",
        design_family="axi",
        metadata={"symptom": "Timeout"},
        baseline_status="INVALID_OUTPUT"
    )
    assert res_inv.status == IngestionStatus.MODEL_OUTPUT_INVALID
    assert not res_inv.is_trusted

    # 2. Test RCA_UNKNOWN
    res_unk = ingestion.ingest_source_manifestation(
        source_case_id="test_case_2",
        design_family="fsm",
        metadata={"symptom": "Stuck State"},
        baseline_diagnosis="unknown",
        baseline_status="SUCCESS"
    )
    assert res_unk.status == IngestionStatus.RCA_UNKNOWN
    assert not res_unk.is_trusted

    # 3. Test CERTIFICATE_REJECTED (ungrounded hallucination)
    res_rej = ingestion.ingest_source_manifestation(
        source_case_id="heldout_fifo_src",
        design_family="fifo",
        metadata={"symptom": "Data Mismatch"},
        baseline_diagnosis="hallucinated_ghost_signal",
        baseline_status="SUCCESS"
    )
    assert res_rej.status == IngestionStatus.CERTIFICATE_REJECTED
    assert not res_rej.is_trusted


def test_adaptive_settlement_engine():
    engine = EvidenceAwareSettlementEngine()
    signal_map = {"count": HardwareRole.OCCUPANCY_TRACKER}

    # Test short trace truncation
    dec_short = engine.evaluate_settlement(
        cycle_states=[{"count": 0}, {"count": 1}],
        design_family="fifo",
        trigger_cycle=0,
        signal_role_map=signal_map
    )
    assert dec_short.termination_reason == SettlementTerminationReason.INSUFFICIENT_EVIDENCE_TRUNCATED

    # Test settled FIFO trace
    settled_states = [
        {"count": 0}, {"count": 1}, {"count": 1},
        {"count": 1}, {"count": 1}, {"count": 1}
    ]
    dec_settled = engine.evaluate_settlement(
        cycle_states=settled_states,
        design_family="fifo",
        trigger_cycle=1,
        signal_role_map=signal_map
    )
    assert dec_settled.is_settled
    assert dec_settled.termination_reason == SettlementTerminationReason.SETTLEMENT_REACHED
