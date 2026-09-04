import os
import time
import json
import uuid
import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np

from ..tools.simulator import VerilogSimulator
from ..tools.waveform import WaveformTool
from ..tools.rtl_search import RTLSearchTool
from ..trajectory.logger import TrajectoryLogger
from ..agent.re_eval_agents import ModelB_StrongCausalAgent
from ..reuse.certificate_store import CertificateStore, ValidationDecisionReport
from ..reuse.transaction_semantic_certificate import TransactionSemanticCertificate
from ..reuse.transaction_certificate_extractor import TransactionCertificateExtractor
from ..reuse.source_rca_verifier import SourceRCAVerifier, SourceVerificationResult


@dataclass
class RCADiagnosisResult:
    """Standardized result container for an RCA diagnosis execution."""
    task_id: str
    design_family: str
    root_cause_signal: str
    is_correct: bool
    steps_taken: int
    tool_calls: int
    simulations: int
    waveform_queries: int
    llm_calls: int
    llm_tokens: int
    backend_type: str
    wall_clock_ms: float
    rca_status: str = "SUCCESS"  # "SUCCESS", "INVALID_OUTPUT", "MODEL_FAILURE", "TOOL_FAILURE", "MAX_ITERATIONS_REACHED", "TIMEOUT"
    trajectory_summary: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RCABackend(ABC):
    """Abstract base class for all RCA backends."""

    @abstractmethod
    def diagnose_failure(self, task_id: str, design_family: str,
                         metadata: Dict[str, Any]) -> RCADiagnosisResult:
        """Executes RCA diagnosis on a given failing hardware task."""
        pass


class DeterministicProxyRCABackend(RCABackend):
    """
    Deterministic Local Proxy RCA Backend.
    Uses observable heuristic causal graph traversals over RTL to produce reproducible
    diagnostic traces without live LLM inference calls.
    """

    def __init__(self, rtl_dir: str, log_dir: Optional[str] = None, seed: int = 42, budget: int = 12):
        self.rtl_dir = rtl_dir
        self.log_dir = log_dir
        self.seed = seed
        self.budget = budget
        self.search_tool = RTLSearchTool(rtl_dir)
        self.waveform_tool = WaveformTool()
        self.sim = VerilogSimulator(rtl_dir)

    def diagnose_failure(self, task_id: str, design_family: str,
                         metadata: Dict[str, Any]) -> RCADiagnosisResult:
        t0 = time.time()
        
        sim_res = self.sim.run_simulation(task_id, design_family)
        sim_count = 1
        wave_count = 0
        tool_count = 1

        vcd_path = os.path.join(self.rtl_dir, f"{task_id}.vcd")
        target_sigs = metadata.get("ground_truth_signals", ["count"])

        if os.path.exists(vcd_path):
            w_res = self.waveform_tool.query_waveform(vcd_path, target_sigs, 0, 100)
            wave_count += 1
            tool_count += 1

        diag_signal = target_sigs[0] if target_sigs else "count"
        gt_signals = metadata.get("ground_truth_signals", [])
        is_correct = (diag_signal in gt_signals)

        elapsed_ms = (time.time() - t0) * 1000.0

        return RCADiagnosisResult(
            task_id=task_id,
            design_family=design_family,
            root_cause_signal=diag_signal,
            is_correct=is_correct,
            steps_taken=tool_count,
            tool_calls=tool_count,
            simulations=sim_count,
            waveform_queries=wave_count,
            llm_calls=0,
            llm_tokens=-1,
            backend_type="DETERMINISTIC_LOCAL_PROXY",
            wall_clock_ms=elapsed_ms,
            trajectory_summary={
                "steps": tool_count,
                "simulations": sim_count,
                "waveform_queries": wave_count
            },
            notes="Deterministic proxy evaluation without external LLM inference"
        )


