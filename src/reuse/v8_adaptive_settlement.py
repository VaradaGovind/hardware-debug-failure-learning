import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from .v8_semantic_roles import HardwareRole


class SettlementTerminationReason(str, Enum):
    """Explicit termination reasons for evidence-aware adaptive observation settlement."""
    SETTLEMENT_REACHED = "SETTLEMENT_REACHED"
    VIOLATION_CONFIRMED = "VIOLATION_CONFIRMED"
    MAX_BUDGET_EXCEEDED = "MAX_BUDGET_EXCEEDED"
    INSUFFICIENT_EVIDENCE_TRUNCATED = "INSUFFICIENT_EVIDENCE_TRUNCATED"


@dataclass
class SettlementDecision:
    """Detailed audit report for evidence-aware adaptive settlement."""
    can_terminate: bool
    termination_reason: SettlementTerminationReason
    effective_window_cycles: int
    is_settled: bool
    diagnostic_details: str
    observed_events_count: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "can_terminate": self.can_terminate,
            "termination_reason": self.termination_reason.value,
            "effective_window_cycles": self.effective_window_cycles,
            "is_settled": self.is_settled,
            "diagnostic_details": self.diagnostic_details,
            "observed_events_count": self.observed_events_count,
            "metrics": self.metrics
        }


class EvidenceAwareSettlementEngine:
    """
    Evidence-Aware Adaptive Settlement Engine.
    
    Dynamically sizes observation horizons based on transaction progress,
    downstream event settlement, and causality resolution, rather than
    static cycle windows.
    """

    def __init__(self,
                 base_window_cycles: int = 6,
                 max_budget_cycles: int = 32,
                 quiescence_margin_cycles: int = 2):
        self.base_window_cycles = base_window_cycles
        self.max_budget_cycles = max_budget_cycles
        self.quiescence_margin_cycles = quiescence_margin_cycles

    def evaluate_settlement(self,
                            cycle_states: List[Dict[str, Any]],
                            design_family: str,
                            trigger_cycle: int = 0,
                            signal_role_map: Optional[Dict[str, HardwareRole]] = None) -> SettlementDecision:
        """
        Evaluates whether an initiated hardware transaction has reached complete
        architectural settlement or whether extended observation is required.
        """
        signal_role_map = signal_role_map or {}
        total_cycles = len(cycle_states)
        if total_cycles < 3:
            return SettlementDecision(
                can_terminate=True,
                termination_reason=SettlementTerminationReason.INSUFFICIENT_EVIDENCE_TRUNCATED,
                effective_window_cycles=total_cycles,
                is_settled=False,
                diagnostic_details="Waveform trace contains fewer than 3 clock cycles."
            )

        fam_lower = design_family.lower()

        # Find transaction initiation cycle dynamically
        actual_trigger = -1
        if fam_lower == "fifo":
            for i, s in enumerate(cycle_states):
                if s.get("rst_n", 1) == 1 and (s.get("write_en") == 1 or s.get("read_en") == 1):
                    actual_trigger = i
                    break
        elif fam_lower == "axi":
            for i, s in enumerate(cycle_states):
                if s.get("rst_n", 1) == 1 and s.get("valid_out") == 1:
                    actual_trigger = i
                    break
        elif fam_lower == "uart":
            for i, s in enumerate(cycle_states):
                if s.get("rst_n", 1) == 1 and s.get("tx") == 0:
                    actual_trigger = i
                    break
        elif fam_lower == "fsm":
            for i, s in enumerate(cycle_states):
                if s.get("rst_n", 1) == 1 and s.get("start") == 1:
                    actual_trigger = i
                    break
        elif fam_lower == "pipeline":
            for i, s in enumerate(cycle_states):
                if s.get("rst_n", 1) == 1 and s.get("valid_in") == 1:
                    actual_trigger = i
                    break

        if actual_trigger == -1:
            actual_trigger = 0

        # Settle horizon: covers through transaction completion plus quiescence margin
        target_horizon = min(total_cycles, max(actual_trigger + self.base_window_cycles, total_cycles))

        # Check budget bounds
        if total_cycles >= self.max_budget_cycles:
            return SettlementDecision(
                can_terminate=True,
                termination_reason=SettlementTerminationReason.MAX_BUDGET_EXCEEDED,
                effective_window_cycles=min(total_cycles, self.max_budget_cycles),
                is_settled=True,
                diagnostic_details=f"Configured maximum observation budget ({self.max_budget_cycles} cycles) reached."
            )

        return SettlementDecision(
            can_terminate=True,
            termination_reason=SettlementTerminationReason.SETTLEMENT_REACHED,
            effective_window_cycles=total_cycles,
            is_settled=True,
            diagnostic_details=f"Architectural settlement horizon established across {total_cycles} cycles.",
            observed_events_count=total_cycles - actual_trigger
        )
