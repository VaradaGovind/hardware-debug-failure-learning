import os
import json
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from .v8_unified_certificate import (
    V8UnifiedCertificate, CertificateTrustStatus,
    TrustAuditMetadata
)
from .v8_protocol_adapters import ProtocolRegistry
from .source_rca_verifier import SourceRCAVerifier, SourceVerificationResult


class IngestionStatus(str):
    SUCCESS = "SUCCESS"
    MODEL_OUTPUT_INVALID = "MODEL_OUTPUT_INVALID"
    RCA_UNKNOWN = "RCA_UNKNOWN"
    CERTIFICATE_REJECTED = "CERTIFICATE_REJECTED"
    ADAPTER_NOT_FOUND = "ADAPTER_NOT_FOUND"


@dataclass
class IngestionResult:
    """Audit report for deterministic source RCA memory ingestion."""
    status: IngestionStatus
    source_case_id: str
    design_family: str
    candidate_signal: str
    is_trusted: bool
    explanation: str
    certificate: Optional[V8UnifiedCertificate] = None
    verification_audit: Optional[SourceVerificationResult] = None
    raw_response_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": str(self.status),
            "source_case_id": self.source_case_id,
            "design_family": self.design_family,
            "candidate_signal": self.candidate_signal,
            "is_trusted": self.is_trusted,
            "explanation": self.explanation,
            "certificate_id": self.certificate.certificate_id if self.certificate else None,
            "verification_status": self.verification_audit.status if self.verification_audit else None
        }


class DeterministicSourceIngestion:
    """
    Robust, Deterministic Source RCA Memory Ingestion Pipeline.
    
    Guarantees:
    1. Deterministic memory registration from verified baseline RCA traces, eliminating
       stochastic duplicate generation parse failures.
    2. Explicit discrimination between MODEL_OUTPUT_INVALID, RCA_UNKNOWN, and CERTIFICATE_REJECTED.
    3. Malformed outputs are never silently converted into valid or trusted certificates.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.source_verifier = SourceRCAVerifier(workspace_root=self.workspace_root)

    def ingest_source_manifestation(self,
                                    source_case_id: str,
                                    design_family: str,
                                    metadata: Dict[str, Any],
                                    baseline_diagnosis: Optional[str] = None,
                                    baseline_status: str = "SUCCESS",
                                    baseline_confidence: float = 0.9,
                                    trajectory_summary: Optional[Dict[str, Any]] = None,
                                    raw_model_response: Optional[str] = None) -> IngestionResult:
        """
        Deterministically evaluates and ingests a source RCA manifestation into a V8UnifiedCertificate.
        """
        defect_desc = metadata.get("defect_desc", f"{design_family} hardware failure")
        symptom = metadata.get("symptom", "Testbench assertion failure")
        target_signals = metadata.get("target_signals", [])

        # ---------------------------------------------------------------------
        # 1. Deterministic Status Discrimination
        # ---------------------------------------------------------------------
        if baseline_status in ["INVALID_OUTPUT", "MODEL_FAILURE", "PARSE_FAILED"]:
            return IngestionResult(
                status=IngestionStatus.MODEL_OUTPUT_INVALID,
                source_case_id=source_case_id,
                design_family=design_family,
                candidate_signal="invalid",
                is_trusted=False,
                explanation="Model output was malformed or failed JSON parsing. Rejection preserved without silent conversion to unknown.",
                raw_response_text=raw_model_response or ""
            )

        cand_sig = (baseline_diagnosis or "unknown").strip().lower()

        if cand_sig in ["unknown", "none", "null", ""]:
            return IngestionResult(
                status=IngestionStatus.RCA_UNKNOWN,
                source_case_id=source_case_id,
                design_family=design_family,
                candidate_signal="unknown",
                is_trusted=False,
                explanation="Source RCA explicitly abstained or returned unknown due to insufficient evidence."
            )

        # ---------------------------------------------------------------------
        # 2. V5 Deterministic Multi-Layer Verification Gate
        # ---------------------------------------------------------------------
        verif_res = self.source_verifier.verify(
            task_id=source_case_id,
            design_family=design_family,
            candidate_signal=cand_sig,
            trajectory_summary=trajectory_summary or {},
            metadata=metadata
        )

        if verif_res.status != "VERIFIED":
            return IngestionResult(
                status=IngestionStatus.CERTIFICATE_REJECTED,
                source_case_id=source_case_id,
                design_family=design_family,
                candidate_signal=cand_sig,
                is_trusted=False,
                explanation=f"Source verifier rejected candidate '{cand_sig}': {verif_res.explanation}",
                verification_audit=verif_res
            )

        # ---------------------------------------------------------------------
        # 3. Protocol Adapter Retrieval & Unified Certificate Extraction
        # ---------------------------------------------------------------------
        adapter = ProtocolRegistry.get_adapter(design_family)
        if not adapter:
            return IngestionResult(
                status=IngestionStatus.ADAPTER_NOT_FOUND,
                source_case_id=source_case_id,
                design_family=design_family,
                candidate_signal=cand_sig,
                is_trusted=False,
                explanation=f"No protocol adapter registered for hardware family '{design_family}'."
            )

        cert = adapter.extract_certificate_specs(
            source_id=source_case_id,
            defect_desc=defect_desc,
            symptom=symptom,
            signals=target_signals,
            root_sig=cand_sig,
            confidence=baseline_confidence
        )

        cert.trust_metadata = TrustAuditMetadata(
            trust_status=CertificateTrustStatus.TRUSTED,
            source_rca_confidence=baseline_confidence,
            verifier_rule_verdict=verif_res.status,
            verifier_explanation=verif_res.explanation,
            evidence_completeness_score=1.0
        )
        cert.metadata["is_trusted"] = True
        cert.metadata["root_cause_signal"] = cand_sig
        cert.metadata["design_family"] = design_family
        cert.metadata["symptom"] = symptom

        return IngestionResult(
            status=IngestionStatus.SUCCESS,
            source_case_id=source_case_id,
            design_family=design_family,
            candidate_signal=cand_sig,
            is_trusted=True,
            explanation=f"Source RCA successfully verified and ingested as trusted V8 certificate: {verif_res.explanation}",
            certificate=cert,
            verification_audit=verif_res
        )
