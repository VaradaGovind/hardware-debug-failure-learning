# Experiment V10.1 Bug Resolution Audit: Existing Capabilities, Deficiencies, and Formal Deterministic Resolution Criterion

**Document Identifier:** `docs/V10_1_BUG_RESOLUTION_AUDIT.md`  
**Date:** September 6, 2026  
**Experiment Milestone:** `V10.1_CONTROLLED_BUG_RESOLUTION`  
**Author:** Antigravity Autonomous Research Assistant  

---

## 1. Executive Summary

This audit establishes the empirical baseline for Experiment V10.1 by rigorously evaluating the repository's existing root-cause analysis (RCA), simulation, repair, and verification capabilities. 

Historically (from V1 through V10), the project evaluated the **triage and diagnostic decision** (whether a causal certificate matched a downstream target failure and whether the predicted signal matched ground truth). As explicitly documented in `docs/limitations.md` and `docs/rca_vs_reuse.md`, the pipeline terminated prior to patch synthesis and regression verification:
> *"The current pipeline terminates at the triage decision (`REUSE_RCA` vs. `FALLBACK_INDEPENDENT_RCA`). It evaluates whether the causal certificate matches the target trace, but does not simulate patch generation, RTL editing, or regression closure."*

Experiment V10.1 addresses this fundamental gap by introducing a **deterministic, machine-checked bug resolution pipeline** comparing Plain LLM RCA (System A) against Verified LLM-Reuse RCA (System B).

---

## 2. Technical Audit of Existing System Capabilities

### 2.1 How is a Root Cause Currently Represented?
- In the evaluation harness (`src/evaluation/rca_vs_reuse_harness.py`), an RCA diagnosis is represented by the `RCADiagnosisResult` dataclass:
  - `root_cause_signal: str`: The identifier of the primary culprit signal (e.g., `"count"`, `"valid_out"`, `"state"`, `"cnt"`, `"v1"`, or `"unknown"`).
  - `trajectory_summary: Dict[str, Any]`: Multi-step investigation steps, tool calls, and evidence statements.
- In certificates (`TransactionSemanticCertificate` and `V8UnifiedCertificate`), the root cause is encapsulated in:
  - `metadata["root_cause_signal"]`
  - `causal_signal_role`: Hardware role identifier mapped by `v8_semantic_roles.py`.

### 2.2 Is There Already a Repair / Fix Representation?
- **No.** Prior to V10.1, there was no RTL patching, repair representation, or automated AST modifier.
- The term "repair" in `src/agent/llm_provider.py` exclusively referred to a JSON schema syntax retry loop when LLM output failed strict JSON decoding. No RTL repair synthesis existed.

### 2.3 Are Hardware Mutations Deterministic?
- **Yes.** All 25 canonical benchmark failure instances across the 5 hardware families (FIFO, AXI, FSM, UART, Pipeline) were deterministically constructed by benchmark generators (`scripts/generate_variable_latency_benchmark.py`).
- Each defect corresponds to an exact, known Verilog mutation:
  1. **FIFO (`heldout_fifo_src`, `fifo_vl_a1`, `fifo_vl_b1`, `fifo_vl_i2`)**: Defect `FIFO_SIMULTANEOUS_RW` — The occupancy counter logic erroneously uses `else if`, corrupting `count` when both `write_en` and `read_en` are active simultaneously.
  2. **AXI (`heldout_axi_src`, `axi_vl_a1`, `axi_vl_b1`, `axi_vl_i2`)**: Defect `AXI_HANDSHAKE_HOLD` — The slave deasserts `valid_out` when `ready_in` is low, violating the AXI handshake stability protocol.
  3. **FSM (`heldout_fsm_src`, `fsm_vl_a1`, `fsm_vl_b1`, `fsm_vl_i2`)**: Defect `FSM_STUCK_STATE` — The FSM stays in state `0` (IDLE) despite the arrival of the `start` pulse.
  4. **UART (`heldout_uart_src`, `uart_vl_a1`, `uart_vl_b1`, `uart_vl_i2`)**: Defect `UART_BAUD_DIVIDER` — Baud counter `cnt` increments by 2 instead of 1, halving the bit duration.
  5. **Pipeline (`heldout_pipe_src`, `pipeline_vl_a1`, `pipeline_vl_b1`, `pipeline_vl_i2`)**: Defect `PIPE_STALL_BUBBLE` — Stage 1 valid flag `v1` is not propagated to `valid_out` during downstream stall release, dropping tokens.
  6. **Adversarial Negatives (`fifo_vl_f1`, `axi_vl_f1`, `fsm_vl_f1`, `uart_vl_f1`, `pipeline_vl_f1`)**: Different underlying defects (`write_ptr` overflow, `ready_out` drop, `done` timing, `tx` stop-bit defect, `d1` forwarding hazard).

