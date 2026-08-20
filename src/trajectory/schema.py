import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class ToolResult:
    success: bool
    informative: bool
    evidence_type: str
    relevant_modules: List[str]
    relevant_signals: List[str]
    cycle_range: List[int]

@dataclass
class ActionCost:
    latency_ms: int = 15
    tool_calls: int = 1

@dataclass
class Action:
    action_type: str
    target_module: str = ""
    signals: List[str] = field(default_factory=list)
    cycle_start: int = 0
    cycle_end: int = 0
    hypothesis: str = ""

@dataclass
class TrajectoryStep:
    run_id: str
    step: int
    task_id: str
    design_family: str
    symptom: str
    failure_type: str
    agent: str
    action: str
    target_module: str
    signals: List[str]
    cycle_start: int
    cycle_end: int
    result_type: str
    informative: bool
    hypothesis: str
    cost: Dict[str, int]
    global_outcome: str = "PENDING"

@dataclass
class TrajectorySummary:
    run_id: str
    final_outcome: str
    root_cause_found: bool
    steps: int
    tool_calls: int
    waveform_queries: int
    simulations: int
    false_pruning: int = 0
    exploration_overrides: int = 0
