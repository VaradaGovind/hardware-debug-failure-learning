#!/usr/bin/env python3
"""
scripts/calculate_novelty_metrics.py

Calculates the lexical and structural novelty metrics of the V12 external benchmark
relative to historical benchmarks (V7, V8, V10, V11).

Parses Verilog source files, strips comments and Verilog reserved keywords,
and computes:
- Historical unique identifiers
- V12 unique identifiers
- Novel identifiers in V12 (count and percentage)
- Jaccard token similarity
"""

import os
import re
import sys

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

HISTORICAL_DIRS = [
    os.path.join(WORKSPACE_ROOT, "rtl", "designs"),
    os.path.join(WORKSPACE_ROOT, "rtl", "v10"),
    os.path.join(WORKSPACE_ROOT, "rtl", "v11")
]
V12_DIR = os.path.join(WORKSPACE_ROOT, "rtl", "v12")


def tokenize(text: str) -> set:
    """Strips comments and extracts alphanumeric identifiers."""
    text = re.sub(r'//.*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return set(re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', text))


def get_files(directory: str) -> list:
    """Returns all non-testbench Verilog files in a directory."""
    if not os.path.exists(directory):
        return []
    return [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.endswith('.v') and not f.endswith('_tb.v')
    ]


def main():
    hist_tokens = set()
    hist_files = []
    for d in HISTORICAL_DIRS:
        files = get_files(d)
        hist_files.extend(files)
        for f in files:
            with open(f, 'r', encoding='utf-8') as fp:
                hist_tokens.update(tokenize(fp.read()))

    v12_files = get_files(V12_DIR)
    v12_tokens = set()
    for f in v12_files:
        with open(f, 'r', encoding='utf-8') as fp:
            v12_tokens.update(tokenize(fp.read()))

    # Standard Verilog keywords and baseline signals to exclude
    VERILOG_KEYWORDS = {
        'module', 'endmodule', 'input', 'output', 'inout', 'wire', 'reg', 'assign',
        'always', 'posedge', 'negedge', 'begin', 'end', 'if', 'else', 'case', 'endcase',
        'default', 'parameter', 'localparam', 'integer', 'genvar', 'generate', 'endgenerate',
        'clk', 'rst', 'rst_n', 'reset', 'enable', 'in_data', 'out_data', 'busy', 'err_flag'
    }

    hist_idents = hist_tokens - VERILOG_KEYWORDS
    v12_idents = v12_tokens - VERILOG_KEYWORDS

    novel_idents = v12_idents - hist_idents
    overlap_idents = v12_idents.intersection(hist_idents)
    union_idents = v12_idents.union(hist_idents)
    jaccard = len(overlap_idents) / len(union_idents) if union_idents else 0.0

    print("====================================================")
    print("V12 STRUCTURAL & LEXICAL NOVELTY AUDIT")
    print("====================================================")
    print(f"Historical Files:              {len(hist_files)}")
    print(f"V12 Files:                     {len(v12_files)}")
    print(f"Historical Unique Identifiers: {len(hist_idents)}")
    print(f"V12 Unique Identifiers:        {len(v12_idents)}")
    novel_pct = (len(novel_idents) / len(v12_idents) * 100) if v12_idents else 0.0
    print(f"Novel V12 Identifiers:         {len(novel_idents)} ({novel_pct:.1f}%)")
    print(f"Overlap Identifiers:           {len(overlap_idents)}")
    print(f"Jaccard Token Similarity:      {jaccard:.4f}")
    print(f"Lexical Divergence:            {(1.0 - jaccard)*100:.1f}%")
    print("Sample Novel Identifiers (first 20):")
    print(" ", sorted(list(novel_idents))[:20])
    print("====================================================")


if __name__ == "__main__":
    main()
