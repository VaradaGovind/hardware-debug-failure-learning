import os
import json
import hashlib
import random

def sha256_file(filepath: str) -> str:
    if not os.path.exists(filepath):
        return "MISSING"
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def generate_phase4_1_benchmark(base_dir: str):
    blind_dir = os.path.join(base_dir, "results", "transaction_semantic_certs", "blind_validation")
    bench_dir = os.path.join(blind_dir, "benchmark")
    designs_dir = os.path.join(base_dir, "rtl", "designs")
    tb_dir = os.path.join(base_dir, "rtl", "testbenches")
    
    for d in [blind_dir, bench_dir, designs_dir, tb_dir]:
        os.makedirs(d, exist_ok=True)
        
    norm_base = base_dir.replace("\\", "/")
    
    # Hash and record immutable phase 4 validator manifest
    frozen_files = [
        os.path.join(base_dir, "src", "reuse", "transaction_semantic_certificate.py"),
        os.path.join(base_dir, "src", "reuse", "transaction_semantic_validator.py"),
        os.path.join(base_dir, "src", "reuse", "transaction_certificate_extractor.py"),
        os.path.join(base_dir, "src", "reuse", "generic_certificate.py"),
        os.path.join(base_dir, "src", "reuse", "remediated_certificate_validator.py"),
        os.path.join(base_dir, "src", "reuse", "scale_similarity_baselines.py")
    ]
    
    manifest = {
        "timestamp": "2026-08-15T15:40:00Z",
        "phase": "Argus Phase 4.1 Blind Held-Out Validation",
        "frozen_source_hashes": {os.path.basename(p): sha256_file(p) for p in frozen_files},
        "random_seeds": [101, 202, 303, 404, 505],
        "total_designs": 5,
        "design_families": ["FIFO", "AXI", "FSM", "UART", "PIPELINE"],
        "categories": ["A_SAME_DEFECT", "B_SAME_SYMPTOM", "C_SAME_TRIGGER", "D_SAME_INVARIANT_DIFF_SEMANTICS", "E_INSUFFICIENT_EVIDENCE", "F_UNRELATED"]
    }
    
    with open(os.path.join(blind_dir, "frozen_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Recorded Frozen Manifest with SHA256 hashes in {os.path.join(blind_dir, 'frozen_manifest.json')}")

    # GENERATE 50+ UNSEEN HELD-OUT INSTANCES (10 per design family)
    
    held_out_instances = []
    
    # 5 Designs x 10 cases each = 50 total held-out failure instances
    # Plus 5 source failures for certificate extraction = 55 total
    
    designs_config = [
        # FIFO Family (Simultaneous R/W Defect: Count fails to hold)
        {
            "family_id": "FIFO_SIMULTANEOUS_RW",
            "design": "fifo",
            "source_id": "heldout_fifo_src",
            "signals": ["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"],
            "cases": [
                # Category A: Same Defect / Different Manifestation (3 cases)
                {"sub_id": "a1", "cat": "A_SAME_DEFECT", "match": True, "stim": "#10 write_en=1; read_en=1; write_data=8'h33; #10 write_en=1; read_en=1; write_data=8'h44; #10 write_en=0; read_en=0;", "rtl": "if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;", "symptom": "FAIL: FIFO Buffer Overrun Manifestation A1"},
                {"sub_id": "a2", "cat": "A_SAME_DEFECT", "match": True, "stim": "#20 write_en=1; read_en=1; write_data=8'h77; #10 write_en=0; read_en=0;", "rtl": "if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;", "symptom": "FAIL: FIFO Capacity Mismatch A2"},
                {"sub_id": "a3", "cat": "A_SAME_DEFECT", "match": True, "stim": "#10 write_en=1; write_data=8'h11; #10 write_en=1; read_en=1; write_data=8'h22; #10 write_en=0; read_en=0;", "rtl": "if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;", "symptom": "FAIL: FIFO Desync A3"},
                # Category B: Same Symptom / Different Defect (2 cases)
                {"sub_id": "b1", "cat": "B_SAME_DEFECT", "match": False, "stim": "#10 write_en=1; write_data=8'h11; #10 read_en=1; #10 write_en=0; read_en=0;", "rtl": "if (read_en && !empty) count <= 0; else if (write_en && !full) count <= count + 1;", "symptom": "FAIL: FIFO Buffer Overrun Manifestation A1"},
                {"sub_id": "b2", "cat": "B_SAME_DEFECT", "match": False, "stim": "#10 write_en=1; write_data=8'h22; #10 write_en=0;", "rtl": "if (write_en && !full) count <= count + 2;", "symptom": "FAIL: FIFO Capacity Mismatch A2"},
                # Category C: Same Trigger / Different Mechanism (1 case)
                {"sub_id": "c1", "cat": "C_SAME_TRIGGER", "match": False, "stim": "#10 write_en=1; read_en=1; write_data=8'h55; #10 write_en=0; read_en=0;", "rtl": "if (write_en && read_en) write_ptr <= write_ptr + 2; if (write_en && !full && read_en && !empty) count <= count;", "symptom": "FAIL: FIFO Pointer Corruption C1"},
                # Category D: Same Low-Level Invariant / Different Transaction Meaning (2 cases - DECISIVE CONTROL)
                # Count increments by 1 during single write (legitimate invariant, but simultaneous RW was not active)
                {"sub_id": "d1", "cat": "D_SAME_INVARIANT_DIFF_SEMANTICS", "match": False, "stim": "#10 write_en=1; read_en=0; write_data=8'hAA; #10 write_en=0;", "rtl": "if (write_en && !full && read_en && !empty) count <= count; else if (write_en && !full) count <= count + 1;", "symptom": "FAIL: Unrelated Testbench Check D1"},
                {"sub_id": "d2", "cat": "D_SAME_INVARIANT_DIFF_SEMANTICS", "match": False, "stim": "#10 write_en=1; read_en=0; write_data=8'hBB; #10 write_en=0;", "rtl": "if (write_en && !full && read_en && !empty) count <= count; else if (write_en && !full) count <= count + 1;", "symptom": "FAIL: Unrelated Testbench Check D2"},
                # Category E: Insufficient Evidence (1 case)
                {"sub_id": "e1", "cat": "E_INSUFFICIENT_EVIDENCE", "match": False, "stim": "#5 write_en=0; read_en=0;", "rtl": "if (write_en && !full) count <= count + 1;", "symptom": "FAIL: Early Testbench Abort E1"},
                # Category F: Genuine Unrelated Failure (1 case)
                {"sub_id": "f1", "cat": "F_UNRELATED", "match": False, "stim": "#10 write_en=1; write_data=8'hFF;", "rtl": "if (write_en) read_data <= 8'h00;", "symptom": "FAIL: Read Data Line Bus Glitch F1"}
            ]
        },

        # AXI Family (Handshake Hold Defect: valid_out drops during backpressure)
        {
            "family_id": "AXI_HANDSHAKE_HOLD",
            "design": "axi",
            "source_id": "heldout_axi_src",
            "signals": ["valid_in", "ready_in", "valid_out", "ready_out"],
            "cases": [
                # Category A: Same Defect / Different Manifestation (3 cases)
                {"sub_id": "a1", "cat": "A_SAME_DEFECT", "match": True, "stim": "#10 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=0; #10 valid_in=0;", "rtl": "if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;", "symptom": "FAIL: AXI Transfer Dropped A1"},
                {"sub_id": "a2", "cat": "A_SAME_DEFECT", "match": True, "stim": "#20 valid_in=1; ready_in=1; #10 valid_in=1; ready_in=0; #10 valid_in=0;", "rtl": "if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;", "symptom": "FAIL: AXI Backpressure Mismatch A2"},
                {"sub_id": "a3", "cat": "A_SAME_DEFECT", "match": True, "stim": "#10 valid_in=1; ready_in=0; #10 valid_in=0;", "rtl": "if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;", "symptom": "FAIL: AXI Protocol Lock A3"},
                # Category B: Same Symptom / Different Defect (2 cases)
                {"sub_id": "b1", "cat": "B_SAME_DEFECT", "match": False, "stim": "#10 valid_in=1; ready_in=1; #10 valid_in=0;", "rtl": "valid_out <= 0;", "symptom": "FAIL: AXI Transfer Dropped A1"},
                {"sub_id": "b2", "cat": "B_SAME_DEFECT", "match": False, "stim": "#10 valid_in=1; ready_in=1; #10 valid_in=0;", "rtl": "valid_out <= ~valid_in;", "symptom": "FAIL: AXI Backpressure Mismatch A2"},
                # Category C: Same Trigger / Different Mechanism (1 case)
                {"sub_id": "c1", "cat": "C_SAME_TRIGGER", "match": False, "stim": "#10 valid_in=1; ready_in=0; #10 valid_in=0;", "rtl": "if (valid_in && !ready_in) ready_out <= 0; else valid_out <= 1;", "symptom": "FAIL: AXI Slave Stall C1"},
                # Category D: Same Low-Level Invariant / Different Transaction Meaning (2 cases - DECISIVE CONTROL)
                {"sub_id": "d1", "cat": "D_SAME_INVARIANT_DIFF_SEMANTICS", "match": False, "stim": "#10 valid_in=0; ready_in=0;", "rtl": "if (valid_in) valid_out <= 1; else valid_out <= 0;", "symptom": "FAIL: Unrelated Bus Timeout D1"},
                {"sub_id": "d2", "cat": "D_SAME_INVARIANT_DIFF_SEMANTICS", "match": False, "stim": "#10 valid_in=0; ready_in=1;", "rtl": "if (valid_in) valid_out <= 1; else valid_out <= 0;", "symptom": "FAIL: Unrelated Bus Timeout D2"},
                # Category E: Insufficient Evidence (1 case)
                {"sub_id": "e1", "cat": "E_INSUFFICIENT_EVIDENCE", "match": False, "stim": "#5 valid_in=0; ready_in=0;", "rtl": "valid_out <= valid_in;", "symptom": "FAIL: Truncated Waveform E1"},
                # Category F: Genuine Unrelated Failure (1 case)
                {"sub_id": "f1", "cat": "F_UNRELATED", "match": False, "stim": "#10 valid_in=1; ready_in=1;", "rtl": "ready_out <= 0;", "symptom": "FAIL: AXI Ready Deasserted Glitch F1"}
            ]
        },

        # FSM Family (Stuck State Defect: State fails to leave IDLE on start)
        {
            "family_id": "FSM_STUCK_STATE",
            "design": "fsm",
            "source_id": "heldout_fsm_src",
            "signals": ["state", "start", "done"],
            "cases": [
                # Category A: Same Defect / Different Manifestation (3 cases)
                {"sub_id": "a1", "cat": "A_SAME_DEFECT", "match": True, "stim": "#15 start=1; #10 start=0; #30;", "rtl": "state <= 0;", "symptom": "FAIL: FSM Deadlock A1"},
                {"sub_id": "a2", "cat": "A_SAME_DEFECT", "match": True, "stim": "#25 start=1; #10 start=0; #20;", "rtl": "state <= 0;", "symptom": "FAIL: FSM State Hang A2"},
                {"sub_id": "a3", "cat": "A_SAME_DEFECT", "match": True, "stim": "#10 start=1; #10 start=0; #10 start=1; #10 start=0;", "rtl": "state <= 0;", "symptom": "FAIL: FSM Inactive A3"},
                # Category B: Same Symptom / Different Defect (2 cases)
                {"sub_id": "b1", "cat": "B_SAME_DEFECT", "match": False, "stim": "#10 start=1; #10 start=0; #30;", "rtl": "state <= 1;", "symptom": "FAIL: FSM Deadlock A1"},
                {"sub_id": "b2", "cat": "B_SAME_DEFECT", "match": False, "stim": "#10 start=1; #10 start=0; #30;", "rtl": "state <= 2;", "symptom": "FAIL: FSM State Hang A2"},
                # Category C: Same Trigger / Different Mechanism (1 case)
                {"sub_id": "c1", "cat": "C_SAME_TRIGGER", "match": False, "stim": "#10 start=1; #10 start=0; #30;", "rtl": "state <= 1; done <= 1;", "symptom": "FAIL: FSM Premature Done C1"},
                # Category D: Same Low-Level Invariant / Different Transaction Meaning (2 cases - DECISIVE CONTROL)
                {"sub_id": "d1", "cat": "D_SAME_INVARIANT_DIFF_SEMANTICS", "match": False, "stim": "#40 start=0;", "rtl": "if (start) state <= 1; else state <= 0;", "symptom": "FAIL: Unrelated Timer Expiry D1"},
                {"sub_id": "d2", "cat": "D_SAME_INVARIANT_DIFF_SEMANTICS", "match": False, "stim": "#50 start=0;", "rtl": "if (start) state <= 1; else state <= 0;", "symptom": "FAIL: Unrelated Timer Expiry D2"},
                # Category E: Insufficient Evidence (1 case)
                {"sub_id": "e1", "cat": "E_INSUFFICIENT_EVIDENCE", "match": False, "stim": "#5 start=0;", "rtl": "state <= 0;", "symptom": "FAIL: FSM Waveform Truncated E1"},
                # Category F: Genuine Unrelated Failure (1 case)
                {"sub_id": "f1", "cat": "F_UNRELATED", "match": False, "stim": "#10 start=1; #10 start=0;", "rtl": "done <= 0;", "symptom": "FAIL: Done Pulse Missing F1"}
            ]
        },

        # UART Family (Baud Divider Defect: Step by 2 instead of 1)
        {
            "family_id": "UART_BAUD_DIVIDER",
            "design": "uart",
            "source_id": "heldout_uart_src",
            "signals": ["cnt", "start", "tx"],
            "cases": [
                # Category A: Same Defect / Different Manifestation (3 cases)
                {"sub_id": "a1", "cat": "A_SAME_DEFECT", "match": True, "stim": "#15 start=1; #40 start=0;", "rtl": "if (start) cnt <= cnt + 2; if (cnt == 7) tx <= ~tx;", "symptom": "FAIL: UART Baud Rate Mismatch A1"},
                {"sub_id": "a2", "cat": "A_SAME_DEFECT", "match": True, "stim": "#25 start=1; #30 start=0;", "rtl": "if (start) cnt <= cnt + 2; if (cnt == 7) tx <= ~tx;", "symptom": "FAIL: UART Framing Desync A2"},
                {"sub_id": "a3", "cat": "A_SAME_DEFECT", "match": True, "stim": "#10 start=1; #50 start=0;", "rtl": "if (start) cnt <= cnt + 2; if (cnt == 7) tx <= ~tx;", "symptom": "FAIL: UART Bit Skew A3"},
                # Category B: Same Symptom / Different Defect (2 cases)
                {"sub_id": "b1", "cat": "B_SAME_DEFECT", "match": False, "stim": "#10 start=1; #40 start=0;", "rtl": "if (start) cnt <= 0; tx <= 0;", "symptom": "FAIL: UART Baud Rate Mismatch A1"},
                {"sub_id": "b2", "cat": "B_SAME_DEFECT", "match": False, "stim": "#10 start=1; #40 start=0;", "rtl": "if (start) cnt <= cnt + 1; tx <= 0;", "symptom": "FAIL: UART Framing Desync A2"},
                # Category C: Same Trigger / Different Mechanism (1 case)
                {"sub_id": "c1", "cat": "C_SAME_TRIGGER", "match": False, "stim": "#10 start=1; #40 start=0;", "rtl": "if (start) cnt <= cnt + 3; tx <= 1;", "symptom": "FAIL: UART Sampling Error C1"},
                # Category D: Same Low-Level Invariant / Different Transaction Meaning (2 cases - DECISIVE CONTROL)
                {"sub_id": "d1", "cat": "D_SAME_INVARIANT_DIFF_SEMANTICS", "match": False, "stim": "#30 start=0;", "rtl": "if (start) cnt <= cnt + 1; else cnt <= 0;", "symptom": "FAIL: Unrelated Receiver Timeout D1"},
                {"sub_id": "d2", "cat": "D_SAME_INVARIANT_DIFF_SEMANTICS", "match": False, "stim": "#40 start=0;", "rtl": "if (start) cnt <= cnt + 1; else cnt <= 0;", "symptom": "FAIL: Unrelated Receiver Timeout D2"},
                # Category E: Insufficient Evidence (1 case)
                {"sub_id": "e1", "cat": "E_INSUFFICIENT_EVIDENCE", "match": False, "stim": "#5 start=0;", "rtl": "cnt <= 0;", "symptom": "FAIL: UART Truncated E1"},
                # Category F: Genuine Unrelated Failure (1 case)
                {"sub_id": "f1", "cat": "F_UNRELATED", "match": False, "stim": "#10 start=1;", "rtl": "tx <= 0;", "symptom": "FAIL: Stop Bit Low Glitch F1"}
            ]
        },

        # Pipeline Family (Stall Bubble Defect: valid_out dropped during active stream)
        {
            "family_id": "PIPE_STALL_BUBBLE",
            "design": "pipeline",
            "source_id": "heldout_pipe_src",
            "signals": ["valid_in", "d_in", "v1", "d1", "valid_out", "d_out"],
            "cases": [
                # Category A: Same Defect / Different Manifestation (3 cases)
                {"sub_id": "a1", "cat": "A_SAME_DEFECT", "match": True, "stim": "#15 valid_in=1; d_in=8'h33; #10 valid_in=0; #20;", "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0;", "symptom": "FAIL: Pipeline Drop A1"},
                {"sub_id": "a2", "cat": "A_SAME_DEFECT", "match": True, "stim": "#25 valid_in=1; d_in=8'h77; #10 valid_in=0; #20;", "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0;", "symptom": "FAIL: Pipeline Throughput Loss A2"},
                {"sub_id": "a3", "cat": "A_SAME_DEFECT", "match": True, "stim": "#10 valid_in=1; d_in=8'h11; #10 valid_in=1; d_in=8'h22; #10 valid_in=0; #20;", "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= 0; d_out <= 0;", "symptom": "FAIL: Pipeline Bubble Stall A3"},
                # Category B: Same Symptom / Different Defect (2 cases)
                {"sub_id": "b1", "cat": "B_SAME_DEFECT", "match": False, "stim": "#10 valid_in=1; d_in=8'h33; #10 valid_in=0;", "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= v1; d_out <= d_in;", "symptom": "FAIL: Pipeline Drop A1"},
                {"sub_id": "b2", "cat": "B_SAME_DEFECT", "match": False, "stim": "#10 valid_in=1; d_in=8'h77; #10 valid_in=0;", "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= v1; d_out <= 8'hFF;", "symptom": "FAIL: Pipeline Throughput Loss A2"},
                # Category C: Same Trigger / Different Mechanism (1 case)
                {"sub_id": "c1", "cat": "C_SAME_TRIGGER", "match": False, "stim": "#10 valid_in=1; d_in=8'h44; #10 valid_in=0;", "rtl": "v1 <= 0; d1 <= d_in; valid_out <= 1; d_out <= d1;", "symptom": "FAIL: Pipeline Spurious Valid C1"},
                # Category D: Same Low-Level Invariant / Different Transaction Meaning (2 cases - DECISIVE CONTROL)
                {"sub_id": "d1", "cat": "D_SAME_INVARIANT_DIFF_SEMANTICS", "match": False, "stim": "#10 valid_in=0; #30 valid_in=1; d_in=8'h55;", "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= v1; d_out <= d1;", "symptom": "FAIL: Unrelated Data Timeout D1"},
                {"sub_id": "d2", "cat": "D_SAME_INVARIANT_DIFF_SEMANTICS", "match": False, "stim": "#20 valid_in=0; #20 valid_in=1; d_in=8'h66;", "rtl": "v1 <= valid_in; d1 <= d_in; valid_out <= v1; d_out <= d1;", "symptom": "FAIL: Unrelated Data Timeout D2"},
                # Category E: Insufficient Evidence (1 case)
                {"sub_id": "e1", "cat": "E_INSUFFICIENT_EVIDENCE", "match": False, "stim": "#5 valid_in=0;", "rtl": "valid_out <= 0;", "symptom": "FAIL: Pipeline Truncated E1"},
                # Category F: Genuine Unrelated Failure (1 case)
                {"sub_id": "f1", "cat": "F_UNRELATED", "match": False, "stim": "#10 valid_in=1; d_in=8'h99;", "rtl": "v1 <= valid_in; d1 <= 8'h00; valid_out <= v1; d_out <= d1;", "symptom": "FAIL: Payload Zero Clamping F1"}
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
                tb_code = f'module tb; reg clk, rst_n, write_en, read_en; reg [7:0] write_data; wire [7:0] read_data; wire full, empty; fifo dut(.*); initial begin $dumpfile("{norm_base}/rtl/{t_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; write_en=0; read_en=0; write_data=8\'h11; #20 rst_n=1; {case["stim"]} #20; $display("{case["symptom"]}"); #10 $finish; end always #5 clk=~clk; endmodule'
            elif d_name == "axi":
                rtl_code = f"module axi_like(input clk, input rst_n, input valid_in, output ready_out, output reg valid_out, input ready_in); assign ready_out = 1; always @(posedge clk or negedge rst_n) begin if (!rst_n) valid_out <= 0; else begin {case['rtl']} end end endmodule"
                tb_code = f'module tb; reg clk, rst_n, valid_in, ready_in; wire ready_out, valid_out; axi_like dut(.*); initial begin $dumpfile("{norm_base}/rtl/{t_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; valid_in=0; ready_in=0; #20 rst_n=1; {case["stim"]} #20; $display("{case["symptom"]}"); #10 $finish; end always #5 clk=~clk; endmodule'
            elif d_name == "fsm":
                rtl_code = f"module fsm(input clk, input rst_n, input start, output reg done); reg [1:0] state; always @(posedge clk or negedge rst_n) begin if (!rst_n) begin state <= 0; done <= 0; end else begin case(state) 0: if (start) begin {case['rtl']} end 1: state <= 2; 2: begin state <= 0; done <= 1; end endcase end end endmodule"
                tb_code = f'module tb; reg clk, rst_n, start; wire done; fsm dut(.*); initial begin $dumpfile("{norm_base}/rtl/{t_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; start=0; #20 rst_n=1; {case["stim"]} #20; $display("{case["symptom"]}"); #10 $finish; end always #5 clk=~clk; endmodule'
            elif d_name == "uart":
                rtl_code = f"module uart(input clk, input rst_n, input start, output reg tx); reg [2:0] cnt; always @(posedge clk or negedge rst_n) begin if (!rst_n) begin cnt <= 0; tx <= 1; end else begin {case['rtl']} end end endmodule"
                tb_code = f'module tb; reg clk, rst_n, start; wire tx; uart dut(.*); initial begin $dumpfile("{norm_base}/rtl/{t_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; start=0; #20 rst_n=1; {case["stim"]} #20; $display("{case["symptom"]}"); #10 $finish; end always #5 clk=~clk; endmodule'
            else: # pipeline
                rtl_code = f"module pipeline(input clk, input rst_n, input valid_in, input [7:0] d_in, output reg valid_out, output reg [7:0] d_out); reg v1; reg [7:0] d1; always @(posedge clk or negedge rst_n) begin if (!rst_n) begin v1 <= 0; valid_out <= 0; d1 <= 0; d_out <= 0; end else begin {case['rtl']} end end endmodule"
                tb_code = f'module tb; reg clk, rst_n, valid_in; reg [7:0] d_in; wire valid_out; wire [7:0] d_out; pipeline dut(.*); initial begin $dumpfile("{norm_base}/rtl/{t_id}.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; valid_in=0; d_in=8\'h00; #20 rst_n=1; {case["stim"]} #20; $display("{case["symptom"]}"); #10 $finish; end always #5 clk=~clk; endmodule'

            with open(os.path.join(designs_dir, f"{t_id}.v"), "w", encoding="utf-8") as f:
                f.write(rtl_code)
            with open(os.path.join(tb_dir, f"{t_id}_tb.v"), "w", encoding="utf-8") as f:
                f.write(tb_code)

            held_out_instances.append({
                "target_id": t_id,
                "family_id": fam_id,
                "design": d_name,
                "source_id": src_id,
                "category": case["cat"],
                "ground_truth_match": "MATCH" if is_match else "MISMATCH",
                "expected_decision": "PASS" if is_match else ("INSUFFICIENT_EVIDENCE" if case["cat"] == "E_INSUFFICIENT_EVIDENCE" else "FAIL"),
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

    print(f"Generated Phase 4.1 Blind Held-Out Benchmark: {len(held_out_instances)} unseen failure instances across 5 designs.")
    print(f"Isolated ground truth saved to: {gt_path}")
    print(f"Blinded target manifest saved to: {blind_path}")

if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generate_phase4_1_benchmark(base)
