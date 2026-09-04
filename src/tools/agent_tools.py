import os
import re
from typing import Dict, Any, List, Optional
from src.tools.simulator import VerilogSimulator
from src.tools.waveform import WaveformTool


class AgentToolRegistry:
    """
    Sandboxed Tool Registry for Agentic RCA.
    Enforces strict path confinement, argument validation, and output bounding.
    """

    ALLOWED_TOOLS = [
        "read_rtl_file",
        "search_rtl",
        "read_simulation_log",
        "inspect_failure",
        "get_waveform_summary"
    ]

    def __init__(self, workspace_root: Optional[str] = None, max_output_chars: int = 4000):
        if workspace_root is None:
            # Anchor to repository root
            workspace_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
        self.workspace_root = os.path.abspath(workspace_root)
        self.rtl_dir = os.path.join(self.workspace_root, "rtl")
        self.designs_dir = os.path.join(self.rtl_dir, "designs")
        self.testbenches_dir = os.path.join(self.rtl_dir, "testbenches")
        self.max_output_chars = max_output_chars
        
        self.simulator = VerilogSimulator(self.rtl_dir)
        self.waveform_tool = WaveformTool()

    def _sanitize_task_id(self, task_id: str) -> str:
        """Sanitizes task identifier to prevent path traversal."""
        clean = os.path.basename(task_id.strip())
        clean = re.sub(r"[^a-zA-Z0-9_\-]", "", clean)
        return clean

    def read_rtl_file(self, task_id: str) -> Dict[str, Any]:
        """Reads RTL source file for a given task, safely confined to rtl/designs/."""
        safe_id = self._sanitize_task_id(task_id)
        rtl_path = os.path.join(self.designs_dir, f"{safe_id}.v")
        
        if not os.path.exists(rtl_path):
            return {
                "status": "ERROR",
                "message": f"RTL file not found for task '{safe_id}' at {rtl_path}",
                "content": ""
            }

        try:
            with open(rtl_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            truncated = False
            if len(content) > self.max_output_chars:
                content = content[:self.max_output_chars] + "\n... [TRUNCATED DUE TO SIZE LIMIT]"
                truncated = True

            return {
                "status": "SUCCESS",
                "task_id": safe_id,
                "lines": len(content.splitlines()),
                "truncated": truncated,
                "content": content
            }
        except Exception as e:
            return {"status": "ERROR", "message": f"Failed to read RTL file: {str(e)}", "content": ""}

    def search_rtl(self, task_id: str, query: str) -> Dict[str, Any]:
        """Searches RTL code for a keyword or regex pattern with bounded context."""
        safe_id = self._sanitize_task_id(task_id)
        rtl_path = os.path.join(self.designs_dir, f"{safe_id}.v")
        
        if not os.path.exists(rtl_path):
            return {
                "status": "ERROR",
                "message": f"RTL file not found for task '{safe_id}'",
                "matches": []
            }

        if not query or len(query) > 100:
            return {"status": "ERROR", "message": "Invalid search query string", "matches": []}

        try:
            with open(rtl_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            pattern = re.compile(query, re.IGNORECASE)
            matches = []
            for idx, line in enumerate(lines, start=1):
                if pattern.search(line):
                    start = max(1, idx - 2)
                    end = min(len(lines), idx + 2)
                    context_snippet = [
                        f"{i:4d}: {lines[i-1].rstrip()}" for i in range(start, end + 1)
                    ]
                    matches.append({
                        "line_number": idx,
                        "line": line.strip(),
                        "context": "\n".join(context_snippet)
                    })
                    if len(matches) >= 10:
                        break

            return {
                "status": "SUCCESS",
                "task_id": safe_id,
                "query": query,
                "total_matches": len(matches),
                "matches": matches
            }
        except Exception as e:
            return {"status": "ERROR", "message": f"Search failed: {str(e)}", "matches": []}

    def read_simulation_log(self, task_id: str, design_family: str = "") -> Dict[str, Any]:
        """Runs the simulator and returns bounded simulation log output."""
        safe_id = self._sanitize_task_id(task_id)
        
        try:
            res = self.simulator.run_simulation(
                task_id=safe_id,
                family=design_family
            )
            stdout_text = res.get("output", "")
            stderr_text = res.get("error", "")
            full_log = (stdout_text + "\n" + stderr_text).strip()
            
            if len(full_log) > self.max_output_chars:
                full_log = full_log[-self.max_output_chars:] + "\n... [TRUNCATED - DISPLAYING RECENT LOG]"

            return {
                "status": "SUCCESS" if res.get("compiled") else "COMPILE_FAILED",
                "task_id": safe_id,
                "simulation_status": "COMPILED" if res.get("compiled") else "FAILED",
                "log": full_log,
                "vcd_path": res.get("vcd_path", "")
            }
        except Exception as e:
            return {"status": "ERROR", "message": f"Simulation execution failed: {str(e)}", "log": ""}

    def inspect_failure(self, task_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Returns structured symptom and contract metadata for a failure task."""
        safe_id = self._sanitize_task_id(task_id)
        meta = metadata or {}
        
        return {
            "status": "SUCCESS",
            "task_id": safe_id,
            "symptom": meta.get("symptom", "HARDWARE_ASSERTION_FAILED"),
            "design_family": meta.get("design_family", "generic"),
            "suspected_module": meta.get("suspected_module", safe_id),
            "initiating_event": meta.get("initiating_event", "RESET_DEASSERTION"),
            "boundary_signals": meta.get("boundary_signals", [])
        }

    def get_waveform_summary(self, task_id: str, signals: Optional[List[str]] = None,
                             start_time: int = 0, end_time: int = 1000) -> Dict[str, Any]:
        """Parses the generated VCD waveform and returns signal activity summaries."""
        safe_id = self._sanitize_task_id(task_id)
        vcd_path = os.path.join(self.rtl_dir, f"{safe_id}.vcd")
        
        if not os.path.exists(vcd_path):
            # Attempt to run simulation first to extract VCD
            sim_res = self.simulator.run_simulation(task_id=safe_id, family="")
            vcd_path = sim_res.get("vcd_path", vcd_path)
        
        if not os.path.exists(vcd_path):
            return {
                "status": "ERROR",
                "message": f"Waveform file (.vcd) not found for task '{safe_id}'",
                "signals": {}
            }

        target_signals = signals or ["clk", "rst_n", "count", "full", "empty", "read_en", "write_en"]
        try:
            res = self.waveform_tool.query_waveform(
                vcd_path=vcd_path,
                signals=target_signals,
                start_time=start_time,
                end_time=end_time
            )
            data = res.get("data", {})
            total_transitions = sum(len(v) for v in data.values())
            return {
                "status": "SUCCESS" if res.get("success") else "ERROR",
                "task_id": safe_id,
                "total_transitions": total_transitions,
                "window": [start_time, end_time],
                "signals": {k: len(v) for k, v in data.items()},
                "transitions": {k: v[:10] for k, v in data.items()}
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Waveform extraction failed: {str(e)}",
                "signals": {}
            }

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Safe dispatcher for all registered agent tools."""
        if tool_name not in self.ALLOWED_TOOLS:
            return {
                "status": "ERROR",
                "error": f"Tool '{tool_name}' is not permitted. Allowed: {self.ALLOWED_TOOLS}"
            }

        task_id = args.get("task_id", "")
        if not task_id:
            return {"status": "ERROR", "error": "Missing required argument 'task_id'"}

        if tool_name == "read_rtl_file":
            return self.read_rtl_file(task_id=task_id)
        elif tool_name == "search_rtl":
            return self.search_rtl(task_id=task_id, query=args.get("query", ""))
        elif tool_name == "read_simulation_log":
            return self.read_simulation_log(task_id=task_id, design_family=args.get("design_family", ""))
        elif tool_name == "inspect_failure":
            return self.inspect_failure(task_id=task_id, metadata=args.get("metadata", {}))
        elif tool_name == "get_waveform_summary":
            return self.get_waveform_summary(task_id=task_id, signals=args.get("signals"))
        
        return {"status": "ERROR", "error": f"Unhandled tool '{tool_name}'"}
