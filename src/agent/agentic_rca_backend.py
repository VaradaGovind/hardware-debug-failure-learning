import os
import json
import time
from typing import Dict, Any, List, Optional
from ..evaluation.rca_vs_reuse_harness import RCABackend, RCADiagnosisResult
from .llm_provider import LLMProvider, LocalOllamaProvider, LLMResponse
from ..tools.agent_tools import AgentToolRegistry
from .context_builder import build_rca_context, format_rca_context_prompt, format_agentic_initial_context, RCAContext


PROMPT_VERSION = "agentic_rca_v4_waveform"

RCA_SYSTEM_PROMPT_STAGE_A = """You are an expert digital hardware verification and root-cause analysis (RCA) engineer.
You are given a failure report from an RTL testbench simulation along with the Verilog design and chronological waveform transitions.
Your job is to identify the suspected root cause signal, the causal mechanism, and the faulty logic location.

CRITICAL HARDWARE RCA RULES:
1. NEVER invent a signal name.
2. Only select a candidate_signal from the explicitly listed candidate signals.
3. Use chronological waveform transitions to determine which signal deviated first or caused the failure.
4. Distinguish observed failure symptoms (e.g. data mismatch, underflow, timeout) from upstream root causes.
5. If the evidence is insufficient to identify the root cause signal with certainty, return "unknown" as the candidate_signal.

You MUST respond ONLY with a valid JSON object matching this schema:
{
  "failure_summary": "<brief description of the observed failure symptom>",
  "suspected_root_cause": "<detailed technical explanation of the causal defect>",
  "root_cause_location": "<verilog module or code block where the bug exists, or unknown>",
  "candidate_signal": "<exact_signal_name_from_candidates_or_unknown>",
  "causal_chain": [
    "<step 1: initiating condition / input transition>",
    "<step 2: internal anomalous transition of root cause signal>",
    "<step 3: resulting observable assertion failure>"
  ],
  "causal_signals": ["<signal_1>", "<signal_2>"],
  "evidence": ["<concrete evidence item 1 from RTL/waveform>"],
  "confidence": 0.85
}
"""

RCA_SYSTEM_PROMPT_STAGE_B = """You are an autonomous hardware verification RCA agent. Investigate failures step-by-step using verification tools before concluding.

Available Tools:
1. read_rtl_file(task_id) - Read Verilog source code.
2. search_rtl(task_id, query) - Search signals/logic in RTL.
3. read_simulation_log(task_id, design_family) - Read simulation assertion log.
4. get_waveform_summary(task_id, signals) - Query signal transitions in waveform.

Respond ONLY with valid JSON matching ONE of these formats:

Format 1 (Tool Call):
{
  "action": "tool_call",
  "thought": "<reason for invoking this tool based on current investigation state>",
  "tool_name": "<tool_name_to_call>",
  "tool_args": {"task_id": "<current_task_id>", "query": "<search_term>"}
}

Format 2 (Conclude Investigation):
{
  "action": "conclude",
  "thought": "<summary of root cause investigation findings>",
  "candidate_signal": "<exact_signal_name_from_candidates_or_unknown>",
  "suspected_root_cause": "<explanation of causal defect mechanism>",
  "root_cause_location": "<verilog module or block where bug exists>",
  "causal_chain": [
    "<step 1: initiating condition / stimulus>",
    "<step 2: internal anomalous transition of root cause signal>",
    "<step 3: resulting observable assertion failure>"
  ],
  "causal_signals": ["<signal_1>"],
  "evidence": ["<concrete evidence item from RTL/waveform>"],
  "confidence": 0.90
}
"""


