from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class ActionCredit:
    run_id: str
    task_id: str
    step_num: int
    action_type: str
    target_module: str
    signals: List[str]
    cycle_start: int
    cycle_end: int
    
    original_reward: float
    counterfactual_reward: float
    
    # Method scores
    credit_uniform: float = 0.0
    credit_final_step: float = 0.0
    credit_evidence: float = 0.0
    credit_generic_cf: float = 0.0
    credit_generic_context_cf: float = 0.0
    credit_eda_grounded_cf: float = 0.0
    
    # EDA Semantics for Method 6
    structural_relevance: float = 0.0
    behavioral_relevance: float = 0.0
    temporal_relevance: float = 0.0
    
    # Oracle Ground Truth (for evaluation only)
    oracle_criticality: str = "unknown"  # "critical", "non-critical", "misleading"

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__
