import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum

from .v8_semantic_roles import HardwareRole, SignalDirection, RoleClass


class HardwareInvariant(str, Enum):
    """Formal hardware invariants evaluated during causal verification."""
    OCCUPANCY_CONSERVATION = "OCCUPANCY_CONSERVATION"
    HANDSHAKE_STABILITY = "HANDSHAKE_STABILITY"
    STATE_TRANSITION_DEADLOCK = "STATE_TRANSITION_DEADLOCK"
    BAUD_PERIODIC_ROLLOVER = "BAUD_PERIODIC_ROLLOVER"
    STAGE_CONTROL_TOKEN_DRAIN = "STAGE_CONTROL_TOKEN_DRAIN"
    FORWARDING_DATA_CONSISTENCY = "FORWARDING_DATA_CONSISTENCY"
    GENERIC_INVARIANT = "GENERIC_INVARIANT"


class CausalRelation(str, Enum):
    """Causal directionality relative to the observable testbench symptom."""
    ROOT_CAUSE_ANTECEDENT = "ROOT_CAUSE_ANTECEDENT"
    INTERMEDIATE_PROPAGATION = "INTERMEDIATE_PROPAGATION"
    DOWNSTREAM_SYMPTOM = "DOWNSTREAM_SYMPTOM"
    CORRELATED_CONCURRENT = "CORRELATED_CONCURRENT"


class CertificateTrustStatus(str, Enum):
    """Detailed audit status for certificate registration."""
    TRUSTED = "TRUSTED"
    MODEL_OUTPUT_INVALID = "MODEL_OUTPUT_INVALID"
    RCA_UNKNOWN = "RCA_UNKNOWN"
    VERIFIER_REJECTED = "VERIFIER_REJECTED"
    SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


@dataclass
class RootCauseIdentity:
    """Architectural and semantic identity of the diagnosed root cause."""
    signal_name: str
    normalized_role: HardwareRole
    signal_direction: SignalDirection = SignalDirection.INTERNAL_REGISTER
    role_class: RoleClass = RoleClass.STATE
    module_name: str = ""
    bit_width: int = 1


@dataclass
class ProtocolObligationSpec:
    """Contractual protocol rule violated by the bug."""
    obligation_name: str
    precondition: Dict[str, Any]
    required_postcondition: Dict[str, Any]
    violation_signature: Dict[str, Any]
    latency_cycles: int = 1


@dataclass
class FailureMechanism:
    """Causal failure mechanism violated in hardware."""
    violated_invariant: HardwareInvariant
    protocol_obligation: ProtocolObligationSpec
    causal_mechanism_name: str
    upstream_antecedent: str
    downstream_symptom: str
    causal_relation: CausalRelation = CausalRelation.ROOT_CAUSE_ANTECEDENT


@dataclass
class TemporalBehavior:
    """Exact event sequencing and observation requirements."""
    initiating_event: Dict[str, Any]
    trigger_condition: Dict[str, Any]
    active_window_cycles: int = 4
    min_settlement_cycles: int = 2
    max_observation_budget: int = 16
    strict_temporal_order: bool = True
    settlement_requirement: str = "ARCHITECTURAL_SETTLED"


@dataclass
class EvidenceArtifact:
    """Observable RTL, waveform, and simulation evidence supporting diagnosis."""
    rtl_declaration: str = ""
    rtl_assignment_context: str = ""
    first_anomaly_cycle: int = -1
    anomaly_timestamp_ns: float = -1.0
    waveform_transition_summary: Dict[str, Any] = field(default_factory=dict)
    testbench_assertion_message: str = ""
    supporting_observations: List[str] = field(default_factory=list)


@dataclass
class RejectedAlternative:
    """Explicitly audited competing signals rejected during RCA."""
    candidate_signal: str
    normalized_role: HardwareRole
    rejection_rationale: str
    is_downstream_symptom: bool = False


@dataclass
class TrustAuditMetadata:
    """Multi-dimensional trust and verifier confidence score audit."""
    trust_status: CertificateTrustStatus
    source_rca_confidence: float = 0.0
    verifier_rule_verdict: str = ""
    verifier_explanation: str = ""
    evidence_completeness_score: float = 1.0
    extraction_latency_ms: float = 0.0
    serialization_format_version: str = "V8_UNIFIED"


