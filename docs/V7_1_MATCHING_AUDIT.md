# V7.1 Matching & Retrieval Audit: Query Logic and Indexing Analysis

**Document Identifier:** `docs/V7_1_MATCHING_AUDIT.md`  
**Inspected Component:** `CertificateStore.query_candidates()` (`src/reuse/certificate_store.py`)  
**Data Sources:** `results/reports/v7_1_reuse_pipeline_trace.json`, `results/cost_analysis/v7_end_to_end_comparison.json`  

---

## 1. Executive Summary

In the RCA-Reuse architecture, the **Matching and Retrieval Engine** (`CertificateStore.query_candidates`) acts as the first-stage filter: given an incoming target failure with its design family, failure symptom, and observed interface signals, it retrieves and ranks candidate certificates from memory before invoking the expensive waveform validator.

This audit analyzes the mechanics of candidate retrieval to determine whether retrieval failures are causing missed reuse opportunities.

**Key Findings:**
1. **The Retrieval Gate Is Not the Primary Drop Point on Frozen Data**: On the canonical 25-case stream, within each design family, retrieval successfully located the corresponding source certificate whenever a trusted certificate was present in memory.
2. **Hard Filtering on Trust Gating**: When `only_trusted=True` is enabled, any source ingestion failure (such as `heldout_axi_src` suffering an `INVALID_OUTPUT` parse error) produces an empty candidate set (`[]`), completely bypassing downstream validation.
3. **Lexical Brittleness**: The scoring function relies strictly on exact string matching:
   $$\text{Score} = 1.0 + 2.0 \cdot \mathbb{I}(\text{symptom}_{\text{target}} == \text{symptom}_{\text{cert}}) + 3.0 \cdot \frac{|\text{signals}_{\text{cert}} \cap \text{signals}_{\text{target}}|}{|\text{signals}_{\text{cert}}|}$$
   It contains zero semantic normalization, architectural role mapping, or fuzzy symptom clustering.
4. **Quantification**: Retrieval returned candidates for 16 out of 20 target arrivals (80%). The 4 empty queries occurred solely in AXI (`axi_vl_a1`, `b1`, `f1`, `i2`) because the source certificate was rejected at ingestion.

---

## 2. Detailed Inspection of `query_candidates()`

```python
def query_candidates(self,
                     design_family: Optional[str] = None,
                     target_module: Optional[str] = None,
                     symptom: Optional[str] = None,
                     observed_signals: Optional[List[str]] = None,
                     only_trusted: bool = True) -> List[Tuple[float, TransactionSemanticCertificate]]:
    # Step 1: Index-based partition
    if design_family:
        candidate_ids = set(self._family_index.get(design_family, []))
    elif target_module:
        candidate_ids = set(self._module_index.get(target_module, []))
    else:
        candidate_ids = set(self._certificates.keys())

    scored_candidates = []
    for cid in candidate_ids:
        cert = self._certificates[cid]

        # Step 2: Trust Filter Gate
        if only_trusted and not cert.metadata.get("is_trusted", True):
            continue

        score = 1.0

        # Step 3: Exact Symptom Boost
        if symptom and cert.metadata.get("symptom") == symptom:
            score += 2.0

        # Step 4: Lexical Signal Overlap Boost
        if observed_signals:
            cert_sigs = set(cert.target_signals)
            obs_sigs = set(observed_signals)
            overlap = len(cert_sigs & obs_sigs)
            if cert_sigs:
                score += (overlap / len(cert_sigs)) * 3.0

        scored_candidates.append((score, copy.deepcopy(cert)))

    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    return scored_candidates
```

---

## 3. Systematic Testing of Failure Modes

We evaluated `query_candidates` across 5 fundamental dimensions of potential matching failure:

