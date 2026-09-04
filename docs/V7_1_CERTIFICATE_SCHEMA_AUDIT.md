# V7.1 Certificate Schema Audit: Representation, Generalization, and Abstraction

**Document Identifier:** `docs/V7_1_CERTIFICATE_SCHEMA_AUDIT.md`  
**Inspected Components:** `src/reuse/transaction_semantic_certificate.py`, `src/reuse/transaction_certificate_extractor.py`, `src/reuse/transaction_semantic_validator.py`  
**Focus:** Architectural Generalization across Heterogeneous RTL Implementations  

---

## 1. Executive Summary

A debugging knowledge certificate is intended to capture the **invariant failure mechanism** of a hardware bug so that future occurrences of the same conceptual defect can be resolved without an expensive, multi-turn LLM investigation.

This audit evaluates whether the current `TransactionSemanticCertificate` schema stores enough semantic abstraction to generalize across real-world hardware variants.

**Key Findings:**
1. **Excessive Lexical Brittleness**: The current schema binds directly to literal signal string names (`write_en`, `read_en`, `count`, `valid_out`). If an equivalent target design renames `count` to `fifo_count` or `occ_cnt`, matching and validation immediately collapse.
2. **Missing Architectural Roles**: The schema lacks an intermediate **Architectural Role Abstraction layer** (e.g., mapping literal names to canonical hardware roles like `Role.OCCUPANCY_COUNTER`, `Role.FLOW_VALID`, `Role.FLOW_READY`).
3. **Domain Coverage Blindspots**: The certificate extractor hardcodes schemas for only 3 families (`fsm`, `pipeline`, `axi`), while falling back to a `FIFO_STREAM` default for all other designs. This completely blinds the system to UART and other communication protocols.
4. **Overly Narrow Invariant Mechanics**: Invariant checks assume specific delta or toggle patterns (e.g., assuming `valid_out` toggles at anomaly cycles, which fails when a stall drop manifests as a sustained low signal).

---

## 2. Current Certificate Schema Inspection

The current schema defines certificates via the following dataclasses:

```python
@dataclass
class TransactionContext:
    transaction_type: str            # e.g., "FIFO_STREAM", "HANDSHAKE_TRANSFER"
    initiating_event: Dict[str, Any] # e.g., {"write_en": 1, "read_en": 1}
    boundary_signals: List[str]      # e.g., ["write_en", "read_en", "count", "full", "empty"]
    active_window_cycles: int        # e.g., 4

@dataclass
class ProtocolObligation:
    obligation_type: str             # e.g., "OCCUPANCY_CONSERVATION"
    initiating_condition: Dict[str, Any]
    required_contract: Dict[str, Any]
    violation_signature: Dict[str, Any]
    temporal_latency: int

@dataclass
class TransactionSemanticCertificate:
    certificate_id: str
    source_failure: str
    target_module: str
    target_signals: List[str]
    defect_mechanism: str
    transaction_context: TransactionContext
    trigger_spec: Dict[str, Any]
    protocol_obligation: ProtocolObligation
    state_invariant_spec: Dict[str, Any]
    causal_propagation_spec: Dict[str, Any]
    temporal_constraint: Dict[str, Any]
    expected_observable_consequence: str
    metadata: Dict[str, Any]
```

---

## 3. Generalization Breakdown: What is Captured vs What is Missing

| Dimension | Currently Captured? | Current Representation | Missing / Deficient Aspect |
|---|:---:|---|---|
| **Architectural Role** | **No** | Literal signal names (`count`, `valid_out`) | No role binding (e.g., `OCCUPANCY_COUNTER`, `PRESCALER_COUNTER`, `HANDSHAKE_VALID`). |
| **Violated Invariant** | **Partial** | String enum (`CONSERVATION`, `STABILITY`, `STATE_TRANSITION`) | Hardcoded delta check (`delta == 1` or `curr != prev`); cannot handle multi-cycle or stall conditions. |
| **Protocol Obligation** | **Partial** | Precondition/Postcondition dicts (`write_en: 1, read_en: 1`) | Rigid cycle-by-cycle lookups; cannot adapt to variable-latency handshakes without explicit adapter. |
| **Temporal Pattern** | **Yes** | `temporal_latency: 1`, `STRICT_CAUSAL_SEQUENCE` | Order is verified ($T_{\text{tx}} \le T_{\text{obl}} \le T_{\text{prop}}$), but lacks flexible temporal logic (LTL / SVA). |
| **Causal Mechanism** | **Partial** | Enum (`OCCUPANCY_DIVERGENCE`, `STALL_PROPAGATION`) | Only checks whether downstream signals diverge; cannot distinguish causal origin from symptom ripple. |
| **Downstream Symptom** | **Yes** | `expected_observable_consequence` string | Merely stored as metadata; not actively evaluated in semantic ranking. |
| **Root-Cause Abstraction** | **No** | Literal string (`root_cause_signal: "count"`) | If target uses `fifo_count`, the reused signal name is literal and wrong. |
| **Confidence & Evidence** | **Partial** | `metadata["is_trusted"]`, verifier explanation | Confidence score is binary (`True`/`False`); lacks multi-dimensional margin scores. |