### 2.4 Can a Predicted Root-Cause Signal be Mapped to a Known Bug Repair?
- **Yes.** Because the underlying RTL defects are localized and deterministic, diagnosing the true root-cause signal maps directly to the precise repair transformation required for that module.
- Conversely, diagnosing an incorrect or ungrounded signal (e.g. `write_ptr` on a simultaneous R/W counter bug, or `d1` on a valid control drop) maps to either no valid edit or a misdirected patch that fails to remediate the underlying defect.

### 2.5 Is Simulation Already Available?
- **Yes.** `src/tools/simulator.py` provides `VerilogSimulator`, wrapping Icarus Verilog (`iverilog` compiler and `vvp` runtime engine) on Windows. It produces simulation exit codes, stdout logs, and `.vcd` waveform files.

### 2.6 Are Assertions Already Available in the Frozen Benchmark?
- **Audit Finding**: In the initial failure-generation harness (`rtl/testbenches/*_tb.v`), the testbenches were designed strictly to provoke and dump failing VCD waveforms. To ensure simulation failure, they printed unconditional `$display("FAIL: ...")` statements at the end of stimulus delivery.
- Consequently, compiling clean or patched RTL against the legacy stimulus testbenches would still output `FAIL:`, masking any actual repair.
- Therefore, a dedicated **deterministic verification suite** containing actual functional assertions and protocol invariant checkers is required to evaluate true bug resolution.

### 2.7 Can a Bug be Verified as Resolved?
- **Yes**, provided that the patched RTL is executed against a deterministic verification testbench that checks both:
  1. Remediated behavior under the exact failing trigger stimulus.
  2. Regression preservation across standard functional cycles.

---

## 3. Detailed Audit Findings

### A. Existing Capabilities (What Can Already Be Reused?)
1. **Frozen 25-Case Paired Benchmark Stream**: The identical arrival stream across 5 hardware families with strict source/target/negative partitions.
2. **Unified Semantic Certificate Architecture (V8)**: Protocol adapters, normalized hardware roles, and certificate extraction.
3. **Multi-Layer Deterministic Safety Gates (V5/V8)**: `SourceRCAVerifier`, `TransactionSemanticValidator`, and grounded candidate pool validation.
4. **Agentic LLM Backend**: `AgenticRCABackend` supporting tool-assisted multi-turn interaction with `Qwen/Qwen2.5-Coder-1.5B-Instruct` + `soup_v7_qwen_lora`.
5. **Simulation Tooling**: Icarus Verilog (`iverilog`, `vvp`) integration.

### B. Missing Capabilities (What Needs to be Implemented for V10.1?)
1. **Deterministic Patch Synthesizer / Mapper**: A deterministic engine that translates a diagnosed root-cause signal into the corresponding RTL patch for that module family.
2. **Assertion-Based Deterministic Verification Suite**: High-coverage verification testbenches for all 5 hardware families that evaluate functional assertions and protocol invariants rather than unconditionally printing `FAIL`.
3. **Controlled Resolution Runners**:
   - `experiments/run_v10_1_plain_llm_rca.py` (System A: Pure LLM RCA, strictly no memory).
   - `experiments/run_v10_1_llm_reuse_rca.py` (System B: Memory lookup + verified semantic reuse + fallback RCA).
4. **Resolution Telemetry & Token Accounting**: Rigorous separation of LLM token/call work from deterministic simulation/verification overhead.

### C. Formal Resolution Definition

```
                       ┌──────────────────────────────┐
                       │       Buggy RTL Target       │
                       └──────────────┬───────────────┘
                                      │
                         [System A or System B]
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │  Diagnosed Root-Cause Signal │
                       └──────────────┬───────────────┘
                                      │
                        Deterministic Patch Synthesis
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │      Patched RTL Module      │
                       └──────────────┬───────────────┘
                                      │
                         Icarus Verilog Compilation
                       + Assertion-Based Verification
                                      │
                     ┌────────────────┴────────────────┐
                     ▼                                 ▼
           [All Assertions PASS]             [Assertion Violation
              No Simulation Fail]              or Compile Error]
                     │                                 │
                     ▼                                 ▼
               RESOLVED = True                  RESOLVED = False
```

### Deterministic Resolution Criterion
A bug is classified as **`RESOLVED`** if and only if:
1. A candidate diagnosis is emitted (`candidate_signal != "unknown"`).
2. The corresponding patch is synthesized and applied to the target RTL.
3. The patched RTL compiles cleanly without warnings/errors under `iverilog`.
4. The patched RTL passes the entire deterministic verification testbench under `vvp`, satisfying 100% of functional assertions with zero assertion violations, timeouts, or protocol exceptions.

Under no circumstances is an LLM or heuristic model permitted to assess resolution. The verification decision is 100% machine-checked and deterministic.
