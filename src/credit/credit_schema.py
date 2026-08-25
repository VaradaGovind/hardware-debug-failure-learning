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
    
    credit_uniform: float = 0.0
    credit_final_step: float = 0.0
    credit_evidence: float = 0.0
    credit_generic_cf: float = 0.0
    credit_generic_context_cf: float = 0.0
    credit_eda_grounded_cf: float = 0.0
    
    structural_relevance: float = 0.0
    behavioral_relevance: float = 0.0
    temporal_relevance: float = 0.0
    
    oracle_criticality: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__
