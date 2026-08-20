import subprocess
import os
from typing import Tuple, Dict, Any

class VerilogSimulator:
    def __init__(self, rtl_dir: str):
        self.rtl_dir = rtl_dir
        # Ensure iverilog is in PATH if not already
        if "C:\\iverilog\\bin" not in os.environ.get("PATH", ""):
            os.environ["PATH"] = os.environ.get("PATH", "") + ";C:\\iverilog\\bin"

    def run_simulation(self, task_id: str, family: str) -> Dict[str, Any]:
        """Compiles and runs the Verilog simulation for a given task."""
        
        design_file = os.path.join(self.rtl_dir, "designs", f"{task_id}.v")
        tb_file = os.path.join(self.rtl_dir, "testbenches", f"{task_id}_tb.v")
        output_file = os.path.join(self.rtl_dir, f"{task_id}.vvp")
        
        # Compile
        compile_cmd = ["iverilog", "-o", output_file, design_file, tb_file]
        try:
            compile_res = subprocess.run(compile_cmd, capture_output=True, text=True, check=False)
            if compile_res.returncode != 0:
                return {
                    "success": False,
                    "compiled": False,
                    "error": compile_res.stderr,
                    "output": "",
                    "vcd_path": ""
                }
        except FileNotFoundError:
             return {
                    "success": False,
                    "compiled": False,
                    "error": "iverilog not found in PATH",
                    "output": "",
                    "vcd_path": ""
                }

        # Run
        vcd_path = os.path.join(self.rtl_dir, f"{task_id}.vcd")
        # Ensure any previous VCD is removed
        if os.path.exists(vcd_path):
            try:
                os.remove(vcd_path)
            except Exception:
                pass
            
        run_cmd = ["vvp", output_file]
        run_res = subprocess.run(run_cmd, capture_output=True, text=True, check=False)
        
        # Check if an assertion fired or simulation failed
        success = True
        if "ERROR" in run_res.stdout or "FAIL" in run_res.stdout or "FATAL" in run_res.stdout or run_res.returncode != 0:
            success = False
            
        return {
            "success": success,
            "compiled": True,
            "error": run_res.stderr,
            "output": run_res.stdout,
            "vcd_path": vcd_path if os.path.exists(vcd_path) else ""
        }
