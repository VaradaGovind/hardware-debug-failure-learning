# Baseline System Snapshot

- **Date:** 2026-09-01
- **Git Commit Hash:** `5c797da963f8f16a42de9957454ab2b1175f766c`
- **Git Branch:** `main`
- **Environment:** Windows 11 Host, Python 3.12.10, External venv `.venv`, Icarus Verilog 12.0 (`C:\iverilog\bin`)
- **Unit & Safety Test Status:** 25 / 25 PASSED (100%)

## Existing Experiment Baseline Results (Deterministic Proxy RCA vs. RCA-Reuse)

| Metric | Baseline Full RCA | RCA-Reuse Pipeline | Delta / Improvement |
|---|:---:|:---:|:---:|
| **Total Invocations** | 25 | 17 | 8 investigations avoided (32% reduction) |
| **Successful Reuses** | 0 | 8 / 20 target arrivals | 40.0% reuse rate on targets |
| **Fallback Executions** | 25 | 12 / 20 target arrivals | 60.0% fallback rate (safety conservative) |
| **Diagnosis Correctness** | 80.0% | 80.0% | 0.0% accuracy loss (parity maintained) |
| **Reuse Precision** | N/A | 83.3% | Correct reuse across exercised matches |
| **Unsafe Reuse Rate (FRR)** | N/A | 16.7% | 1 false positive on adversarial testbench |
| **Incomplete Trace Safety** | N/A | 100% (5/5) | Safely rejected to independent fallback |
| **Wall-Clock Time** | 2656.5 ms | 1699.3 ms | 36.0% wall-clock latency reduction |
