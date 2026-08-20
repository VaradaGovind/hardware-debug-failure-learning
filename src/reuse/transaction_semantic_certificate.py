import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class TransactionContext:
    transaction_type: str        # e.g. "CONTROL_STIMULUS", "PIPELINE_FLOW", "HANDSHAKE_TRANSFER", "FIFO_STREAM"
    initiating_event: Dict[str, Any]  # Triggering transition event
    boundary_signals: List[str]  # Signals defining transaction scope
    active_window_cycles: int = 4

@dataclass
class ProtocolObligation:
    obligation_type: str         # e.g. "STATE_TRANSITION_OBLIGATION", "FORWARDING_HAZARD_RESOLUTION", "STALL_DRAINAGE_PRESERVATION", "HANDSHAKE_HOLD"
    initiating_condition: Dict[str, Any]
    required_contract: Dict[str, Any]  # What legitimate protocol semantics require
    violation_signature: Dict[str, Any] # What the specific causal defect produces
    temporal_latency: int = 1

@dataclass
class TransactionSemanticCertificate:
    certificate_id: str
    source_failure: str
    target_module: str
    target_signals: List[str]
    defect_mechanism: str
    transaction_context: TransactionContext
    trigger_spec: Dict[str, Any]
    protocol_obligation: ProtocolObligation
    state_invariant_spec: Dict[str, Any]
    causal_propagation_spec: Dict[str, Any]
    temporal_constraint: Dict[str, Any]
    expected_observable_consequence: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionSemanticCertificate':
        ctx_data = data.pop("transaction_context")
        obl_data = data.pop("protocol_obligation")
        ctx = TransactionContext(**ctx_data) if isinstance(ctx_data, dict) else ctx_data
        obl = ProtocolObligation(**obl_data) if isinstance(obl_data, dict) else obl_data
        return cls(transaction_context=ctx, protocol_obligation=obl, **data)
