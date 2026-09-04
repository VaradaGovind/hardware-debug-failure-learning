import os
import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from .v8_unified_certificate import (
    V8UnifiedCertificate, CertificateTrustStatus, HardwareInvariant
)
from .v8_semantic_roles import HardwareRole, SemanticRoleNormalizer
from .v8_protocol_adapters import ProtocolRegistry, BaseProtocolAdapter
from .v8_adaptive_settlement import EvidenceAwareSettlementEngine, SettlementTerminationReason
from .generic_certificate import parse_vcd_signals, build_cycle_state_table


@dataclass
class V8ValidationReport:
    """Structured validation report emitted by V8 Certificate Store."""
    certificate_id: str
    target_id: str
    design_family: str
    raw_validator_decision: str  # "PASS", "FAIL", "INSUFFICIENT_EVIDENCE"
    policy_action: str           # "REUSE_RCA", "FALLBACK_INDEPENDENT_RCA"
    safe_to_reuse: bool
    reused_signal_name: Optional[str]
    normalized_role: Optional[HardwareRole]
    decision_reason: str
    settlement_reason: str
    effective_window_cycles: int
    validation_latency_ms: float
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "target_id": self.target_id,
            "design_family": self.design_family,
            "raw_validator_decision": self.raw_validator_decision,
            "policy_action": self.policy_action,
            "safe_to_reuse": self.safe_to_reuse,
            "reused_signal_name": self.reused_signal_name,
            "normalized_role": self.normalized_role.value if self.normalized_role else None,
            "decision_reason": self.decision_reason,
            "settlement_reason": self.settlement_reason,
            "effective_window_cycles": self.effective_window_cycles,
            "validation_latency_ms": self.validation_latency_ms,
            "metrics": self.metrics
        }


