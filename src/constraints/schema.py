from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class NegativeConstraint:
    constraint_id: str
    context: Dict[str, str]
    pattern: Dict[str, str]
    effect: str = "DEPRIORITIZE" # BLOCK, DEPRIORITIZE, WARN
    confidence: float = 0.0
    support_count: int = 0
    false_positive_count: int = 0
    source_runs: List[str] = field(default_factory=list)