class AgenticRCABackend(RCABackend):
    """
    Minimal Agentic RCA Backend.
    
    Supports:
    - Stage A: Zero-tool direct structured RCA inference.
    - Stage B: Bounded tool-assisted multi-step autonomous RCA loop.
    """

    def __init__(self,
                 provider: Optional[LLMProvider] = None,
                 mode: str = "tool_assisted",
                 max_iterations: int = 5,
                 max_retries: int = 2,
                 temperature: float = 0.1,
                 max_tokens: int = 512,
                 workspace_root: Optional[str] = None):
        self.provider = provider or LocalOllamaProvider()
        self.mode = mode  # "direct" (Stage A) or "tool_assisted" (Stage B)
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.workspace_root = workspace_root
        self.tools = AgentToolRegistry(workspace_root=workspace_root)

    def diagnose_failure(self, task_id: str, design_family: str,
                         metadata: Dict[str, Any]) -> RCADiagnosisResult:
        """Executes autonomous root-cause analysis for a failing RTL testbench."""
        t0 = time.time()
        
        if self.mode == "direct":
            return self._diagnose_stage_a_direct(task_id, design_family, metadata, t0)
        else:
            return self._diagnose_stage_b_tool_assisted(task_id, design_family, metadata, t0)

    @staticmethod
    def _extract_clean_signal(parsed_json: Dict[str, Any]) -> str:
        """Extracts and sanitizes the candidate signal identifier from model response."""
        cand = str(parsed_json.get("candidate_signal", "")).strip()
        
        # Check if candidate_signal is placeholder phrase or too long
        if not cand or "exact" in cand.lower() or "signal name" in cand.lower() or "<" in cand or len(cand.split()) > 2:
            # Try to grab first valid signal from causal_signals list
            causal = parsed_json.get("causal_signals", [])
            if isinstance(causal, list) and causal:
                for c in causal:
                    c_clean = str(c).strip().strip("\"'.,;:")
                    if c_clean and "<" not in c_clean and len(c_clean.split()) == 1:
                        return c_clean

        # Clean single token
        cand_clean = cand.strip("\"'.,;:").split()[0] if cand else "unknown"
        if "<" in cand_clean or ">" in cand_clean:
            return "unknown"
        return cand_clean if cand_clean else "unknown"

    def _diagnose_stage_a_direct(self, task_id: str, design_family: str,
                                 metadata: Dict[str, Any], t0: float) -> RCADiagnosisResult:
        """Stage A: Non-tool direct structured RCA from deterministic context."""
        rca_ctx = build_rca_context(task_id, design_family, metadata, self.tools.workspace_root)
        prompt = format_rca_context_prompt(rca_ctx)

        parsed_json, resp = self.provider.structured_generate(
            prompt=prompt,
            system_prompt=RCA_SYSTEM_PROMPT_STAGE_A,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            max_retries=self.max_retries
        )

        elapsed_ms = (time.time() - t0) * 1000.0
        
        if "error" in parsed_json or parsed_json.get("status") in ["PARSE_FAILED", "INVALID_OUTPUT", "MODEL_FAILURE"]:
            raw_st = parsed_json.get("status", "")
            status = "MODEL_FAILURE" if raw_st == "MODEL_FAILURE" else "INVALID_OUTPUT"
            candidate_sig = "unknown"
            is_correct = False
        else:
            status = "SUCCESS"
            candidate_sig = self._extract_clean_signal(parsed_json)
            gt_signals = metadata.get("ground_truth_signals", [])
            is_correct = (candidate_sig in gt_signals) if gt_signals else False

        total_tokens = resp.total_tokens

        return RCADiagnosisResult(
            task_id=task_id,
            design_family=design_family,
            root_cause_signal=candidate_sig,
            is_correct=is_correct,
            steps_taken=1,
            tool_calls=1,
            simulations=1,
            waveform_queries=0,
            llm_calls=1,
            llm_tokens=total_tokens,
            backend_type="LIVE_LLM_AGENT_DIRECT",
            wall_clock_ms=elapsed_ms,
            rca_status=status,
            trajectory_summary={
                "status": status,
                "mode": "stage_a_direct",
                "parsed_response": parsed_json,
                "token_accounting": {
                    "prompt_tokens": resp.prompt_tokens,
                    "completion_tokens": resp.completion_tokens,
                    "total_tokens": resp.total_tokens
                }
            },
            notes=f"Direct structured RCA via {self.provider.__class__.__name__} (Status: {status})"
        )

    def _diagnose_stage_b_tool_assisted(self, task_id: str, design_family: str,
                                       metadata: Dict[str, Any], t0: float) -> RCADiagnosisResult:
        """Stage B: Multi-step bounded tool-assisted autonomous RCA agent loop with deterministic initial context."""
        trajectory_steps: List[Dict[str, Any]] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        llm_call_count = 0
        sim_count = 0
        wave_count = 0
        tool_call_count = 0

        # Build initial deterministic context
        rca_ctx = build_rca_context(task_id, design_family, metadata, self.tools.workspace_root)
        conversation_history = format_agentic_initial_context(rca_ctx)

        candidate_sig = "unknown"
        final_diagnosis: Dict[str, Any] = {}
        status = "MAX_ITERATIONS_REACHED"

        for step in range(1, self.max_iterations + 1):
            prompt = (
                f"{conversation_history}\n\n"
                f"[Step {step}/{self.max_iterations}] Decide your next action (tool_call or conclude)."
            )

            parsed_json, resp = self.provider.structured_generate(
                prompt=prompt,
                system_prompt=RCA_SYSTEM_PROMPT_STAGE_B,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                max_retries=self.max_retries
            )

            llm_call_count += 1
            if resp.prompt_tokens >= 0:
                total_prompt_tokens += resp.prompt_tokens
                total_completion_tokens += resp.completion_tokens

            if resp.finish_reason == "error" or parsed_json.get("status") == "MODEL_FAILURE":
                status = "MODEL_FAILURE"
                break

            if parsed_json.get("status") == "PARSE_FAILED" or parsed_json.get("error") == "INVALID_OUTPUT":
                status = "MODEL_OUTPUT_INVALID"
                break

            action = parsed_json.get("action", "conclude")
            
            if action == "conclude" or "candidate_signal" in parsed_json:
                candidate_sig = self._extract_clean_signal(parsed_json)
                final_diagnosis = parsed_json
                if candidate_sig.lower() == "unknown":
                    status = "UNKNOWN"
                else:
                    status = "FINAL_RCA"
                trajectory_steps.append({
                    "step": step,
                    "action": "conclude",
                    "machine_state": status,
                    "thought": parsed_json.get("thought", ""),
                    "candidate_signal": candidate_sig,
                    "confidence": parsed_json.get("confidence", 0.0)
                })
                break

            elif action == "tool_call":
                tool_name = parsed_json.get("tool_name", "")
                tool_args = parsed_json.get("tool_args", {})
                # Ensure task_id is populated
                if "task_id" not in tool_args:
                    tool_args["task_id"] = task_id
                if "design_family" not in tool_args and design_family:
                    tool_args["design_family"] = design_family

                tool_res = self.tools.execute_tool(tool_name, tool_args)
                tool_call_count += 1
                if tool_name == "read_simulation_log":
                    sim_count += 1
                elif tool_name == "get_waveform_summary":
                    wave_count += 1

                tool_summary_str = json.dumps(tool_res)[:450]
                trajectory_steps.append({
                    "step": step,
                    "action": "tool_call",
                    "machine_state": "TOOL_CALL",
                    "thought": parsed_json.get("thought", ""),
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "tool_status": tool_res.get("status", "UNKNOWN")
                })

                # Append tool observation to conversation history for next iteration
                conversation_history += (
                    f"\n\n[Agent Thought]: {parsed_json.get('thought', '')}\n"
                    f"[Tool Call]: {tool_name}({json.dumps(tool_args)})\n"
                    f"[Tool Output]: {tool_summary_str}"
                )
            else:
                # Unrecognized action fallback
                status = "MODEL_OUTPUT_INVALID"
                break

        elapsed_ms = (time.time() - t0) * 1000.0
        gt_signals = metadata.get("ground_truth_signals", [])
        is_correct = (candidate_sig in gt_signals) if (status in ["FINAL_RCA", "SUCCESS"] and gt_signals and candidate_sig != "unknown") else (candidate_sig.lower() == "unknown" and "unknown" in [g.lower() for g in gt_signals])

        total_tokens = (total_prompt_tokens + total_completion_tokens) if total_prompt_tokens > 0 else -1

        # Map back status string for legacy compatibility where needed
        legacy_status = "SUCCESS" if status in ["FINAL_RCA", "UNKNOWN"] else ("INVALID_OUTPUT" if status == "MODEL_OUTPUT_INVALID" else status)

        return RCADiagnosisResult(
            task_id=task_id,
            design_family=design_family,
            root_cause_signal=candidate_sig,
            is_correct=is_correct,
            steps_taken=len(trajectory_steps),
            tool_calls=tool_call_count,
            simulations=sim_count,
            waveform_queries=wave_count,
            llm_calls=llm_call_count,
            llm_tokens=total_tokens,
            backend_type="LIVE_LLM_AGENT_TOOL_ASSISTED",
            wall_clock_ms=elapsed_ms,
            rca_status=legacy_status,
            trajectory_summary={
                "status": legacy_status,
                "machine_state": status,
                "mode": "stage_b_tool_assisted",
                "trajectory_steps": trajectory_steps,
                "final_diagnosis": final_diagnosis,
                "token_accounting": {
                    "prompt_tokens": total_prompt_tokens,
                    "completion_tokens": total_completion_tokens,
                    "total_tokens": total_tokens
                }
            },
            notes=f"Tool-assisted Agentic RCA via {self.provider.__class__.__name__} (Status: {status})"
        )
