import os
import json
import hashlib
from typing import List, Dict, Any

def sha256_file(filepath: str) -> str:
    if not os.path.exists(filepath):
        return "MISSING"
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def generate_variable_latency_benchmark(base_dir: str):
    stress_dir = os.path.join(base_dir, "results", "transaction_semantic_certs", "variable_latency_stress")
    bench_dir = os.path.join(stress_dir, "benchmark")
    designs_dir = os.path.join(base_dir, "rtl", "designs")
    tb_dir = os.path.join(base_dir, "rtl", "testbenches")
    
    for d in [stress_dir, bench_dir, designs_dir, tb_dir]:
        os.makedirs(d, exist_ok=True)
        
    norm_base = base_dir.replace("\\", "/")
    
# Verify and record frozen manifest
    frozen_files = [
        os.path.join(base_dir, "src", "reuse", "transaction_semantic_certificate.py"),
        os.path.join(base_dir, "src", "reuse", "transaction_semantic_validator.py"),
        os.path.join(base_dir, "src", "reuse", "transaction_certificate_extractor.py"),
        os.path.join(base_dir, "src", "reuse", "generic_certificate.py"),
        os.path.join(base_dir, "src", "reuse", "remediated_certificate_validator.py"),
        os.path.join(base_dir, "src", "reuse", "scale_similarity_baselines.py")
    ]
    
    manifest = {
        "timestamp": "2026-08-16T00:20:00Z",
        "phase": "Argus Phase 4.3 Variable-Latency Adaptive Boundary Stress Test",
        "frozen_source_hashes": {os.path.basename(p): sha256_file(p) for p in frozen_files},
        "random_seeds": [1001, 2002, 3003, 4004, 5005],
        "total_designs": 5,
        "design_families": ["FIFO", "AXI", "FSM", "UART", "PIPELINE"],
        "transaction_classes": [
            "CLASS_A_SHORT",
            "CLASS_B_DELAYED",
            "CLASS_C_MULTI_BEAT",
            "CLASS_D_STALL_BACKPRESSURE",
            "CLASS_E_IDLE_DISTRACTOR",
            "CLASS_F_SAME_SYMPTOM_NEG",
            "CLASS_G_SAME_TRIGGER_NEG",
            "CLASS_H_SAME_INVARIANT_NEG",
            "CLASS_I_INCOMPLETE_EVIDENCE"
        ]
    }
    
    with open(os.path.join(stress_dir, "frozen_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # GENERATE 75+ VARIABLE-LATENCY BENCHMARK INSTANCES (15 per design family)
    
    held_out_instances = []
    
    # Configuration for 5 Design Families x 15 Cases = 75 Cases Total
    designs_config = [
        # FIFO Family (Defect: Simultaneous R/W occupancy counter corruption)
        {
            "family_id": "FIFO_SIMULTANEOUS_RW",
            "design": "fifo",
            "source_id": "heldout_fifo_src",
            "signals": ["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"],
            "cases": [
                # Class A: Short (1-4 cycles) - Positive match
                {"sub_id": "vl_a1", "class": "CLASS_A_SHORT", "match": True, "exp_len": 3,
                 "stim": "#10 write_en=1; read_en=1; write_data=8'h33; #10 write_en=0; read_en=0; #30;",
                 "rtl": "if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;",
                 "symptom": "FAIL: FIFO Buffer Overrun Short A1"},
                {"sub_id": "vl_a2", "class": "CLASS_A_SHORT", "match": True, "exp_len": 4,
                 "stim": "#10 write_en=1; write_data=8'h11; #10 write_en=1; read_en=1; write_data=8'h22; #10 write_en=0; read_en=0; #30;",
                 "rtl": "if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;",
                 "symptom": "FAIL: FIFO Desync Short A2"},

                # Class B: Delayed Trigger (6-10 cycles delay after initiation) - Positive match
                # Initiation begins at cycle 1, but simultaneous RW trigger occurs at cycle 7!
                {"sub_id": "vl_b1", "class": "CLASS_B_DELAYED", "match": True, "exp_len": 9,
                 "stim": "#10 write_en=1; write_data=8'h10; #10 write_en=1; write_data=8'h20; #10 write_en=1; write_data=8'h30; #10 write_en=1; write_data=8'h40; #10 write_en=1; write_data=8'h50; #10 write_en=1; read_en=1; write_data=8'h60; #10 write_en=0; read_en=0; #30;",
                 "rtl": "if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;",
                 "symptom": "FAIL: FIFO Delayed Simultaneous RW Trigger B1"},
                {"sub_id": "vl_b2", "class": "CLASS_B_DELAYED", "match": True, "exp_len": 8,
                 "stim": "#10 write_en=1; write_data=8'h11; #10 write_en=0; #10 write_en=1; write_data=8'h22; #10 write_en=0; #10 write_en=1; read_en=1; write_data=8'h33; #10 write_en=0; read_en=0; #30;",
                 "rtl": "if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;",
                 "symptom": "FAIL: FIFO Intermittent RW Trigger B2"},

                # Class C: Long Multi-Beat Stream (12-20 cycles) - Positive match
                {"sub_id": "vl_c1", "class": "CLASS_C_MULTI_BEAT", "match": True, "exp_len": 14,
                 "stim": "#10 write_en=1; write_data=8'h01; #10 write_en=1; write_data=8'h02; #10 write_en=1; write_data=8'h03; #10 write_en=1; write_data=8'h04; #10 write_en=1; write_data=8'h05; #10 write_en=1; read_en=1; write_data=8'h06; #10 write_en=1; read_en=1; write_data=8'h07; #10 write_en=1; read_en=1; write_data=8'h08; #10 write_en=0; read_en=0; #30;",
                 "rtl": "if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;",
                 "symptom": "FAIL: FIFO Multi-Beat Stream Overrun C1"},
                {"sub_id": "vl_c2", "class": "CLASS_C_MULTI_BEAT", "match": True, "exp_len": 16,
                 "stim": "#10 write_en=1; write_data=8'hAA; #10 write_en=1; write_data=8'hBB; #10 write_en=1; write_data=8'hCC; #10 write_en=1; write_data=8'hDD; #10 write_en=1; write_data=8'hEE; #10 write_en=1; write_data=8'hFF; #10 write_en=1; read_en=1; write_data=8'h77; #10 write_en=0; read_en=0; #30;",
                 "rtl": "if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;",
                 "symptom": "FAIL: FIFO Sustained Burst Desync C2"},

                # Class D: Stall / Backpressure (Stalled writes followed by simultaneous RW) - Positive match
                {"sub_id": "vl_d1", "class": "CLASS_D_STALL_BACKPRESSURE", "match": True, "exp_len": 10,
                 "stim": "#10 write_en=1; write_data=8'h11; #10 write_en=0; #20; #10 write_en=1; read_en=1; write_data=8'h99; #10 write_en=0; read_en=0; #30;",
                 "rtl": "if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;",
                 "symptom": "FAIL: FIFO Backpressure Stalled Overrun D1"},

                # Class E: Long Idle Gaps with Adjacent Distractors - Positive match
                {"sub_id": "vl_e1", "class": "CLASS_E_IDLE_DISTRACTOR", "match": True, "exp_len": 12,
                 "stim": "#50; #10 write_en=1; write_data=8'h11; #10 write_en=1; read_en=1; write_data=8'h22; #10 write_en=0; read_en=0; #50 write_data=8'hFF; #30;",
                 "rtl": "if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;",
                 "symptom": "FAIL: FIFO Idle Offset Distractor E1"},

                # Class F: Same Symptom / Different Defect (Negative)
                {"sub_id": "vl_f1", "class": "CLASS_F_SAME_SYMPTOM_NEG", "match": False, "exp_len": 6,
                 "stim": "#10 write_en=1; write_data=8'h11; #10 read_en=1; #10 write_en=0; read_en=0; #30;",
                 "rtl": "if (read_en && !empty) count <= 0; else if (write_en && !full) count <= count + 1;",
                 "symptom": "FAIL: FIFO Buffer Overrun Short A1"},
                {"sub_id": "vl_f2", "class": "CLASS_F_SAME_SYMPTOM_NEG", "match": False, "exp_len": 8,
                 "stim": "#10 write_en=1; write_data=8'h22; #10 write_en=1; write_data=8'h33; #10 write_en=0; #30;",
                 "rtl": "if (write_en && !full) count <= count + 2;",
                 "symptom": "FAIL: FIFO Delayed Simultaneous RW Trigger B1"},

                # Class G: Same Trigger / Different Mechanism (Negative)
                {"sub_id": "vl_g1", "class": "CLASS_G_SAME_TRIGGER_NEG", "match": False, "exp_len": 8,
                 "stim": "#10 write_en=1; write_data=8'h11; #10 write_en=1; read_en=1; write_data=8'h55; #10 write_en=0; read_en=0; #30;",
                 "rtl": "if (write_en && read_en) write_ptr <= write_ptr + 2; if (write_en && !full && read_en && !empty) count <= count;",
                 "symptom": "FAIL: FIFO Pointer Corruption G1"},

                # Class H: Same Low-Level Invariant / Different Transaction Semantics (Decisive Negative)
                {"sub_id": "vl_h1", "class": "CLASS_H_SAME_INVARIANT_NEG", "match": False, "exp_len": 6,
                 "stim": "#10 write_en=1; read_en=0; write_data=8'hAA; #10 write_en=0; #30;",
                 "rtl": "if (write_en && !full && read_en && !empty) count <= count; else if (write_en && !full) count <= count + 1;",
                 "symptom": "FAIL: Unrelated FIFO Check H1"},
                {"sub_id": "vl_h2", "class": "CLASS_H_SAME_INVARIANT_NEG", "match": False, "exp_len": 10,
                 "stim": "#10 write_en=1; read_en=0; write_data=8'hBB; #10 write_en=1; read_en=0; write_data=8'hCC; #10 write_en=0; #30;",
                 "rtl": "if (write_en && !full && read_en && !empty) count <= count; else if (write_en && !full) count <= count + 1;",
                 "symptom": "FAIL: Unrelated FIFO Check H2"},

                # Class I: Incomplete / Truncated Evidence (Safety control -> INSUFFICIENT_EVIDENCE)
                {"sub_id": "vl_i1", "class": "CLASS_I_INCOMPLETE_EVIDENCE", "match": False, "exp_len": 2,
                 "stim": "#5 write_en=0; read_en=0;",
                 "rtl": "if (write_en && !full) count <= count + 1;",
                 "symptom": "FAIL: Early FIFO Abort I1"},
                {"sub_id": "vl_i2", "class": "CLASS_I_INCOMPLETE_EVIDENCE", "match": False, "exp_len": 4,
                 "stim": "#10 write_en=1; read_en=1; write_data=8'h11;", # Ends abruptly during active write
                 "rtl": "if (write_en && !full) count <= count + 1;",
                 "symptom": "FAIL: Truncated FIFO Mid-Flight I2"}
            ]
        },

        # AXI Family (Defect: Handshake stability drop during backpressure)
        {
            "family_id": "AXI_HANDSHAKE_HOLD",
            "design": "axi",
            "source_id": "heldout_axi_src",
            "signals": ["valid_in", "ready_in", "valid_out", "ready_out"],
            "cases": [
                # Class A: Short (1-4 cycles) - Positive match
                {"sub_id": "vl_a1", "class": "CLASS_A_SHORT", "match": True, "exp_len": 4,
                 "stim": "#10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=0; #10 valid_in=0; #30;",
                 "rtl": "if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;",
                 "symptom": "FAIL: AXI Transfer Dropped Short A1"},
                {"sub_id": "vl_a2", "class": "CLASS_A_SHORT", "match": True, "exp_len": 4,
                 "stim": "#10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=0; #10 valid_in=0; #30;",
                 "rtl": "if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;",
                 "symptom": "FAIL: AXI Backpressure Short A2"},

                # Class B: Delayed Trigger (Delayed backpressure after 6 transfer beats) - Positive match
                {"sub_id": "vl_b1", "class": "CLASS_B_DELAYED", "match": True, "exp_len": 10,
                 "stim": "#10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=0; #10 valid_in=0; #30;",
                 "rtl": "if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;",
                 "symptom": "FAIL: AXI Delayed Backpressure Defect B1"},
                {"sub_id": "vl_b2", "class": "CLASS_B_DELAYED", "match": True, "exp_len": 9,
                 "stim": "#10 valid_in=1; ready_in=1; #10 valid_in=0; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=0; #10 valid_in=1; ready_in=0; #10 valid_in=0; #30;",
                 "rtl": "if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;",
                 "symptom": "FAIL: AXI Intermittent Backpressure Defect B2"},

                # Class C: Long Multi-Beat Stream (12-20 cycles) - Positive match
                {"sub_id": "vl_c1", "class": "CLASS_C_MULTI_BEAT", "match": True, "exp_len": 14,
                 "stim": "#10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=0; #10 valid_in=0; #30;",
                 "rtl": "if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;",
                 "symptom": "FAIL: AXI Burst Stream Drop C1"},
                {"sub_id": "vl_c2", "class": "CLASS_C_MULTI_BEAT", "match": True, "exp_len": 16,
                 "stim": "#10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=0; #10 valid_in=0; #30;",
                 "rtl": "if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;",
                 "symptom": "FAIL: AXI Sustained Transfer Loss C2"},

                # Class D: Multi-Cycle Stall Backpressure (5 cycles of ready=0) - Positive match
                {"sub_id": "vl_d1", "class": "CLASS_D_STALL_BACKPRESSURE", "match": True, "exp_len": 11,
                 "stim": "#10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=0; #10 valid_in=1; ready_in=0; #10 valid_in=1; ready_in=0; #10 valid_in=1; ready_in=0; #10 valid_in=0; #30;",
                 "rtl": "if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;",
                 "symptom": "FAIL: AXI Long Backpressure Hold D1"},

                # Class E: Long Idle Gap & Distractors - Positive match
                {"sub_id": "vl_e1", "class": "CLASS_E_IDLE_DISTRACTOR", "match": True, "exp_len": 12,
                 "stim": "#40; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=0; #10 valid_in=0; #40 ready_in=1; #30;",
                 "rtl": "if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;",
                 "symptom": "FAIL: AXI Idle Distractor Transfer E1"},

                # Class F: Same Symptom / Different Defect (Negative)
                {"sub_id": "vl_f1", "class": "CLASS_F_SAME_SYMPTOM_NEG", "match": False, "exp_len": 6,
                 "stim": "#10 valid_in=1; ready_in=1; #10 valid_in=0; #30;",
                 "rtl": "valid_out <= 0;",
                 "symptom": "FAIL: AXI Transfer Dropped Short A1"},
                {"sub_id": "vl_f2", "class": "CLASS_F_SAME_SYMPTOM_NEG", "match": False, "exp_len": 8,
                 "stim": "#10 valid_in=1; ready_in=1; #10 valid_in=0; #30;",
                 "rtl": "valid_out <= ~valid_in;",
                 "symptom": "FAIL: AXI Delayed Backpressure Defect B1"},

                # Class G: Same Trigger / Different Mechanism (Negative)
                {"sub_id": "vl_g1", "class": "CLASS_G_SAME_TRIGGER_NEG", "match": False, "exp_len": 6,
                 "stim": "#10 valid_in=1; ready_in=0; #10 valid_in=0; #30;",
                 "rtl": "if (valid_in && !ready_in) valid_out <= 1; else valid_out <= 0;",
                 "symptom": "FAIL: AXI Slave Stall G1"},

                # Class H: Same Low-Level Invariant / Different Semantics (Decisive Negative)
                {"sub_id": "vl_h1", "class": "CLASS_H_SAME_INVARIANT_NEG", "match": False, "exp_len": 6,
                 "stim": "#10 valid_in=0; ready_in=0; #30;",
                 "rtl": "if (valid_in) valid_out <= 1; else valid_out <= 0;",
                 "symptom": "FAIL: Unrelated AXI Bus Timeout H1"},
                {"sub_id": "vl_h2", "class": "CLASS_H_SAME_INVARIANT_NEG", "match": False, "exp_len": 8,
                 "stim": "#10 valid_in=0; ready_in=1; #30;",
                 "rtl": "if (valid_in) valid_out <= 1; else valid_out <= 0;",
                 "symptom": "FAIL: Unrelated AXI Bus Timeout H2"},

                # Class I: Incomplete / Truncated Trace (Safety -> INSUFFICIENT)
                {"sub_id": "vl_i1", "class": "CLASS_I_INCOMPLETE_EVIDENCE", "match": False, "exp_len": 2,
                 "stim": "#5 valid_in=0; ready_in=0;",
                 "rtl": "valid_out <= valid_in;",
                 "symptom": "FAIL: Truncated AXI Trace I1"},
                {"sub_id": "vl_i2", "class": "CLASS_I_INCOMPLETE_EVIDENCE", "match": False, "exp_len": 4,
                 "stim": "#10 valid_in=1; ready_in=0;",
                 "rtl": "valid_out <= 0;",
                 "symptom": "FAIL: Truncated AXI Handshake I2"}
            ]
        },

        # FSM Family (Defect: State stuck in IDLE despite start trigger)
        {
            "family_id": "FSM_STUCK_STATE",
            "design": "fsm",
            "source_id": "heldout_fsm_src",
            "signals": ["state", "start", "done"],
            "cases": [
                # Class A: Short (1-4 cycles) - Positive match
                {"sub_id": "vl_a1", "class": "CLASS_A_SHORT", "match": True, "exp_len": 4,
                 "stim": "#10 start=1; #10 start=0; #30;",
                 "rtl": "state <= 0;",
                 "symptom": "FAIL: FSM Deadlock Short A1"},
                {"sub_id": "vl_a2", "class": "CLASS_A_SHORT", "match": True, "exp_len": 4,
                 "stim": "#10 start=1; #10 start=0; #30;",
                 "rtl": "state <= 0;",
                 "symptom": "FAIL: FSM State Hang Short A2"},

                # Class B: Delayed Trigger (Delayed start pulse after preamble) - Positive match
                {"sub_id": "vl_b1", "class": "CLASS_B_DELAYED", "match": True, "exp_len": 10,
                 "stim": "#50 start=0; #10 start=1; #10 start=0; #30;",
                 "rtl": "state <= 0;",
                 "symptom": "FAIL: FSM Delayed Start Pulse B1"},
                {"sub_id": "vl_b2", "class": "CLASS_B_DELAYED", "match": True, "exp_len": 12,
                 "stim": "#70 start=0; #10 start=1; #10 start=0; #30;",
                 "rtl": "state <= 0;",
                 "symptom": "FAIL: FSM Delayed Stimulus Trigger B2"},

                # Class C: Long Multi-Beat / Repeated Start Cycles - Positive match
                {"sub_id": "vl_c1", "class": "CLASS_C_MULTI_BEAT", "match": True, "exp_len": 14,
                 "stim": "#10 start=1; #10 start=0; #20; #10 start=1; #10 start=0; #20; #10 start=1; #10 start=0; #30;",
                 "rtl": "state <= 0;",
                 "symptom": "FAIL: FSM Repeated Start Failure C1"},
                {"sub_id": "vl_c2", "class": "CLASS_C_MULTI_BEAT", "match": True, "exp_len": 16,
                 "stim": "#10 start=1; #10 start=0; #10 start=1; #10 start=0; #10 start=1; #10 start=0; #30;",
                 "rtl": "state <= 0;",
                 "symptom": "FAIL: FSM Multi-Start Lock C2"},

                # Class D: Multi-Cycle Start Hold - Positive match
                {"sub_id": "vl_d1", "class": "CLASS_D_STALL_BACKPRESSURE", "match": True, "exp_len": 8,
                 "stim": "#10 start=1; #40 start=1; #10 start=0; #30;",
                 "rtl": "state <= 0;",
                 "symptom": "FAIL: FSM Extended Start Hold D1"},

                # Class E: Long Idle Gap & Distractor - Positive match
                {"sub_id": "vl_e1", "class": "CLASS_E_IDLE_DISTRACTOR", "match": True, "exp_len": 12,
                 "stim": "#60; #10 start=1; #10 start=0; #50;",
                 "rtl": "state <= 0;",
                 "symptom": "FAIL: FSM Long Idle Distractor E1"},

                # Class F: Same Symptom / Different Defect (Negative)
                {"sub_id": "vl_f1", "class": "CLASS_F_SAME_SYMPTOM_NEG", "match": False, "exp_len": 6,
                 "stim": "#10 start=1; #10 start=0; #30;",
                 "rtl": "state <= 1;",
                 "symptom": "FAIL: FSM Deadlock Short A1"},
                {"sub_id": "vl_f2", "class": "CLASS_F_SAME_SYMPTOM_NEG", "match": False, "exp_len": 8,
                 "stim": "#10 start=1; #10 start=0; #30;",
                 "rtl": "state <= 2;",
                 "symptom": "FAIL: FSM Delayed Start Pulse B1"},

                # Class G: Same Trigger / Different Mechanism (Negative)
                {"sub_id": "vl_g1", "class": "CLASS_G_SAME_TRIGGER_NEG", "match": False, "exp_len": 6,
                 "stim": "#10 start=1; #10 start=0; #30;",
                 "rtl": "state <= 1; done <= 1;",
                 "symptom": "FAIL: FSM Premature Done G1"},

                # Class H: Same Low-Level Invariant / Different Semantics (Decisive Negative)
                {"sub_id": "vl_h1", "class": "CLASS_H_SAME_INVARIANT_NEG", "match": False, "exp_len": 6,
                 "stim": "#40 start=0; #30;",
                 "rtl": "if (start) state <= 1; else state <= 0;",
                 "symptom": "FAIL: Unrelated FSM Timer Expiry H1"},
                {"sub_id": "vl_h2", "class": "CLASS_H_SAME_INVARIANT_NEG", "match": False, "exp_len": 8,
                 "stim": "#60 start=0; #30;",
                 "rtl": "if (start) state <= 1; else state <= 0;",
                 "symptom": "FAIL: Unrelated FSM Timer Expiry H2"},

                # Class I: Incomplete / Truncated Trace (Safety -> INSUFFICIENT)
                {"sub_id": "vl_i1", "class": "CLASS_I_INCOMPLETE_EVIDENCE", "match": False, "exp_len": 2,
                 "stim": "#5 start=0;",
                 "rtl": "state <= 0;",
                 "symptom": "FAIL: FSM Truncated Trace I1"},
                {"sub_id": "vl_i2", "class": "CLASS_I_INCOMPLETE_EVIDENCE", "match": False, "exp_len": 3,
                 "stim": "#10 start=1;",
                 "rtl": "state <= 0;",
                 "symptom": "FAIL: FSM Mid-Start Abort I2"}
            ]
        },

        # PIPELINE Family (Defect: Stall bubble / valid_out dropped)
        {
            "family_id": "PIPE_STALL_BUBBLE",
            "design": "pipeline",
            "source_id": "heldout_pipe_src",
            "signals": ["valid_in", "d_in", "v1", "d1", "valid_out", "d_out"],
            "cases": [
                # Class A: Short (1-4 cycles) - Positive match
                {"sub_id": "vl_a1", "class": "CLASS_A_SHORT", "match": True, "exp_len": 4,
                 "stim": "#10 valid_in=1; d_in=8'h33; #10 valid_in=0; #30;",
                 "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0;",
                 "symptom": "FAIL: Pipeline Drop Short A1"},
                {"sub_id": "vl_a2", "class": "CLASS_A_SHORT", "match": True, "exp_len": 4,
                 "stim": "#10 valid_in=1; d_in=8'h77; #10 valid_in=0; #30;",
                 "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0;",
                 "symptom": "FAIL: Pipeline Throughput Loss Short A2"},

                # Class B: Delayed Trigger (Delayed valid_in pulse after multi-cycle idle) - Positive match
                {"sub_id": "vl_b1", "class": "CLASS_B_DELAYED", "match": True, "exp_len": 10,
                 "stim": "#50 valid_in=0; #10 valid_in=1; d_in=8'h44; #10 valid_in=0; #30;",
                 "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0;",
                 "symptom": "FAIL: Pipeline Delayed Stream Drop B1"},
                {"sub_id": "vl_b2", "class": "CLASS_B_DELAYED", "match": True, "exp_len": 12,
                 "stim": "#70 valid_in=0; #10 valid_in=1; d_in=8'h55; #10 valid_in=0; #30;",
                 "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0;",
                 "symptom": "FAIL: Pipeline Delayed Ingestion Defect B2"},

                # Class C: Long Multi-Beat Stream (8-20 cycles) - Positive match
                {"sub_id": "vl_c1", "class": "CLASS_C_MULTI_BEAT", "match": True, "exp_len": 14,
                 "stim": "#10 valid_in=1; d_in=8'h11; #10 valid_in=1; d_in=8'h22; #10 valid_in=1; d_in=8'h33; #10 valid_in=1; d_in=8'h44; #10 valid_in=1; d_in=8'h55; #10 valid_in=0; #30;",
                 "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0;",
                 "symptom": "FAIL: Pipeline Continuous Stream Loss C1"},
                {"sub_id": "vl_c2", "class": "CLASS_C_MULTI_BEAT", "match": True, "exp_len": 16,
                 "stim": "#10 valid_in=1; d_in=8'hAA; #10 valid_in=1; d_in=8'hBB; #10 valid_in=1; d_in=8'hCC; #10 valid_in=1; d_in=8'hDD; #10 valid_in=1; d_in=8'hEE; #10 valid_in=1; d_in=8'hFF; #10 valid_in=0; #30;",
                 "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0;",
                 "symptom": "FAIL: Pipeline Extended Multi-Beat Drop C2"},

                # Class D: Multi-Cycle Bubble Interruption - Positive match
                {"sub_id": "vl_d1", "class": "CLASS_D_STALL_BACKPRESSURE", "match": True, "exp_len": 10,
                 "stim": "#10 valid_in=1; d_in=8'h10; #20 valid_in=0; #10 valid_in=1; d_in=8'h20; #10 valid_in=0; #30;",
                 "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0;",
                 "symptom": "FAIL: Pipeline Bubble Stalled Loss D1"},

                # Class E: Long Idle Gap & Adjacent Distractor - Positive match
                {"sub_id": "vl_e1", "class": "CLASS_E_IDLE_DISTRACTOR", "match": True, "exp_len": 12,
                 "stim": "#50; #10 valid_in=1; d_in=8'h88; #10 valid_in=0; #40 d_in=8'hFF; #30;",
                 "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0;",
                 "symptom": "FAIL: Pipeline Distractor Ingestion E1"},

                # Class F: Same Symptom / Different Defect (Negative)
                {"sub_id": "vl_f1", "class": "CLASS_F_SAME_SYMPTOM_NEG", "match": False, "exp_len": 6,
                 "stim": "#10 valid_in=1; d_in=8'h33; #10 valid_in=0; #30;",
                 "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= v1; d_out <= d_in;",
                 "symptom": "FAIL: Pipeline Drop Short A1"},
                {"sub_id": "vl_f2", "class": "CLASS_F_SAME_SYMPTOM_NEG", "match": False, "exp_len": 8,
                 "stim": "#10 valid_in=1; d_in=8'h77; #10 valid_in=0; #30;",
                 "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= v1; d_out <= 8'hFF;",
                 "symptom": "FAIL: Pipeline Delayed Stream Drop B1"},

                # Class G: Same Trigger / Different Mechanism (Negative)
                {"sub_id": "vl_g1", "class": "CLASS_G_SAME_TRIGGER_NEG", "match": False, "exp_len": 6,
                 "stim": "#10 valid_in=1; d_in=8'h44; #10 valid_in=0; #30;",
                 "rtl": "v1 <= 0; d1 <= d_in; valid_out <= 1; d_out <= d1;",
                 "symptom": "FAIL: Pipeline Spurious Valid G1"},

                # Class H: Same Low-Level Invariant / Different Semantics (Decisive Negative)
                {"sub_id": "vl_h1", "class": "CLASS_H_SAME_INVARIANT_NEG", "match": False, "exp_len": 6,
                 "stim": "#10 valid_in=0; #30 valid_in=1; d_in=8'h55; #30;",
                 "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= v1; d_out <= d1;",
                 "symptom": "FAIL: Unrelated Pipeline Data Timeout H1"},
                {"sub_id": "vl_h2", "class": "CLASS_H_SAME_INVARIANT_NEG", "match": False, "exp_len": 8,
                 "stim": "#20 valid_in=0; #20 valid_in=1; d_in=8'h66; #30;",
                 "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= v1; d_out <= d1;",
                 "symptom": "FAIL: Unrelated Pipeline Data Timeout H2"},

                # Class I: Incomplete / Truncated Trace (Safety -> INSUFFICIENT)
                {"sub_id": "vl_i1", "class": "CLASS_I_INCOMPLETE_EVIDENCE", "match": False, "exp_len": 2,
                 "stim": "#5 valid_in=0;",
                 "rtl": "valid_out <= 0;",
                 "symptom": "FAIL: Pipeline Truncated Trace I1"},
                {"sub_id": "vl_i2", "class": "CLASS_I_INCOMPLETE_EVIDENCE", "match": False, "exp_len": 3,
                 "stim": "#10 valid_in=1; d_in=8'h99;",
                 "rtl": "valid_out <= 0;",
                 "symptom": "FAIL: Pipeline Mid-Ingestion Abort I2"}
            ]
        },

        # UART Family (Documented Extractor Limitation: FIFO_STREAM context)
        {
            "family_id": "UART_BAUD_DIVIDER",
            "design": "uart",
            "source_id": "heldout_uart_src",
            "signals": ["cnt", "start", "tx"],
            "cases": [
                # Class A: Short
                {"sub_id": "vl_a1", "class": "CLASS_A_SHORT", "match": True, "exp_len": 4,
                 "stim": "#10 start=1; #40 start=0; #30;",
                 "rtl": "if (start) cnt <= cnt + 2; if (cnt == 7) tx <= ~tx;",
                 "symptom": "FAIL: UART Baud Rate Mismatch A1"},
                {"sub_id": "vl_a2", "class": "CLASS_A_SHORT", "match": True, "exp_len": 4,
                 "stim": "#10 start=1; #30 start=0; #30;",
                 "rtl": "if (start) cnt <= cnt + 2; if (cnt == 7) tx <= ~tx;",
                 "symptom": "FAIL: UART Framing Desync A2"},

                # Class B: Delayed Trigger
                {"sub_id": "vl_b1", "class": "CLASS_B_DELAYED", "match": True, "exp_len": 10,
                 "stim": "#50 start=0; #10 start=1; #40 start=0; #30;",
                 "rtl": "if (start) cnt <= cnt + 2; if (cnt == 7) tx <= ~tx;",
                 "symptom": "FAIL: UART Delayed Baud Defect B1"},
                {"sub_id": "vl_b2", "class": "CLASS_B_DELAYED", "match": True, "exp_len": 12,
                 "stim": "#70 start=0; #10 start=1; #40 start=0; #30;",
                 "rtl": "if (start) cnt <= cnt + 2; if (cnt == 7) tx <= ~tx;",
                 "symptom": "FAIL: UART Extended Preamble Defect B2"},

                # Class C: Long Multi-Beat Burst
                {"sub_id": "vl_c1", "class": "CLASS_C_MULTI_BEAT", "match": True, "exp_len": 14,
                 "stim": "#10 start=1; #80 start=0; #30;",
                 "rtl": "if (start) cnt <= cnt + 2; if (cnt == 7) tx <= ~tx;",
                 "symptom": "FAIL: UART Continuous Stream Error C1"},
                {"sub_id": "vl_c2", "class": "CLASS_C_MULTI_BEAT", "match": True, "exp_len": 16,
                 "stim": "#10 start=1; #100 start=0; #30;",
                 "rtl": "if (start) cnt <= cnt + 2; if (cnt == 7) tx <= ~tx;",
                 "symptom": "FAIL: UART Multi-Byte Bit Skew C2"},

                # Class D: Multi-Pulse Intermittent
                {"sub_id": "vl_d1", "class": "CLASS_D_STALL_BACKPRESSURE", "match": True, "exp_len": 10,
                 "stim": "#10 start=1; #20 start=0; #20 start=1; #40 start=0; #30;",
                 "rtl": "if (start) cnt <= cnt + 2; if (cnt == 7) tx <= ~tx;",
                 "symptom": "FAIL: UART Stalled Transfer Desync D1"},

                # Class E: Long Idle Gap
                {"sub_id": "vl_e1", "class": "CLASS_E_IDLE_DISTRACTOR", "match": True, "exp_len": 12,
                 "stim": "#60; #10 start=1; #40 start=0; #50;",
                 "rtl": "if (start) cnt <= cnt + 2; if (cnt == 7) tx <= ~tx;",
                 "symptom": "FAIL: UART Idle Distractor E1"},

                # Class F: Same Symptom (Negative)
                {"sub_id": "vl_f1", "class": "CLASS_F_SAME_SYMPTOM_NEG", "match": False, "exp_len": 6,
                 "stim": "#10 start=1; #40 start=0; #30;",
                 "rtl": "if (start) cnt <= 0; tx <= 0;",
                 "symptom": "FAIL: UART Baud Rate Mismatch A1"},
                {"sub_id": "vl_f2", "class": "CLASS_F_SAME_SYMPTOM_NEG", "match": False, "exp_len": 8,
                 "stim": "#10 start=1; #40 start=0; #30;",
                 "rtl": "if (start) cnt <= cnt + 1; tx <= 0;",
                 "symptom": "FAIL: UART Delayed Baud Defect B1"},

                # Class G: Same Trigger (Negative)
                {"sub_id": "vl_g1", "class": "CLASS_G_SAME_TRIGGER_NEG", "match": False, "exp_len": 6,
                 "stim": "#10 start=1; #40 start=0; #30;",
                 "rtl": "if (start) cnt <= cnt + 3; tx <= 1;",
                 "symptom": "FAIL: UART Sampling Error G1"},

                # Class H: Same Invariant (Decisive Negative)
                {"sub_id": "vl_h1", "class": "CLASS_H_SAME_INVARIANT_NEG", "match": False, "exp_len": 6,
                 "stim": "#30 start=0; #30;",
                 "rtl": "if (start) cnt <= cnt + 1; else cnt <= 0;",
                 "symptom": "FAIL: Unrelated UART Receiver Timeout H1"},
                {"sub_id": "vl_h2", "class": "CLASS_H_SAME_INVARIANT_NEG", "match": False, "exp_len": 8,
                 "stim": "#50 start=0; #30;",
                 "rtl": "if (start) cnt <= cnt + 1; else cnt <= 0;",
                 "symptom": "FAIL: Unrelated UART Receiver Timeout H2"},

                # Class I: Incomplete (Safety -> INSUFFICIENT)
                {"sub_id": "vl_i1", "class": "CLASS_I_INCOMPLETE_EVIDENCE", "match": False, "exp_len": 2,
                 "stim": "#5 start=0;",
                 "rtl": "cnt <= 0;",
                 "symptom": "FAIL: UART Truncated Trace I1"},
                {"sub_id": "vl_i2", "class": "CLASS_I_INCOMPLETE_EVIDENCE", "match": False, "exp_len": 3,
                 "stim": "#10 start=1;",
                 "rtl": "cnt <= 0;",
                 "symptom": "FAIL: UART Mid-Baud Abort I2"}
            ]
        }
    ]

    for d_cfg in designs_config:
        d_name = d_cfg["design"]
        fam_id = d_cfg["family_id"]
        src_id = d_cfg["source_id"]

        # Write Source failure files
        if d_name == "fifo":
            src_rtl = "module fifo(input clk, input rst_n, input write_en, input [7:0] write_data, input read_en, output reg [7:0] read_data, output full, output empty); reg [7:0] mem [0:15]; reg [4:0] write_ptr; reg [4:0] read_ptr; reg [5:0] count; assign full = (count == 16); assign empty = (count == 0); always @(posedge clk or negedge rst_n) begin if (!rst_n) begin write_ptr <= 0; read_ptr <= 0; count <= 0; end else begin if (write_en && !full) begin mem[write_ptr] <= write_data; write_ptr <= (write_ptr + 1) % 16; end if (read_en && !empty) begin read_data <= mem[read_ptr]; read_ptr <= (read_ptr + 1) % 16; end if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1; end end endmodule"
            src_tb = f'module tb; reg clk, rst_n, write_en, read_en; reg [7:0] write_data; wire [7:0] read_data; wire full, empty; fifo dut(.*); initial begin $dumpfile("{norm_base}/rtl/{src_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; write_en=0; read_en=0; write_data=8\'h11; #20 rst_n=1; #10 write_en=1; read_en=1; write_data=8\'h22; #20 $display("FAIL: Source FIFO Simultaneous RW"); #10 $finish; end always #5 clk=~clk; endmodule'
        elif d_name == "axi":
            src_rtl = "module axi_like(input clk, input rst_n, input valid_in, output ready_out, output reg valid_out, input ready_in); assign ready_out = 1; always @(posedge clk or negedge rst_n) begin if (!rst_n) valid_out <= 0; else begin if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1; end end endmodule"
            src_tb = f'module tb; reg clk, rst_n, valid_in, ready_in; wire ready_out, valid_out; axi_like dut(.*); initial begin $dumpfile("{norm_base}/rtl/{src_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; valid_in=0; ready_in=0; #20 rst_n=1; #10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=0; #20 $display("FAIL: Source AXI Handshake Hold"); #10 $finish; end always #5 clk=~clk; endmodule'
        elif d_name == "fsm":
            src_rtl = "module fsm(input clk, input rst_n, input start, output reg done); reg [1:0] state; always @(posedge clk or negedge rst_n) begin if (!rst_n) begin state <= 0; done <= 0; end else begin case(state) 0: if (start) begin state <= 0; end 1: state <= 2; 2: begin state <= 0; done <= 1; end endcase end end endmodule"
            src_tb = f'module tb; reg clk, rst_n, start; wire done; fsm dut(.*); initial begin $dumpfile("{norm_base}/rtl/{src_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; start=0; #20 rst_n=1; #10 start=1; #10 start=0; #20 $display("FAIL: Source FSM Stuck State"); #10 $finish; end always #5 clk=~clk; endmodule'
        elif d_name == "uart":
            src_rtl = "module uart(input clk, input rst_n, input start, output reg tx); reg [2:0] cnt; always @(posedge clk or negedge rst_n) begin if (!rst_n) begin cnt <= 0; tx <= 1; end else begin if (start) cnt <= cnt + 2; if (cnt == 7) tx <= ~tx; end end endmodule"
            src_tb = f'module tb; reg clk, rst_n, start; wire tx; uart dut(.*); initial begin $dumpfile("{norm_base}/rtl/{src_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; start=0; #20 rst_n=1; #10 start=1; #40 start=0; #20 $display("FAIL: Source UART Baud Divider"); #10 $finish; end always #5 clk=~clk; endmodule'
        else: # pipeline
            src_rtl = "module pipeline(input clk, input rst_n, input valid_in, input [7:0] d_in, output reg valid_out, output reg [7:0] d_out); reg v1; reg [7:0] d1; always @(posedge clk or negedge rst_n) begin if (!rst_n) begin v1 <= 0; valid_out <= 0; d1 <= 0; d_out <= 0; end else begin v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0; end end endmodule"
            src_tb = f'module tb; reg clk, rst_n, valid_in; reg [7:0] d_in; wire valid_out; wire [7:0] d_out; pipeline dut(.*); initial begin $dumpfile("{norm_base}/rtl/{src_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; valid_in=0; d_in=8\'h00; #20 rst_n=1; #10 valid_in=1; d_in=8\'hAA; #10 valid_in=0; #20 $display("FAIL: Source Pipeline Stall Bubble"); #10 $finish; end always #5 clk=~clk; endmodule'

        with open(os.path.join(designs_dir, f"{src_id}.v"), "w", encoding="utf-8") as f:
            f.write(src_rtl)
        with open(os.path.join(tb_dir, f"{src_id}_tb.v"), "w", encoding="utf-8") as f:
            f.write(src_tb)

        # Write Held-Out target instances
        for case in d_cfg["cases"]:
            t_id = f"{d_name}_{case['sub_id']}"
            is_match = case["match"]
            
            if d_name == "fifo":
                rtl_code = f"module fifo(input clk, input rst_n, input write_en, input [7:0] write_data, input read_en, output reg [7:0] read_data, output full, output empty); reg [7:0] mem [0:15]; reg [4:0] write_ptr; reg [4:0] read_ptr; reg [5:0] count; assign full = (count == 16); assign empty = (count == 0); always @(posedge clk or negedge rst_n) begin if (!rst_n) begin write_ptr <= 0; read_ptr <= 0; count <= 0; end else begin if (write_en && !full) begin mem[write_ptr] <= write_data; write_ptr <= (write_ptr + 1) % 16; end if (read_en && !empty) begin read_data <= mem[read_ptr]; read_ptr <= (read_ptr + 1) % 16; end {case['rtl']} end end endmodule"
                tb_code = f'module tb; reg clk, rst_n, write_en, read_en; reg [7:0] write_data; wire [7:0] read_data; wire full, empty; fifo dut(.*); initial begin $dumpfile("{norm_base}/rtl/{t_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; write_en=0; read_en=0; write_data=8\'h11; #20 rst_n=1; {case["stim"]} $display("{case["symptom"]}"); #10 $finish; end always #5 clk=~clk; endmodule'
            elif d_name == "axi":
                rtl_code = f"module axi_like(input clk, input rst_n, input valid_in, output ready_out, output reg valid_out, input ready_in); assign ready_out = 1; always @(posedge clk or negedge rst_n) begin if (!rst_n) valid_out <= 0; else begin {case['rtl']} end end endmodule"
                tb_code = f'module tb; reg clk, rst_n, valid_in, ready_in; wire ready_out, valid_out; axi_like dut(.*); initial begin $dumpfile("{norm_base}/rtl/{t_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; valid_in=0; ready_in=0; #20 rst_n=1; {case["stim"]} $display("{case["symptom"]}"); #10 $finish; end always #5 clk=~clk; endmodule'
            elif d_name == "fsm":
                rtl_code = f"module fsm(input clk, input rst_n, input start, output reg done); reg [1:0] state; always @(posedge clk or negedge rst_n) begin if (!rst_n) begin state <= 0; done <= 0; end else begin case(state) 0: if (start) begin {case['rtl']} end 1: state <= 2; 2: begin state <= 0; done <= 1; end endcase end end endmodule"
                tb_code = f'module tb; reg clk, rst_n, start; wire done; fsm dut(.*); initial begin $dumpfile("{norm_base}/rtl/{t_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; start=0; #20 rst_n=1; {case["stim"]} $display("{case["symptom"]}"); #10 $finish; end always #5 clk=~clk; endmodule'
            elif d_name == "uart":
                rtl_code = f"module uart(input clk, input rst_n, input start, output reg tx); reg [2:0] cnt; always @(posedge clk or negedge rst_n) begin if (!rst_n) begin cnt <= 0; tx <= 1; end else begin {case['rtl']} end end endmodule"
                tb_code = f'module tb; reg clk, rst_n, start; wire tx; uart dut(.*); initial begin $dumpfile("{norm_base}/rtl/{t_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; start=0; #20 rst_n=1; {case["stim"]} $display("{case["symptom"]}"); #10 $finish; end always #5 clk=~clk; endmodule'
            else: # pipeline
                rtl_code = f"module pipeline(input clk, input rst_n, input valid_in, input [7:0] d_in, output reg valid_out, output reg [7:0] d_out); reg v1; reg [7:0] d1; always @(posedge clk or negedge rst_n) begin if (!rst_n) begin v1 <= 0; valid_out <= 0; d1 <= 0; d_out <= 0; end else begin {case['rtl']} end end endmodule"
                tb_code = f'module tb; reg clk, rst_n, valid_in; reg [7:0] d_in; wire valid_out; wire [7:0] d_out; pipeline dut(.*); initial begin $dumpfile("{norm_base}/rtl/{t_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; valid_in=0; d_in=8\'h00; #20 rst_n=1; {case["stim"]} $display("{case["symptom"]}"); #10 $finish; end always #5 clk=~clk; endmodule'

            with open(os.path.join(designs_dir, f"{t_id}.v"), "w", encoding="utf-8") as f:
                f.write(rtl_code)
            with open(os.path.join(tb_dir, f"{t_id}_tb.v"), "w", encoding="utf-8") as f:
                f.write(tb_code)

            held_out_instances.append({
                "target_id": t_id,
                "family_id": fam_id,
                "design": d_name,
                "source_id": src_id,
                "transaction_class": case["class"],
                "ground_truth_match": "MATCH" if is_match else "MISMATCH",
                "expected_decision": "PASS" if is_match else ("INSUFFICIENT_EVIDENCE" if case["class"] == "CLASS_I_INCOMPLETE_EVIDENCE" else "FAIL"),
                "expected_tx_length": case["exp_len"],
                "defect_desc": case["symptom"],
                "target_signals": d_cfg["signals"]
            })

    # Save isolated ground truth metadata
    gt_path = os.path.join(bench_dir, "heldout_ground_truth.json")
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(held_out_instances, f, indent=2)

    # Save blinded target manifest (accessible during inference)
    blinded_manifest = [
        {"target_id": inst["target_id"], "design": inst["design"], "source_id": inst["source_id"], "target_signals": inst["target_signals"]}
        for inst in held_out_instances
    ]
    blind_path = os.path.join(bench_dir, "blinded_target_manifest.json")
    with open(blind_path, "w", encoding="utf-8") as f:
        json.dump(blinded_manifest, f, indent=2)

    print(f"Generated Phase 4.3 Variable-Latency Stress Benchmark: {len(held_out_instances)} failure instances across 5 designs & 9 transaction classes.")
    print(f"Isolated ground truth saved to: {gt_path}")
    print(f"Blinded target manifest saved to: {blind_path}")

if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generate_variable_latency_benchmark(base)