class V8CertificateStore:
    """
    V8 Unified Semantic Certificate Store.
    
    Indexes certificates by design family, normalized hardware roles, and formal invariants.
    Executes role-aware candidate retrieval, protocol validation, and evidence-aware settlement.
    """

    def __init__(self):
        self._certificates: Dict[str, V8UnifiedCertificate] = {}
        self._family_index: Dict[str, List[str]] = {}
        self._role_index: Dict[HardwareRole, List[str]] = {}
        self.settlement_engine = EvidenceAwareSettlementEngine()

    def register(self, cert: V8UnifiedCertificate) -> str:
        """Registers a V8UnifiedCertificate into the store and updates indices."""
        cert_id = cert.certificate_id
        if not cert_id:
            h = hashlib.sha256(json.dumps(cert.to_dict(), sort_keys=True).encode()).hexdigest()[:12].upper()
            cert_id = f"V8_CERT_{h}"
            cert.certificate_id = cert_id

        self._certificates[cert_id] = copy.deepcopy(cert)

        # Index by family
        fam = cert.design_family.lower()
        self._family_index.setdefault(fam, [])
        if cert_id not in self._family_index[fam]:
            self._family_index[fam].append(cert_id)

        # Index by normalized role
        role = cert.root_cause.normalized_role
        self._role_index.setdefault(role, [])
        if cert_id not in self._role_index[role]:
            self._role_index[role].append(cert_id)

        return cert_id

    def get(self, cert_id: str) -> Optional[V8UnifiedCertificate]:
        if cert_id in self._certificates:
            return copy.deepcopy(self._certificates[cert_id])
        return None

    def query_candidates(self,
                          design_family: Optional[str] = None,
                          observed_signals: Optional[List[str]] = None,
                          symptom: Optional[str] = None,
                          only_trusted: bool = True) -> List[Tuple[float, V8UnifiedCertificate]]:
        """
        Retrieves candidate certificates ranked by semantic role compatibility,
        protocol alignment, and signal overlap.
        """
        if design_family:
            candidate_ids = set(self._family_index.get(design_family.lower(), []))
        else:
            candidate_ids = set(self._certificates.keys())

        # Build target signal role map if signals provided
        target_role_map = {}
        if observed_signals:
            target_role_map = SemanticRoleNormalizer.map_signals_to_roles(observed_signals, design_family=design_family)

        scored = []
        for cid in candidate_ids:
            cert = self._certificates[cid]

            # Trust Filter
            if only_trusted and cert.trust_metadata.trust_status != CertificateTrustStatus.TRUSTED:
                continue

            score = 1.0

            # Protocol / Family Alignment
            if design_family and cert.design_family.lower() == design_family.lower():
                score += 3.0

            # Semantic Role Compatibility
            cert_role = cert.root_cause.normalized_role
            if cert_role in target_role_map.values():
                score += 4.0

            # Symptom Similarity
            if symptom and symptom.lower() in cert.mechanism.downstream_symptom.lower():
                score += 2.0

            # Signal Overlap
            if observed_signals:
                c_sigs = set(cert.target_signals)
                t_sigs = set(observed_signals)
                if c_sigs:
                    score += (len(c_sigs & t_sigs) / len(c_sigs)) * 2.0

            scored.append((score, copy.deepcopy(cert)))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def validate_and_decide(self,
                            cert: V8UnifiedCertificate,
                            vcd_path: str,
                            target_id: str = "unknown",
                            observed_signals: Optional[List[str]] = None,
                            rtl_declarations: Optional[Dict[str, Any]] = None) -> V8ValidationReport:
        """
        Executes complete multi-layer validation using the appropriate protocol adapter,
        semantic role normalization, and evidence-aware adaptive settlement.
        """
        import time
        t0 = time.time()

        if not os.path.exists(vcd_path):
            return V8ValidationReport(
                certificate_id=cert.certificate_id,
                target_id=target_id,
                design_family=cert.design_family,
                raw_validator_decision="INSUFFICIENT_EVIDENCE",
                policy_action="FALLBACK_INDEPENDENT_RCA",
                safe_to_reuse=False,
                reused_signal_name=None,
                normalized_role=cert.root_cause.normalized_role,
                decision_reason=f"VCD waveform not found at {vcd_path}",
                settlement_reason=SettlementTerminationReason.INSUFFICIENT_EVIDENCE_TRUNCATED.value,
                effective_window_cycles=0,
                validation_latency_ms=(time.time() - t0) * 1000
            )

        # Parse signals and build cycle states
        all_sigs = list(set((observed_signals or cert.target_signals) + ["clk", "rst_n"]))
        parsed_map = parse_vcd_signals(vcd_path, all_sigs)
        cycle_states = build_cycle_state_table(parsed_map)

        if len(cycle_states) < 3:
            return V8ValidationReport(
                certificate_id=cert.certificate_id,
                target_id=target_id,
                design_family=cert.design_family,
                raw_validator_decision="INSUFFICIENT_EVIDENCE",
                policy_action="FALLBACK_INDEPENDENT_RCA",
                safe_to_reuse=False,
                reused_signal_name=None,
                normalized_role=cert.root_cause.normalized_role,
                decision_reason="Target waveform trace contains fewer than 3 clock cycles.",
                settlement_reason=SettlementTerminationReason.INSUFFICIENT_EVIDENCE_TRUNCATED.value,
                effective_window_cycles=len(cycle_states),
                validation_latency_ms=(time.time() - t0) * 1000
            )

        # Semantic Role Normalization
        signal_role_map = SemanticRoleNormalizer.map_signals_to_roles(
            all_sigs, design_family=cert.design_family, rtl_declarations=rtl_declarations
        )

        # Evidence-Aware Adaptive Settlement Check
        settle_dec = self.settlement_engine.evaluate_settlement(
            cycle_states=cycle_states,
            design_family=cert.design_family,
            trigger_cycle=0,
            signal_role_map=signal_role_map
        )

        # Protocol Adapter Validation
        adapter = ProtocolRegistry.get_adapter(cert.design_family)
        if not adapter:
            return V8ValidationReport(
                certificate_id=cert.certificate_id,
                target_id=target_id,
                design_family=cert.design_family,
                raw_validator_decision="INSUFFICIENT_EVIDENCE",
                policy_action="FALLBACK_INDEPENDENT_RCA",
                safe_to_reuse=False,
                reused_signal_name=None,
                normalized_role=cert.root_cause.normalized_role,
                decision_reason=f"No protocol adapter registered for '{cert.design_family}'.",
                settlement_reason=settle_dec.termination_reason.value,
                effective_window_cycles=settle_dec.effective_window_cycles,
                validation_latency_ms=(time.time() - t0) * 1000
            )

        val_res = adapter.validate_target(
            cert=cert,
            cycle_states=cycle_states[:settle_dec.effective_window_cycles],
            signal_role_map=signal_role_map
        )

        raw_dec = val_res.get("decision", "FAIL")
        matched_sig = val_res.get("matched_root_cause", cert.root_cause.signal_name)
        reason = val_res.get("reason", "Protocol validation failed.")

        # Resolve target signal name if alias exists
        if matched_sig not in all_sigs:
            # Map by role
            for s, r in signal_role_map.items():
                if r == cert.root_cause.normalized_role:
                    matched_sig = s
                    break

        safe_to_reuse = (raw_dec == "PASS")
        policy_action = "REUSE_RCA" if safe_to_reuse else "FALLBACK_INDEPENDENT_RCA"

        return V8ValidationReport(
            certificate_id=cert.certificate_id,
            target_id=target_id,
            design_family=cert.design_family,
            raw_validator_decision=raw_dec,
            policy_action=policy_action,
            safe_to_reuse=safe_to_reuse,
            reused_signal_name=matched_sig if safe_to_reuse else None,
            normalized_role=cert.root_cause.normalized_role,
            decision_reason=reason,
            settlement_reason=settle_dec.termination_reason.value,
            effective_window_cycles=settle_dec.effective_window_cycles,
            validation_latency_ms=(time.time() - t0) * 1000,
            metrics={"adapter": adapter.family_name, "stage": val_res.get("stage", "UNKNOWN")}
        )

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "V8_UNIFIED_1.0",
            "certificates": [c.to_dict() for c in self._certificates.values()]
        }