@dataclass
class V8UnifiedCertificate:
    """
    Unified Domain-Independent Debugging Knowledge Certificate.
    
    Captures complete root-cause identity, normalized architectural roles,
    formal invariant contracts, temporal causality, and audit evidence.
    """
    certificate_id: str
    source_case_id: str
    design_family: str
    root_cause: RootCauseIdentity
    mechanism: FailureMechanism
    temporal: TemporalBehavior
    evidence: EvidenceArtifact
    rejected_alternatives: List[RejectedAlternative] = field(default_factory=list)
    trust_metadata: TrustAuditMetadata = field(default_factory=lambda: TrustAuditMetadata(trust_status=CertificateTrustStatus.PENDING_VERIFICATION))
    target_signals: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes certificate to clean JSON-compatible dictionary."""
        data = asdict(self)
        # Convert enums to strings
        data["root_cause"]["normalized_role"] = self.root_cause.normalized_role.value
        data["root_cause"]["signal_direction"] = self.root_cause.signal_direction.value
        data["root_cause"]["role_class"] = self.root_cause.role_class.value
        data["mechanism"]["violated_invariant"] = self.mechanism.violated_invariant.value
        data["mechanism"]["causal_relation"] = self.mechanism.causal_relation.value
        data["trust_metadata"]["trust_status"] = self.trust_metadata.trust_status.value
        for alt in data.get("rejected_alternatives", []):
            if isinstance(alt.get("normalized_role"), HardwareRole):
                alt["normalized_role"] = alt["normalized_role"].value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'V8UnifiedCertificate':
        """Constructs a V8UnifiedCertificate from a dictionary."""
        rc_data = data["root_cause"]
        rc = RootCauseIdentity(
            signal_name=rc_data["signal_name"],
            normalized_role=HardwareRole(rc_data["normalized_role"]),
            signal_direction=SignalDirection(rc_data.get("signal_direction", "INTERNAL_REGISTER")),
            role_class=RoleClass(rc_data.get("role_class", "STATE")),
            module_name=rc_data.get("module_name", ""),
            bit_width=rc_data.get("bit_width", 1)
        )

        mech_data = data["mechanism"]
        obl_data = mech_data["protocol_obligation"]
        obl = ProtocolObligationSpec(**obl_data)
        mech = FailureMechanism(
            violated_invariant=HardwareInvariant(mech_data["violated_invariant"]),
            protocol_obligation=obl,
            causal_mechanism_name=mech_data.get("causal_mechanism_name", ""),
            upstream_antecedent=mech_data.get("upstream_antecedent", ""),
            downstream_symptom=mech_data.get("downstream_symptom", ""),
            causal_relation=CausalRelation(mech_data.get("causal_relation", "ROOT_CAUSE_ANTECEDENT"))
        )

        temp = TemporalBehavior(**data["temporal"])
        ev = EvidenceArtifact(**data["evidence"])

        alts = []
        for a in data.get("rejected_alternatives", []):
            alts.append(RejectedAlternative(
                candidate_signal=a["candidate_signal"],
                normalized_role=HardwareRole(a.get("normalized_role", "GENERIC_PORT")),
                rejection_rationale=a["rejection_rationale"],
                is_downstream_symptom=a.get("is_downstream_symptom", False)
            ))

        tm_data = data["trust_metadata"]
        tm = TrustAuditMetadata(
            trust_status=CertificateTrustStatus(tm_data["trust_status"]),
            source_rca_confidence=tm_data.get("source_rca_confidence", 0.0),
            verifier_rule_verdict=tm_data.get("verifier_rule_verdict", ""),
            verifier_explanation=tm_data.get("verifier_explanation", ""),
            evidence_completeness_score=tm_data.get("evidence_completeness_score", 1.0),
            extraction_latency_ms=tm_data.get("extraction_latency_ms", 0.0),
            serialization_format_version=tm_data.get("serialization_format_version", "V8_UNIFIED")
        )

        return cls(
            certificate_id=data["certificate_id"],
            source_case_id=data["source_case_id"],
            design_family=data["design_family"],
            root_cause=rc,
            mechanism=mech,
            temporal=temp,
            evidence=ev,
            rejected_alternatives=alts,
            trust_metadata=tm,
            target_signals=data.get("target_signals", []),
            metadata=data.get("metadata", {})
        )
