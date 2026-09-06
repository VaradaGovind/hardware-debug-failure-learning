# V12 Data Isolation & Benchmark Non-Contamination Audit

**Evaluation Date**: September 6, 2026  
**Experiment Identifier**: `V12_DATA_ISOLATION_AUDIT`  
**Model Identity**: `Qwen/Qwen2.5-Coder-1.5B-Instruct`  
**LoRA Weights**: `soup_v7_qwen_lora` (`best_v7_checkpoint`)  

---

## 1. Executive Summary

Experiment V12 evaluates the RCA-Reuse architecture on an external, realistic hardware corpus. To preserve absolute scientific integrity, this audit formally verifies that **zero training contamination, zero prompt leakage, and zero memory pre-loading** occurred between the external evaluation benchmark and the evaluated models.

---

## 2. Five-Tier Isolation Verification

```
                      DATA ISOLATION BOUNDARIES IN V12
  ┌────────────────────────────────────────────────────────────────────────┐
  │ 1. HISTORICAL TRAINING DATA ISOLATION                                  │
  │    V7 canonical training set (1,170 samples) audited.                   │
  │    0 external modules or bug patterns present in training splits.      │
  ├────────────────────────────────────────────────────────────────────────┤
  │ 2. TRUSTED RCA MEMORY ISOLATION                                        │
  │    System B trusted memory is strictly FROZEN to canonical sources.     │
  │    0 V12 external target cases admitted to memory prior to test.       │
  ├────────────────────────────────────────────────────────────────────────┤
  │ 3. SYSTEM A ZERO-MEMORY ISOLATION                                      │
  │    System A executes plain LLM RCA with strictly zero memory access.   │
  ├────────────────────────────────────────────────────────────────────────┤
  │ 4. ORACLE & GROUND-TRUTH PATCH ISOLATION                               │
  │    Ground-truth fixes and testbench assertion code are inaccessible     │
  │    to LLM context during investigation.                                │
  ├────────────────────────────────────────────────────────────────────────┤
  │ 5. RETRAINING & LO-RA IMMUTABILITY                                     │
  │    Zero fine-tuning, zero weight updates, zero prompt modifications.   │
  └────────────────────────────────────────────────────────────────────────┘
```

### Tier 1: Historical Training Data Isolation
* **Audit Subject**: The V7 canonical training dataset ([`docs/V7_DATASET_AUDIT.md`](file:///c:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/docs/V7_DATASET_AUDIT.md)) used to train `soup_v7_qwen_lora`.
* **Findings**:
  * The V7 dataset exclusively contains samples derived from synthetic variants of FIFO, AXI, FSM, UART, and Pipeline designs.
  * None of the 10 external IP cores (`sdram_controller`, `cache_controller_l1`, `i2c_master_bit_ctrl`, `spi_master_fifo`, `arbiter_round_robin`, `arbiter_priority`, `dma_controller_sg`, `interrupt_controller_pic`, `sha3_keccak_padder`, `divider_radix2`) are present in the V7 training set.
  * Zero signal names, module headers, or bug injection locations from V12 appear in training records.

### Tier 2: Trusted Memory Non-Contamination
* **Audit Subject**: System B's trusted semantic memory store.
* **Findings**:
  * System B's memory store contains exclusively the 5 canonical source cases established in Experiment V10.1 (`source_fifo`, `source_axi`, `source_fsm`, `source_uart`, `source_pipeline`).
  * No V12 target cases, certificates, or intermediate diagnostic outputs were admitted to memory prior to evaluation.
  * System B must evaluate V12 cases solely by querying the pre-existing source memory through its multi-stage semantic verification gate.

### Tier 3: System A Memory Isolation
* System A is hard-coded with zero memory access. It executes multi-turn LLM reasoning from scratch on every case without any lookup capability.

### Tier 4: Testbench & Patch Oracle Isolation
* The ground-truth repair diff and testbench assertion implementation are stored in the validation harness and are never exposed in prompt contexts sent to the model.
* Only the buggy RTL snippet, declared module interface, and the simulation assertion failure symptom are presented to the model during RCA.

### Tier 5: Zero Retraining & Architecture Invariance
* The model weights, LoRA adapter, tokenizer, temperature ($T=0.0$), and maximum context tokens remain bitwise identical to Experiments V10.1, V10.2, and V11.

---

## 3. Formal Isolation Certification

| Audit Item | Verification Method | Status |
|:---|:---|:---:|
| External RTL in training data | Full string search across V7/V9/V10 datasets | **0 Occurrences (PASSED)** |
| External bug patterns in training | Lexical AST comparison with V7 dataset | **0 Occurrences (PASSED)** |
| External cases in trusted memory | Memory inspection in System B runner | **0 Preloaded Cases (PASSED)** |
| Ground-truth patch leakage | Prompt template audit | **0 Exposed Patches (PASSED)** |
| Model weights modified | SHA256 verification of `best_v7_checkpoint` | **Bitwise Identical (PASSED)** |
