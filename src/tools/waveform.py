from vcd.reader import TokenKind, tokenize
import os
from typing import Dict, List, Any

class WaveformTool:
    def __init__(self):
        pass

    def query_waveform(self, vcd_path: str, signals: List[str], start_time: int, end_time: int) -> Dict[str, Any]:
        """Reads a VCD file and extracts transitions for specific signals in a time window."""
        if not os.path.exists(vcd_path):
             return {"success": False, "error": f"VCD not found: {vcd_path}", "data": {}}
             
        signal_map = {}
        id_to_name = {}
        
        current_time = 0
        
        with open(vcd_path, 'rb') as f:
            for token in tokenize(f):
                if token.kind == TokenKind.VAR:
                    name = token.data.reference
                    if name in signals:
                        id_to_name[token.data.id_code] = name
                        signal_map[name] = []
                elif token.kind == TokenKind.CHANGE_TIME:
                    current_time = token.data
                elif token.kind in (TokenKind.CHANGE_SCALAR, TokenKind.CHANGE_VECTOR, TokenKind.CHANGE_STRING, TokenKind.CHANGE_REAL):
                    if token.data.id_code in id_to_name:
                        name = id_to_name[token.data.id_code]
                        if start_time <= current_time <= end_time:
                            signal_map[name].append((current_time, token.data.value))
                            
        return {
            "success": True,
            "data": signal_map,
            "error": ""
        }
