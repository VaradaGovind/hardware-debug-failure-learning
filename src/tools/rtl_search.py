import os
import re
from typing import Dict, List, Any

class RTLSearchTool:
    def __init__(self, rtl_dir: str):
        self.rtl_dir = rtl_dir

    def inspect_rtl(self, module_name: str, task_id: str) -> Dict[str, Any]:
        """Reads the RTL file and returns a simplistic structural view."""
        design_file = os.path.join(self.rtl_dir, "designs", f"{task_id}.v")
        if not os.path.exists(design_file):
            return {"success": False, "error": f"File not found: {design_file}"}

        with open(design_file, 'r') as f:
            content = f.read()

        # Basic regex parsing to find ports and internal signals
        ports = re.findall(r'(input|output)\s+(?:wire|reg)?\s*(?:\[.*\])?\s*(\w+)', content)
        internals = re.findall(r'(wire|reg)\s*(?:\[.*\])?\s*(\w+)\s*;', content)
        
        signals = [p[1] for p in ports] + [i[1] for i in internals]
        
        return {
            "success": True,
            "module": module_name,
            "signals": list(set(signals)),
            "content": content
        }

    def trace_dependency(self, signal: str, task_id: str) -> Dict[str, Any]:
        """Returns lines where the signal is assigned to or used."""
        design_file = os.path.join(self.rtl_dir, "designs", f"{task_id}.v")
        if not os.path.exists(design_file):
            return {"success": False, "error": f"File not found: {design_file}"}

        with open(design_file, 'r') as f:
            lines = f.readlines()

        assigned_in = []
        used_in = []
        
        for i, line in enumerate(lines):
            # very naive heuristic
            if re.search(rf'\b{signal}\b\s*<=', line) or re.search(rf'assign\s+\b{signal}\b', line):
                assigned_in.append(i + 1)
            elif re.search(rf'\b{signal}\b', line):
                used_in.append(i + 1)

        return {
            "success": True,
            "signal": signal,
            "assigned_in": assigned_in,
            "used_in": used_in
        }