### Dimension 1: Lexical Signal Names Differ
* **Mechanism:** In real RTL codebases, signal names vary across IP blocks (e.g., `wr_en` vs `write_en`, `pop` vs `read_en`, `fifo_cnt` vs `count`).
* **Test:** If target signals are renamed from `["count", "write_en", "read_en"]` to `["fifo_count", "wr_en", "rd_en"]`:
  * `overlap = len(cert_sigs & obs_sigs) == 0`.
  * The signal overlap boost drops from $+3.0$ to $0.0$.
  * Furthermore, when the certificate is handed to `TransactionSemanticValidator`, the validator checks `curr_s["count"]` and crashes with missing signal error.
* **Status on Frozen Stream:** Not triggered on frozen stream because target signals use canonical naming. However, it represents a fatal blocker for cross-design transfer in real RTL.

### Dimension 2: Semantic Role Differs in Wording
* **Mechanism:** Symptom description strings differ (e.g., `"Timeout"` vs `"AXI Handshake Timeout"`).
* **Test:** In the current implementation:
  ```python
  if symptom and cert.metadata.get("symptom") == symptom:
  ```
  This is strict literal equality. A target reporting `"Simulation Timeout"` will receive $0$ symptom boost against a certificate labeled `"Timeout"`.
* **Status on Frozen Stream:** Exact string match held within each family.

### Dimension 3: Architectural Roles Are Not Normalized
* **Mechanism:** A FIFO and a Ring Buffer both maintain an occupancy invariant. A UART transmitter and an SPI controller both maintain a serial baud divider invariant.
* **Test:** Because `query_candidates` partitions by `design_family`, a certificate from `fifo` can NEVER be queried by a `ring_buffer` or `elastic_buffer`, even if the underlying bug is identical concurrent read/write occupancy corruption.
* **Impact:** Cross-family transfer is structurally impossible under the current index schema.

### Dimension 4: Protocol & Invariant Information Is Not Represented in Query
* **Mechanism:** The query filter does not know what protocol or invariant is violated. It relies purely on design family string.
* **Test:** If multiple certificates exist within the same family (e.g., one for `FIFO_SIMULTANEOUS_RW` and another for `FIFO_POINTER_OVERFLOW`), the query engine has no mechanism to rank between them other than identical symptom strings.
* **Impact:** Downstream validator must sequentially evaluate all candidates, increasing validation latency.

### Dimension 5: Temporal Mechanism Is Not Represented
* **Mechanism:** Causality latency contracts (e.g., 1-cycle vs 4-cycle stall drop) are absent from query scoring.
* **Test:** Candidates are ranked without regard to clock cycle budgets or temporal windows.

---

## 4. Quantification of Missed-Match Cases on Frozen 25-Case Stream

| Family | Targets | Queries Attempted | Candidates Returned | Top Score | Retrieval Outcome | Reason for Any Missing Retrieval |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **FIFO** | 4 | 4 | 1 per target | 6.0 | **100% Retrievable** | Symptom `"Data Mismatch"` matched; 100% signal overlap. |
| **AXI** | 4 | 4 | **0 per target** | N/A | **0% Retrievable** | Source certificate `heldout_axi_src` was marked `is_trusted=False` due to `INVALID_OUTPUT` on ingestion pass. |
| **FSM** | 4 | 4 | 1 per target | 6.0 | **100% Retrievable** | Symptom `"Stuck State"` matched; 100% signal overlap. |
| **UART** | 4 | 4 | 1 per target | 6.0 | **100% Retrievable** | Retrieved `cnt` certificate; failed downstream due to extractor schema gap. |
| **Pipeline** | 4 | 4 | 1 per target | 6.0 | **100% Retrievable** | Retrieved `d1` certificate; failed downstream due to invariant mismatch. |
| **Total** | **20** | **20** | **16 (80.0%)** | — | **80.0% Candidate Hit Rate** | **4 missed queries solely caused by AXI source trust rejection.** |

---

## 5. Key Conclusion

The retrieval engine itself did not fail on the frozen benchmark. When a trusted certificate was present, it achieved a **100% recall rate (16/16)**. 

The two failure mechanisms observed were:
1. **Upstream Starvation**: In AXI, retrieval failed because the source certificate was rejected before entering the index.
2. **Downstream Rejection**: In UART and Pipeline, retrieval succeeded, but downstream validation rejected the candidate due to schema and invariant brittleness.