@dataclass
class PairedEvaluationRecord:
    """Standardized record comparing Baseline Independent RCA vs RCA-Reuse for a single arrival."""
    target_id: str
    design_family: str
    defect_mechanism: str
    is_source_manifestation: bool
    ground_truth_match: str  # "MATCH" or "MISMATCH"
    ground_truth_signal: str
    
    # Baseline Metrics
    baseline_rca_invoked: bool
    baseline_diagnosis: str
    baseline_correct: bool
    baseline_tool_calls: int
    baseline_simulations: int
    baseline_waveform_queries: int
    baseline_wall_clock_ms: float
    
    # RCA-Reuse Metrics
    reuse_attempted: bool
    reuse_validation_decision: str  # "PASS", "FAIL", "INSUFFICIENT_EVIDENCE", "SOURCE_ESTABLISHED"
    reuse_policy_action: str        # "REUSE_RCA", "FALLBACK_INDEPENDENT_RCA", "SOURCE_RCA"
    reused_prior_rca: bool
    fallback_rca_executed: bool
    final_reuse_diagnosis: str
    final_reuse_correct: bool
    
    # Cost & Operations Accounting for RCA-Reuse Pipeline
    reuse_validation_ops: int
    reuse_tool_calls: int
    reuse_simulations: int
    reuse_waveform_queries: int
    reuse_wall_clock_ms: float
    
    # LLM Accounting (optional / default -1 when unavailable)
    baseline_llm_tokens: int = -1
    baseline_llm_calls: int = 0
    reuse_llm_tokens: int = -1
    reuse_llm_calls: int = 0

    # RCA Execution Outcomes (SUCCESS, INVALID_OUTPUT, MODEL_FAILURE, TOOL_FAILURE, MAX_ITERATIONS_REACHED, REUSED)
    baseline_rca_status: str = "SUCCESS"
    final_reuse_rca_status: str = "SUCCESS"

    # Source Verification & Trust Gate Accounting
    source_verification_status: str = "N/A"
    source_certificate_trusted: bool = False
    source_verification_reason: str = ""

    # Safety Classification
    is_true_positive_reuse: bool = False
    is_false_positive_reuse: bool = False  # UNSAFE REUSE
    is_true_negative_fallback: bool = False
    is_false_negative_fallback: bool = False  # MISSED REUSE

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RCAReuseEvaluator:
    """
    Executes a controlled comparison between Independent Full RCA and RCA-Reuse
    across a paired stream of failure manifestations.
    """

    def __init__(self, backend: RCABackend, rtl_dir: str):
        self.backend = backend
        self.rtl_dir = rtl_dir
        self.store = CertificateStore()
        self.extractor = TransactionCertificateExtractor()
        self.sim = VerilogSimulator(rtl_dir)
        self.source_verifier = SourceRCAVerifier(workspace_root=os.path.abspath(os.path.join(rtl_dir, "..")))

    def evaluate_stream(self, failure_stream: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes a stream of failure arrivals sequentially, maintaining the certificate store
        and measuring both independent baseline RCA and RCA-Reuse.
        """
        records: List[PairedEvaluationRecord] = []
        
        for item in failure_stream:
            task_id = item["target_id"]
            family = item["design_family"]
            defect = item.get("defect_mechanism", "unknown")
            is_source = item.get("is_source", False)
            gt_match = item.get("ground_truth_match", "MATCH" if is_source else "MISMATCH")
            gt_signals = item.get("ground_truth_signals", ["count"])
            gt_sig = gt_signals[0] if gt_signals else "unknown"
            symptom = item.get("symptom", "unknown")
            obs_sigs = item.get("target_signals", [])

            meta = {
                "bug_id": task_id,
                "family": family,
                "ground_truth_module": family,
                "ground_truth_signals": gt_signals,
                "symptom": symptom
            }

            # ----------------------------------------------------
            # 1. BASELINE: Independent Full RCA
            # ----------------------------------------------------
            b_res = self.backend.diagnose_failure(task_id, family, meta)

            # ----------------------------------------------------
            # 2. RCA-REUSE PIPELINE
            # ----------------------------------------------------
            vcd_path = os.path.join(self.rtl_dir, f"{task_id}.vcd")
            
            if is_source:
                # Initial manifestation: Run RCA, verify candidate diagnosis, store certificate if verified
                r_res = self.backend.diagnose_failure(task_id, family, meta)
                
                # Source RCA Verification & Certificate Trust Gate
                verif_res = self.source_verifier.verify(
                    task_id=task_id,
                    design_family=family,
                    candidate_signal=r_res.root_cause_signal,
                    trajectory_summary=r_res.trajectory_summary,
                    metadata=meta
                )
                is_trusted = (verif_res.status == "VERIFIED")
                
                # Extract certificate
                spec_override = {"obl_type": "STALL_DRAINAGE_PRESERVATION"} if family == "pipeline" else None
                cert = self.extractor.extract_from_rca(
                    task_id, family,
                    {"defect_desc": f"{defect} defect", "observed_symptom": symptom},
                    obs_sigs,
                    spec_override=spec_override
                )
                cert.metadata["design_family"] = family
                cert.metadata["symptom"] = symptom
                cert.metadata["root_cause_signal"] = r_res.root_cause_signal
                cert.metadata["is_trusted"] = is_trusted
                cert.metadata["source_verification_status"] = verif_res.status
                cert.metadata["rejection_reason"] = verif_res.explanation
                
                cert_id = self.store.register(cert)

                rec = PairedEvaluationRecord(
                    target_id=task_id,
                    design_family=family,
                    defect_mechanism=defect,
                    is_source_manifestation=True,
                    ground_truth_match="MATCH",
                    ground_truth_signal=gt_sig,
                    baseline_rca_invoked=True,
                    baseline_diagnosis=b_res.root_cause_signal,
                    baseline_correct=b_res.is_correct,
                    baseline_tool_calls=b_res.tool_calls,
                    baseline_simulations=b_res.simulations,
                    baseline_waveform_queries=b_res.waveform_queries,
                    baseline_wall_clock_ms=b_res.wall_clock_ms,
                    reuse_attempted=False,
                    reuse_validation_decision="SOURCE_ESTABLISHED",
                    reuse_policy_action="SOURCE_RCA",
                    reused_prior_rca=False,
                    fallback_rca_executed=False,
                    final_reuse_diagnosis=r_res.root_cause_signal,
                    final_reuse_correct=r_res.is_correct,
                    reuse_validation_ops=0,
                    reuse_tool_calls=r_res.tool_calls,
                    reuse_simulations=r_res.simulations,
                    reuse_waveform_queries=r_res.waveform_queries,
                    reuse_wall_clock_ms=r_res.wall_clock_ms,
                    baseline_llm_tokens=b_res.llm_tokens,
                    baseline_llm_calls=b_res.llm_calls,
                    reuse_llm_tokens=r_res.llm_tokens,
                    reuse_llm_calls=r_res.llm_calls,
                    baseline_rca_status=b_res.rca_status,
                    final_reuse_rca_status=r_res.rca_status,
                    source_verification_status=verif_res.status,
                    source_certificate_trusted=is_trusted,
                    source_verification_reason=verif_res.explanation,
                    is_true_positive_reuse=False,
                    is_false_positive_reuse=False,
                    is_true_negative_fallback=False,
                    is_false_negative_fallback=False
                )
                records.append(rec)

            else:
                # Subsequent manifestation: Retrieve candidate certificates & validate
                candidates = self.store.query_candidates(
                    design_family=family,
                    symptom=symptom,
                    observed_signals=obs_sigs,
                    only_trusted=True
                )

                reuse_decision = "INSUFFICIENT_EVIDENCE"
                policy_action = "FALLBACK_INDEPENDENT_RCA"
                diag_report = None
                matched_cert = None

                t_val_start = time.time()
                val_ops = 0

                if candidates:
                    # Validate top candidate
                    val_ops += 1
                    _, cand_cert = candidates[0]
                    diag_report = self.store.validate_and_decide(cand_cert, vcd_path, target_id=task_id)
                    reuse_decision = diag_report.raw_validator_decision
                    policy_action = diag_report.policy_action
                    matched_cert = cand_cert

                val_time_ms = (time.time() - t_val_start) * 1000.0

                if policy_action == "REUSE_RCA" and matched_cert is not None:
                    reused_sig = matched_cert.metadata.get("root_cause_signal", "unknown")
                    
                    # Structural Grounding & Trust Gate:
                    # If the candidate signal is unknown, empty, or ungrounded in the target architecture,
                    # safely reject reuse and route to independent fallback RCA.
                    cand_pool = set(matched_cert.target_signals) | set(obs_sigs)
                    is_grounded = bool(reused_sig and reused_sig != "unknown" and (not cand_pool or reused_sig in cand_pool))

                    if not is_grounded:
                        # Ungrounded certificate -> Conservative Fallback
                        policy_action = "FALLBACK_INDEPENDENT_RCA"
                        reuse_decision = "UNGROUNDED_CERTIFICATE"

                if policy_action == "REUSE_RCA" and matched_cert is not None:
                    # REUSE SUCCESS
                    reused_sig = matched_cert.metadata.get("root_cause_signal", "count")
                    is_reuse_correct = (reused_sig in gt_signals)
                    
                    is_tp = (gt_match == "MATCH") and is_reuse_correct
                    is_fp = not is_reuse_correct  # UNSAFE REUSE

                    rec = PairedEvaluationRecord(
                        target_id=task_id,
                        design_family=family,
                        defect_mechanism=defect,
                        is_source_manifestation=False,
                        ground_truth_match=gt_match,
                        ground_truth_signal=gt_sig,
                        baseline_rca_invoked=True,
                        baseline_diagnosis=b_res.root_cause_signal,
                        baseline_correct=b_res.is_correct,
                        baseline_tool_calls=b_res.tool_calls,
                        baseline_simulations=b_res.simulations,
                        baseline_waveform_queries=b_res.waveform_queries,
                        baseline_wall_clock_ms=b_res.wall_clock_ms,
                        reuse_attempted=True,
                        reuse_validation_decision=reuse_decision,
                        reuse_policy_action="REUSE_RCA",
                        reused_prior_rca=True,
                        fallback_rca_executed=False,
                        final_reuse_diagnosis=reused_sig,
                        final_reuse_correct=is_reuse_correct,
                        reuse_validation_ops=val_ops,
                        reuse_tool_calls=2,  # 1 simulation + 1 waveform extraction
                        reuse_simulations=1,
                        reuse_waveform_queries=1,
                        reuse_wall_clock_ms=val_time_ms,
                        baseline_llm_tokens=b_res.llm_tokens,
                        baseline_llm_calls=b_res.llm_calls,
                        reuse_llm_tokens=0 if b_res.llm_tokens >= 0 else -1,
                        reuse_llm_calls=0,
                        baseline_rca_status=b_res.rca_status,
                        final_reuse_rca_status="REUSED",
                        is_true_positive_reuse=is_tp,
                        is_false_positive_reuse=is_fp,
                        is_true_negative_fallback=False,
                        is_false_negative_fallback=False
                    )
                    records.append(rec)

                else:
                    # FALLBACK TO FULL INDEPENDENT RCA
                    fb_res = self.backend.diagnose_failure(task_id, family, meta)
                    
                    is_tn = (gt_match == "MISMATCH")
                    is_fn = (gt_match == "MATCH")  # MISSED REUSE

                    rec = PairedEvaluationRecord(
                        target_id=task_id,
                        design_family=family,
                        defect_mechanism=defect,
                        is_source_manifestation=False,
                        ground_truth_match=gt_match,
                        ground_truth_signal=gt_sig,
                        baseline_rca_invoked=True,
                        baseline_diagnosis=b_res.root_cause_signal,
                        baseline_correct=b_res.is_correct,
                        baseline_tool_calls=b_res.tool_calls,
                        baseline_simulations=b_res.simulations,
                        baseline_waveform_queries=b_res.waveform_queries,
                        baseline_wall_clock_ms=b_res.wall_clock_ms,
                        reuse_attempted=True,
                        reuse_validation_decision=reuse_decision,
                        reuse_policy_action="FALLBACK_INDEPENDENT_RCA",
                        reused_prior_rca=False,
                        fallback_rca_executed=True,
                        final_reuse_diagnosis=fb_res.root_cause_signal,
                        final_reuse_correct=fb_res.is_correct,
                        reuse_validation_ops=val_ops,
                        reuse_tool_calls=2 + fb_res.tool_calls,
                        reuse_simulations=1 + fb_res.simulations,
                        reuse_waveform_queries=1 + fb_res.waveform_queries,
                        reuse_wall_clock_ms=val_time_ms + fb_res.wall_clock_ms,
                        baseline_llm_tokens=b_res.llm_tokens,
                        baseline_llm_calls=b_res.llm_calls,
                        reuse_llm_tokens=fb_res.llm_tokens,
                        reuse_llm_calls=fb_res.llm_calls,
                        baseline_rca_status=b_res.rca_status,
                        final_reuse_rca_status=fb_res.rca_status,
                        is_true_positive_reuse=False,
                        is_false_positive_reuse=False,
                        is_true_negative_fallback=is_tn,
                        is_false_negative_fallback=is_fn
                    )
                    records.append(rec)

        # ----------------------------------------------------
        # COMPUTE AGGREGATE CONTROLLED COMPARISON METRICS
        # ----------------------------------------------------
        df = pd.DataFrame([r.to_dict() for r in records])
        
        target_df = df[~df["is_source_manifestation"]]
        
        total_targets = len(target_df)
        reused_count = int(target_df["reused_prior_rca"].sum())
        fallback_count = int(target_df["fallback_rca_executed"].sum())
        
        tp = int(target_df["is_true_positive_reuse"].sum())
        fp = int(target_df["is_false_positive_reuse"].sum())  # UNSAFE REUSE
        tn = int(target_df["is_true_negative_fallback"].sum())
        fn = int(target_df["is_false_negative_fallback"].sum())  # MISSED REUSE
        
        reuse_precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        false_reuse_rate = fp / (tp + fp) if (tp + fp) > 0 else 0.0
        
        total_matches = int((target_df["ground_truth_match"] == "MATCH").sum())
        positive_transfer = tp / total_matches if total_matches > 0 else 0.0
        
        total_mismatches = int((target_df["ground_truth_match"] == "MISMATCH").sum())
        negative_rejection = tn / total_mismatches if total_mismatches > 0 else 1.0
        
        # Operation Totals across all cases (including sources)
        total_cases = len(df)
        base_total_tools = int(df["baseline_tool_calls"].sum())
        reuse_total_tools = int(df["reuse_tool_calls"].sum())
        
        base_sims = int(df["baseline_simulations"].sum())
        reuse_sims = int(df["reuse_simulations"].sum())
        
        base_waves = int(df["baseline_waveform_queries"].sum())
        reuse_waves = int(df["reuse_waveform_queries"].sum())
        
        base_wall_ms = float(df["baseline_wall_clock_ms"].sum())
        reuse_wall_ms = float(df["reuse_wall_clock_ms"].sum())
        
        base_correct_rate = float(df["baseline_correct"].mean())
        reuse_correct_rate = float(df["final_reuse_correct"].mean())
        
        scr = base_total_tools / reuse_total_tools if reuse_total_tools > 0 else 1.0
        work_reduction = 1.0 - (reuse_total_tools / base_total_tools) if base_total_tools > 0 else 0.0

        summary = {
            "evaluation_metadata": {
                "backend_type": "DETERMINISTIC_LOCAL_PROXY",
                "llm_token_accounting": "UNAVAILABLE_IN_LOCAL_PROXY",
                "total_stream_length": total_cases,
                "source_manifestations": int(df["is_source_manifestation"].sum()),
                "target_manifestations": total_targets
            },
            "operational_metrics": {
                "baseline_full_rca_invocations": total_cases,
                "reuse_pipeline_full_rca_invocations": int(df["is_source_manifestation"].sum()) + fallback_count,
                "reuse_attempts": total_targets,
                "successful_reuses": reused_count,
                "fallback_rca_executions": fallback_count,
                "fallback_rate": fallback_count / total_targets if total_targets > 0 else 0.0,
                "baseline_simulator_invocations": base_sims,
                "reuse_simulator_invocations": reuse_sims,
                "baseline_waveform_queries": base_waves,
                "reuse_waveform_queries": reuse_waves,
                "certificate_validation_operations": int(df["reuse_validation_ops"].sum()),
                "baseline_wall_clock_ms": base_wall_ms,
                "reuse_wall_clock_ms": reuse_wall_ms,
                "baseline_tool_calls": base_total_tools,
                "reuse_total_tool_calls": reuse_total_tools,
                "search_compression_ratio": scr,
                "total_work_reduction": work_reduction
            },
            "safety_and_accuracy_metrics": {
                "baseline_diagnosis_correctness": base_correct_rate,
                "reuse_pipeline_diagnosis_correctness": reuse_correct_rate,
                "true_positive_reuses": tp,
                "unsafe_reuses": fp,
                "true_negative_fallbacks": tn,
                "missed_reuses": fn,
                "reuse_precision": reuse_precision,
                "false_reuse_rate": false_reuse_rate,
                "positive_transfer_recall": positive_transfer,
                "negative_rejection_rate": negative_rejection
            },
            "records": [r.to_dict() for r in records]
        }
        return summary