---

## 4. Concrete Generalization Stress Tests

### Case Study A: Signal Renaming (`count` vs `fifo_count`)
* **Source Design (`heldout_fifo_src`):**
  Internal occupancy register is named `count`.
  Certificate stores:
  ```json
  "state_invariant_spec": {
    "type": "CONSERVATION",
    "target_register": "count",
    "anomaly_delta": 1
  }
  ```
* **Target Design Variant:**
  Suppose an IP team integrates a FIFO where the register is named `fifo_count` or `occupancy`.
* **Execution Failure:**
  When `TransactionSemanticValidator.validate()` runs:
  ```python
  delta = curr_s.get("count", 0) - prev_s.get("count", 0)
  ```
  Because `"count"` does not exist in the target waveform dictionary, `curr_s.get("count")` returns `None` (or 0). The invariant calculation fails, emitting `Expected state invariant anomaly (CONSERVATION on count) was not observed in waveform.`
* **Root Problem**: The certificate stores the *lexical identifier* rather than the *semantic role*.

---

### Case Study B: Communication Protocols & The UART Omission
* **Source Design (`heldout_uart_src`):**
  Defect is in baud rate divider (`cnt`).
  Model correctly diagnosed `cnt` with 0.95 confidence.
  Verifier correctly confirmed rollover anomaly.
* **Extraction Failure (`TransactionCertificateExtractor.extract_from_rca`):**
  ```python
  if design_family == "fsm":
      ...
  elif design_family == "pipeline":
      ...
  elif design_family == "axi":
      ...
  else:
      # FALLS THROUGH TO FIFO!
      tx_ctx = TransactionContext(
          transaction_type="FIFO_STREAM",
          initiating_event={"write_en": 1, "read_en": 1},
          boundary_signals=["write_en", "read_en", "count", "full", "empty"],
          active_window_cycles=4
      )
  ```
* **Consequence**: The certificate was constructed with a FIFO transaction context! When validated against UART targets, the validator looked for `write_en` and `read_en`, rejected the context, and blocked 2 valid positive reuses.

---

### Case Study C: Pipeline Control Token vs Port Stability
* **Source Design (`heldout_pipe_src`):**
  Ground truth defect: stage 1 valid control flip-flop `v1` dropped during stall.
* **Extracted Certificate Spec:**
  ```json
  "protocol_obligation": {
    "obligation_type": "STALL_DRAINAGE_PRESERVATION",
    "initiating_condition": {"valid_in": 1}
  },
  "state_invariant_spec": {
    "type": "STABILITY",
    "target_register": "valid_out"
  }
  ```
* **Validation Failure on Pipeline Targets (`pipeline_vl_a1`, `b1`):**
  In `TransactionSemanticValidator`:
  ```python
  elif inv_type == "STABILITY":
      if curr_s.get(target_reg) != prev_s.get(target_reg):
          anomaly_cycles.append(c_idx)
  ```
  The check requires `valid_out` to *change value* (`curr != prev`) between adjacent cycles. But during a stall drop, `valid_out` remains unasserted (`0` $\rightarrow$ `0`). Consequently, `anomaly_cycles` is empty, and validation fails with:
  `"Expected state invariant anomaly (STABILITY on valid_out) was not observed in waveform."`
* **Root Problem**: Conflating a protocol obligation (stall drainage) with a rigid toggle invariant on a downstream port.

---

## 5. Architectural Recommendations for Next-Generation Schema

To achieve cross-design and cross-project knowledge reuse without weakening the V5 trust gate:

1. **Decouple Semantic Roles from Lexical Identifiers**:
   ```python
   @dataclass
   class SemanticRoleBinding:
       role: HardwareRole  # e.g., FLOW_VALID, FLOW_READY, OCCUPANCY_COUNTER, BAUD_PRESCALER
       canonical_signal: str
       target_alias: Optional[str]
   ```
2. **Schema Extensibility via Protocol Templates**:
   Replace the hardcoded `if/elif/else` extractor with modular protocol templates (`AxiProtocolTemplate`, `FifoProtocolTemplate`, `UartProtocolTemplate`, `PipelineProtocolTemplate`).
3. **State Invariant Generalization**:
   Expand invariants from primitive delta equality to predicate evaluation:
   * `INVARIANT_HOLD`: signal must maintain value across condition.
   * `CONSERVATION`: sum/count must balance across push/pop.
   * `PERIODIC_ROLLOVER`: counter must roll over within $[N-\epsilon, N+\epsilon]$ clock cycles.
