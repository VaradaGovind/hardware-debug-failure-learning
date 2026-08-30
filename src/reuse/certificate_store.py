import os
import json
import copy
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from .transaction_semantic_certificate import TransactionSemanticCertificate, TransactionContext, ProtocolObligation
from .transaction_semantic_validator import TransactionSemanticValidator
from .adaptive_l2_adapter import AdaptiveL2Adapter
from .adaptive_evidence import AdaptiveEvidenceClassifier, EvidenceSufficiencyResult
from .adaptive_reuse_policy import AdaptiveReusePolicy


@dataclass
class ValidationDecisionReport:
    """Detailed audit report distinguishing all 5 validation and decision layers."""
    certificate_id: str
    target_id: str
    
    # Layer 1: Symptom & Trigger Invariant Matching
    symptom_matched: bool
    trigger_detected: bool
    
    # Layer 2: Transaction Context & Protocol Obligations
    transaction_context_active: bool
    protocol_obligation_violated: bool
    
    # Layer 3: Downstream Causal Propagation & Temporal Ordering
    causal_propagation_confirmed: bool
    temporal_order_valid: bool
    
    # Layer 4: Evidence Sufficiency & Adaptive Boundaries
    sufficiency_state: str  # e.g., "TRANSACTION_COMPLETED_SUFFICIENT", "TRANSACTION_ACCEPTED_INCOMPLETE"
    is_sufficient_evidence: bool
    adaptive_window_cycles: int
    
    # Layer 5: Final Reuse Policy Decision
    raw_validator_decision: str  # "PASS", "FAIL", "INSUFFICIENT_EVIDENCE"
    policy_action: str           # "REUSE_RCA", "FALLBACK_INDEPENDENT_RCA"
    safe_to_reuse: bool
    decision_reason: str
    validation_latency_ms: float
    
    # Detailed diagnostic metrics
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CertificateStore:
    """
    Structured registry for storing, indexing, retrieving, and validating
    Transaction-Semantic Causal Certificates.
    
    Explicitly separates:
      1. Symptom / Invariant similarity
      2. Transaction semantic equivalence
      3. Causal propagation equivalence
      4. Evidence sufficiency & completeness
      5. Final triage decision (REUSE_RCA vs FALLBACK_INDEPENDENT_RCA)
    """

    def __init__(self):
        self._certificates: Dict[str, TransactionSemanticCertificate] = {}
        self._family_index: Dict[str, List[str]] = {}
        self._module_index: Dict[str, List[str]] = {}
        self._symptom_index: Dict[str, List[str]] = {}
        self.adapter = AdaptiveL2Adapter()
        self.policy = AdaptiveReusePolicy()

    def register(self, cert: TransactionSemanticCertificate) -> str:
        """Registers a certificate into the store and updates indices."""
        cert_id = cert.certificate_id
        if not cert_id:
            # Generate a deterministic content hash ID
            cert_id = f"CERT_{hashlib.sha256(json.dumps(cert.to_dict(), sort_keys=True).encode()).hexdigest()[:12].upper()}"
            cert.certificate_id = cert_id

        self._certificates[cert_id] = copy.deepcopy(cert)

        # Index by module
        mod = cert.target_module
        if mod not in self._module_index:
            self._module_index[mod] = []
        if cert_id not in self._module_index[mod]:
            self._module_index[mod].append(cert_id)

        # Index by design family (from metadata or module)
        family = cert.metadata.get("design_family", mod.split("_")[0] if "_" in mod else mod)
        if family not in self._family_index:
            self._family_index[family] = []
        if cert_id not in self._family_index[family]:
            self._family_index[family].append(cert_id)

        # Index by symptom (from metadata)
        symptom = cert.metadata.get("symptom", "unknown")
        if symptom not in self._symptom_index:
            self._symptom_index[symptom] = []
        if cert_id not in self._symptom_index[symptom]:
            self._symptom_index[symptom].append(cert_id)

        return cert_id

    def get(self, cert_id: str) -> Optional[TransactionSemanticCertificate]:
        """Retrieves a certificate by ID."""
        if cert_id in self._certificates:
            return copy.deepcopy(self._certificates[cert_id])
        return None

    def list_certificate_ids(self) -> List[str]:
        """Returns all registered certificate IDs."""
        return list(self._certificates.keys())

    def count(self) -> int:
        """Returns the total number of registered certificates."""
        return len(self._certificates)

    def query_candidates(self,
                         design_family: Optional[str] = None,
                         target_module: Optional[str] = None,
                         symptom: Optional[str] = None,
                         observed_signals: Optional[List[str]] = None) -> List[Tuple[float, TransactionSemanticCertificate]]:
        """
        Retrieves candidate certificates ranked by interface and structural signal overlap.
        
        Returns:
            List of (match_score, certificate) tuples sorted descending by score.
        """
        if design_family:
            candidate_ids = set(self._family_index.get(design_family, []))
        elif target_module:
            candidate_ids = set(self._module_index.get(target_module, []))
        else:
            candidate_ids = set(self._certificates.keys())

        scored_candidates = []
        for cid in candidate_ids:
            cert = self._certificates[cid]
            score = 1.0

            # Boost score if symptom matches metadata
            if symptom and cert.metadata.get("symptom") == symptom:
                score += 2.0

            # Boost score based on signal overlap
            if observed_signals:
                cert_sigs = set(cert.target_signals)
                obs_sigs = set(observed_signals)
                overlap = len(cert_sigs & obs_sigs)
                if cert_sigs:
                    score += (overlap / len(cert_sigs)) * 3.0

            scored_candidates.append((score, copy.deepcopy(cert)))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return scored_candidates

    def validate_and_decide(self, cert: TransactionSemanticCertificate, vcd_path: str,
                            target_id: str = "unknown") -> ValidationDecisionReport:
        """
        Executes complete multi-layer validation of a target waveform against a certificate
        and emits a structured ValidationDecisionReport.
        """
        # Execute adaptive validation
        val_res = self.adapter.validate_adaptive(cert, vcd_path, control_mode="ADAPTIVE_PRIMARY")
        decision_info = self.policy.decide(val_res)
        
        raw_decision = decision_info["raw_decision"]
        policy_action = decision_info["policy_action"]
        safe_to_reuse = decision_info["safe_to_reuse"]
        stage = decision_info["stage"]
        reason = decision_info["reason"]

        adaptive_metrics = val_res.get("adaptive_metrics", {})
        suff_state = adaptive_metrics.get("sufficiency_state", "UNKNOWN")
        window_cycles = adaptive_metrics.get("effective_window_cycles", cert.transaction_context.active_window_cycles)
        latency_ms = adaptive_metrics.get("total_latency_ms", 0.0)

        # Layer 1 & 2 breakdown
        tx_active = stage not in ["PRECHECK", "TRANSACTION_CONTEXT", "TRANSACTION_NEVER_INITIATED"]
        trigger_det = stage not in ["PRECHECK", "TRANSACTION_CONTEXT", "TRIGGER", "TRANSACTION_NEVER_INITIATED"]
        obl_violated = stage not in ["PRECHECK", "TRANSACTION_CONTEXT", "TRIGGER", "PROTOCOL_OBLIGATION", "TRANSACTION_NEVER_INITIATED"]
        causal_prop = stage in ["FULL_TRANSACTION_SEMANTIC"] or (raw_decision == "PASS")
        temporal_valid = stage in ["FULL_TRANSACTION_SEMANTIC"] or (raw_decision == "PASS")
        is_suff = suff_state not in ["TRANSACTION_ACCEPTED_INCOMPLETE", "TRANSACTION_NEVER_INITIATED", "TRANSACTION_BOUNDARIES_AMBIGUOUS"]

        report = ValidationDecisionReport(
            certificate_id=cert.certificate_id,
            target_id=target_id,
            symptom_matched=True,
            trigger_detected=trigger_det,
            transaction_context_active=tx_active,
            protocol_obligation_violated=obl_violated,
            causal_propagation_confirmed=causal_prop,
            temporal_order_valid=temporal_valid,
            sufficiency_state=suff_state,
            is_sufficient_evidence=is_suff,
            adaptive_window_cycles=window_cycles,
            raw_validator_decision=raw_decision,
            policy_action=policy_action,
            safe_to_reuse=safe_to_reuse,
            decision_reason=reason,
            validation_latency_ms=latency_ms,
            metrics={
                "tx_count": val_res.get("tx_count", 0),
                "obligation_violations": val_res.get("obligation_violations", 0),
                "propagation_cycles": val_res.get("propagation_cycles", 0),
                "boundary_recovery_time_ms": adaptive_metrics.get("boundary_recovery_time_ms", 0.0),
                "frozen_l2_time_ms": adaptive_metrics.get("frozen_l2_time_ms", 0.0),
            }
        )
        return report

    def to_json_dict(self) -> Dict[str, Any]:
        """Serializes the entire store into a JSON-compatible dictionary."""
        return {
            "schema_version": "1.0",
            "certificates": [c.to_dict() for c in self._certificates.values()]
        }

    def save_to_file(self, filepath: str) -> None:
        """Saves store to a JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_json_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> 'CertificateStore':
        """Loads store from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        store = cls()
        for c_dict in data.get("certificates", []):
            cert = TransactionSemanticCertificate.from_dict(c_dict)
            store.register(cert)
        return store
