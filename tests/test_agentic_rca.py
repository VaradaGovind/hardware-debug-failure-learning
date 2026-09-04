import os
import json
import pytest
from src.agent.llm_provider import MockLLMProvider, LocalOllamaProvider, LLMResponse
from src.tools.agent_tools import AgentToolRegistry
from src.agent.agentic_rca_backend import AgenticRCABackend


class TestAgenticRCA:
    """Test suite for Agentic RCA components and boundaries."""

    def test_mock_llm_provider_generation(self):
        provider = MockLLMProvider()
        resp = provider.generate("Analyze hardware failure.")
        assert resp.model_name == "mock-deterministic"
        assert resp.total_tokens > 0
        assert "failure_summary" in resp.text

    def test_mock_llm_provider_structured_generate(self):
        provider = MockLLMProvider(default_signal="read_ptr")
        data, resp = provider.structured_generate("Task fifo_f1")
        assert isinstance(data, dict)
        assert data.get("candidate_signal") == "read_ptr"
        assert data.get("confidence") == 0.90
        assert resp.latency_ms > 0

    def test_structured_generate_repair_loop(self):
        """Tests that invalid raw text triggers the repair loop."""
        malformed_json = "This is not json {candidate_signal: 'count'}"
        valid_json = '{"candidate_signal": "count", "confidence": 0.85}'
        
        provider = MockLLMProvider(canned_responses={
            "Analyze malformed": malformed_json,
            "[SYSTEM ERROR]": valid_json
        })
        
        data, resp = provider.structured_generate("Analyze malformed")
        assert data.get("candidate_signal") == "count"
        assert data.get("confidence") == 0.85

    def test_agent_tool_registry_path_confinement(self):
        """Verifies directory traversal is prevented."""
        tools = AgentToolRegistry()
        sanitized = tools._sanitize_task_id("../../etc/passwd")
        assert ".." not in sanitized
        assert "/" not in sanitized
        assert sanitized == "passwd"

    def test_agent_tool_read_and_search_rtl(self):
        """Verifies reading and searching valid RTL design files."""
        tools = AgentToolRegistry()
        read_res = tools.read_rtl_file("fifo_f1")
        assert read_res.get("status") == "SUCCESS"
        assert "module" in read_res.get("content", "")

        search_res = tools.search_rtl("fifo_f1", query="always")
        assert search_res.get("status") == "SUCCESS"
        assert search_res.get("total_matches", 0) > 0

    def test_agent_tool_invalid_tool_rejection(self):
        """Verifies unknown tools are safely rejected."""
        tools = AgentToolRegistry()
        res = tools.execute_tool("rm_rf_root", {"task_id": "fifo_f1"})
        assert res.get("status") == "ERROR"
        assert "not permitted" in res.get("error", "")

    def test_agentic_rca_backend_stage_a_direct(self):
        """Tests Stage A direct reasoning with Mock LLM provider."""
        provider = MockLLMProvider(default_signal="count")
        backend = AgenticRCABackend(provider=provider, mode="direct")
        
        metadata = {
            "symptom": "FIFO_UNDERFLOW_VIOLATION",
            "ground_truth_signals": ["count"],
            "initiating_event": "READ_ON_EMPTY",
            "boundary_signals": ["empty", "read_en"]
        }
        
        result = backend.diagnose_failure("fifo_f1", "fifo", metadata)
        assert result.task_id == "fifo_f1"
        assert result.design_family == "fifo"
        assert result.root_cause_signal == "count"
        assert result.is_correct is True
        assert result.llm_calls == 1
        assert result.backend_type == "LIVE_LLM_AGENT_DIRECT"

    def test_agentic_rca_backend_stage_b_tool_assisted(self):
        """Tests Stage B multi-step bounded agent loop with tool invocation and conclusion."""
        step1_tool_call = json.dumps({
            "action": "tool_call",
            "thought": "Need to search RTL for count register assignment.",
            "tool_name": "search_rtl",
            "tool_args": {"task_id": "fifo_f1", "query": "count <="}
        })
        step2_conclude = json.dumps({
            "action": "conclude",
            "thought": "Identified root cause in count decrement underflow condition.",
            "candidate_signal": "count",
            "suspected_root_cause": "Count decrement occurs on empty read.",
            "confidence": 0.95
        })

        provider = MockLLMProvider(canned_responses={
            "Step 1/5": step1_tool_call,
            "Step 2/5": step2_conclude
        })

        backend = AgenticRCABackend(provider=provider, mode="tool_assisted", max_iterations=5)
        metadata = {
            "symptom": "FIFO_UNDERFLOW_VIOLATION",
            "ground_truth_signals": ["count"],
            "boundary_signals": ["empty", "read_en"]
        }

        result = backend.diagnose_failure("fifo_f1", "fifo", metadata)
        assert result.task_id == "fifo_f1"
        assert result.root_cause_signal == "count"
        assert result.is_correct is True
        assert result.steps_taken == 2
        assert result.tool_calls == 1
        assert result.llm_calls == 2
        assert result.backend_type == "LIVE_LLM_AGENT_TOOL_ASSISTED"
        assert result.trajectory_summary["status"] == "SUCCESS"

    def test_agent_loop_max_iterations_enforcement(self):
        """Verifies that an agent looping endlessly is strictly terminated at max_iterations."""
        infinite_tool_call = json.dumps({
            "action": "tool_call",
            "thought": "Still searching...",
            "tool_name": "search_rtl",
            "tool_args": {"task_id": "fifo_f1", "query": "always"}
        })

        provider = MockLLMProvider(canned_responses={
            "Step": infinite_tool_call
        })

        backend = AgenticRCABackend(provider=provider, mode="tool_assisted", max_iterations=3)
        metadata = {
            "symptom": "FIFO_UNDERFLOW_VIOLATION",
            "ground_truth_signals": ["count"]
        }

        result = backend.diagnose_failure("fifo_f1", "fifo", metadata)
        assert result.steps_taken == 3
        assert result.tool_calls == 3
        assert result.llm_calls == 3
        assert result.rca_status == "MAX_ITERATIONS_REACHED"
        assert result.trajectory_summary["status"] == "MAX_ITERATIONS_REACHED"

    def test_invalid_output_exhausted_retries(self):
        """Verifies unrepairable JSON triggers INVALID_OUTPUT status without fake diagnosis."""
        provider = MockLLMProvider(canned_responses={
            "fifo_f1": "Total gibberish text with no JSON anywhere.",
            "[SYSTEM ERROR]": "Still invalid gibberish."
        })
        backend = AgenticRCABackend(provider=provider, mode="direct")
        metadata = {"symptom": "FAIL", "ground_truth_signals": ["count"]}

        result = backend.diagnose_failure("fifo_f1", "fifo", metadata)
        assert result.rca_status == "INVALID_OUTPUT"
        assert result.root_cause_signal == "unknown"
        assert result.is_correct is False

    def test_confidence_range_validation_triggers_repair(self):
        """Verifies invalid confidence range (e.g. 5.0) triggers repair loop."""
        invalid_conf = '{"candidate_signal": "count", "confidence": 5.0}'
        valid_conf = '{"candidate_signal": "count", "confidence": 0.95}'
        provider = MockLLMProvider(canned_responses={
            "Task": invalid_conf,
            "[SYSTEM ERROR]": valid_conf
        })
        data, resp = provider.structured_generate("Task fifo_f1")
        assert data.get("candidate_signal") == "count"
        assert data.get("confidence") == 0.95

    def test_metrics_calculation_paired_records(self):
        """Verifies metric computation across TP, FP, TN, FN cases."""
        from src.evaluation.metrics import compute_rca_vs_reuse_metrics
        mock_records = [
            # Source
            {"is_source_manifestation": True, "ground_truth_match": "MATCH", "baseline_correct": True, "final_reuse_correct": True,
             "baseline_tool_calls": 2, "reuse_tool_calls": 2, "reused_prior_rca": False, "fallback_rca_executed": False, "baseline_wall_clock_ms": 100.0, "reuse_wall_clock_ms": 100.0},
            # TP Reuse
            {"is_source_manifestation": False, "ground_truth_match": "MATCH", "baseline_correct": True, "final_reuse_correct": True,
             "baseline_tool_calls": 2, "reuse_tool_calls": 0, "reused_prior_rca": True, "fallback_rca_executed": False, "baseline_wall_clock_ms": 100.0, "reuse_wall_clock_ms": 10.0},
            # FP Reuse (Unsafe)
            {"is_source_manifestation": False, "ground_truth_match": "MATCH", "baseline_correct": True, "final_reuse_correct": False,
             "baseline_tool_calls": 2, "reuse_tool_calls": 0, "reused_prior_rca": True, "fallback_rca_executed": False, "baseline_wall_clock_ms": 100.0, "reuse_wall_clock_ms": 10.0},
            # TN Fallback (Correct Rejection)
            {"is_source_manifestation": False, "ground_truth_match": "MISMATCH", "baseline_correct": True, "final_reuse_correct": True,
             "baseline_tool_calls": 2, "reuse_tool_calls": 4, "reused_prior_rca": False, "fallback_rca_executed": True, "baseline_wall_clock_ms": 100.0, "reuse_wall_clock_ms": 110.0},
        ]
        stats = compute_rca_vs_reuse_metrics(mock_records)
        assert stats["total_manifestations"] == 4
        assert stats["source_cases"] == 1
        assert stats["target_arrivals"] == 3
        assert stats["successful_reuses"] == 1
        assert stats["unsafe_reuses"] == 1
        assert stats["total_reuses_applied"] == 2
        assert stats["reuse_precision_pct"] == 50.0
        assert stats["negative_rejection_rate_pct"] == 100.0

    def test_metrics_zero_division_safety(self):
        """Verifies that empty streams and zero-reuse scenarios don't crash."""
        from src.evaluation.metrics import compute_rca_vs_reuse_metrics
        empty_stats = compute_rca_vs_reuse_metrics([])
        assert empty_stats["total_manifestations"] == 0

        zero_reuse_records = [
            {"is_source_manifestation": False, "ground_truth_match": "MISMATCH", "baseline_correct": True, "final_reuse_correct": True,
             "baseline_tool_calls": 2, "reuse_tool_calls": 4, "reused_prior_rca": False, "fallback_rca_executed": True, "baseline_wall_clock_ms": 50.0, "reuse_wall_clock_ms": 60.0}
        ]
        stats = compute_rca_vs_reuse_metrics(zero_reuse_records)
        assert stats["successful_reuses"] == 0
        assert stats["reuse_precision_pct"] == 100.0
        assert stats["negative_rejection_rate_pct"] == 100.0

    def test_context_builder_parsing_and_no_leakage(self):
        """Verifies deterministic context extraction and automated zero-leakage enforcement."""
        from src.agent.context_builder import build_rca_context, validate_context_no_leakage
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        meta = {
            "symptom": "DATA_MISMATCH",
            "initiating_event": "SIMULTANEOUS_RW",
            "boundary_signals": ["count", "read_en", "write_en"],
            "ground_truth_signals": ["count"],
            "defect_mechanism": "FIFO_SIMULTANEOUS_RW"
        }
        ctx = build_rca_context("heldout_fifo_src", "fifo", meta, workspace_root)
        assert ctx.module_name == "fifo"
        assert "count" in ctx.internal_signals
        assert "write_en" in [p.split()[-1] for p in ctx.ports]
        assert ctx.char_length > 0
        # Anti-leakage test: context object must not contain ground_truth attributes
        validate_context_no_leakage(ctx)


