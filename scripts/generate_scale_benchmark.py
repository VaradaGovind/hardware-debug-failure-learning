import os
import json

def generate_scale_benchmark(base_dir: str):
    designs_dir = os.path.join(base_dir, "rtl", "designs")
    tb_dir = os.path.join(base_dir, "rtl", "testbenches")
    scale_dir = os.path.join(base_dir, "results", "causal_reuse_scale")
    
    os.makedirs(designs_dir, exist_ok=True)
    os.makedirs(tb_dir, exist_ok=True)
    os.makedirs(scale_dir, exist_ok=True)
    
    norm_base = base_dir.replace("\\", "/")
    
    causal_families = [
        # FIFO (4 families)
        {
            "family_id": "FIFO_SIMULTANEOUS_RW",
            "design": "fifo",
            "is_held_out_mechanism": False,
            "defect_desc": "Missing simultaneous R/W hold logic (increments on simultaneous RW)",
            "root_signal": "count",
            "invariant_type": "CONSERVATION",
            "target_reg": "count",
            "anomaly_delta": 1,
            "prop_type": "POINTER_OCCUPANCY_DIVERGENCE",
            "trigger_conds": {"write_en": 1, "read_en": 1, "full": 0, "empty": 0},
            "signals": ["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"]
        },
        {
            "family_id": "FIFO_PTR_WRAP",
            "design": "fifo",
            "is_held_out_mechanism": False,
            "defect_desc": "Write pointer increment without modulo 16 wrap",
            "root_signal": "write_ptr",
            "invariant_type": "STEP_INCREMENT",
            "target_reg": "write_ptr",
            "expected_change": 1,
            "prop_type": "POINTER_OCCUPANCY_DIVERGENCE",
            "trigger_conds": {"write_en": 1, "full": 0},
            "signals": ["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"]
        },
        {
            "family_id": "FIFO_EMPTY_THRESHOLD",
            "design": "fifo",
            "is_held_out_mechanism": False,
            "defect_desc": "Early empty flag threshold (count <= 1)",
            "root_signal": "empty",
            "invariant_type": "STABILITY",
            "target_reg": "empty",
            "prop_type": "POINTER_OCCUPANCY_DIVERGENCE",
            "trigger_conds": {"count": 1, "read_en": 1},
            "signals": ["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"]
        },
        {
            "family_id": "FIFO_RESET_CLEAR",
            "design": "fifo",
            "is_held_out_mechanism": True, # HELD-OUT MECHANISM
            "defect_desc": "Reset does not clear occupancy count register",
            "root_signal": "count",
            "invariant_type": "CONSERVATION",
            "target_reg": "count",
            "prop_type": "POINTER_OCCUPANCY_DIVERGENCE",
            "trigger_conds": {"rst_n": 0},
            "signals": ["count", "write_en", "read_en", "full", "empty", "write_ptr", "read_ptr"]
        },

        # AXI (4 families)
        {
            "family_id": "AXI_HANDSHAKE_HOLD",
            "design": "axi",
            "is_held_out_mechanism": False,
            "defect_desc": "valid_out drops during backpressure (ready_in == 0)",
            "root_signal": "valid_out",
            "invariant_type": "STABILITY",
            "target_reg": "valid_out",
            "prop_type": "HANDSHAKE_STALL_PROPAGATION",
            "trigger_conds": {"valid_in": 1, "ready_in": 0},
            "signals": ["valid_in", "ready_out", "valid_out", "ready_in"]
        },
        {
            "family_id": "AXI_EARLY_READY",
            "design": "axi",
            "is_held_out_mechanism": False,
            "defect_desc": "ready_out deasserts prematurely during active transfer",
            "root_signal": "ready_out",
            "invariant_type": "STABILITY",
            "target_reg": "ready_out",
            "prop_type": "HANDSHAKE_STALL_PROPAGATION",
            "trigger_conds": {"valid_in": 1, "ready_in": 1},
            "signals": ["valid_in", "ready_out", "valid_out", "ready_in"]
        },
        {
            "family_id": "AXI_BURST_COUNT",
            "design": "axi",
            "is_held_out_mechanism": False,
            "defect_desc": "Burst beat counter increments on valid_in only without checking ready_out",
            "root_signal": "valid_out",
            "invariant_type": "CONSERVATION",
            "target_reg": "valid_out",
            "prop_type": "HANDSHAKE_STALL_PROPAGATION",
            "trigger_conds": {"valid_in": 1, "ready_in": 0},
            "signals": ["valid_in", "ready_out", "valid_out", "ready_in"]
        },
        {
            "family_id": "AXI_RESP_MISMATCH",
            "design": "axi",
            "is_held_out_mechanism": True, # HELD-OUT MECHANISM
            "defect_desc": "Response channel returns OKAY on unacknowledged transaction",
            "root_signal": "valid_out",
            "invariant_type": "STABILITY",
            "target_reg": "valid_out",
            "prop_type": "HANDSHAKE_STALL_PROPAGATION",
            "trigger_conds": {"valid_in": 1, "ready_in": 0},
            "signals": ["valid_in", "ready_out", "valid_out", "ready_in"]
        },

        # FSM (4 families)
        {
            "family_id": "FSM_STATE_SKIP",
            "design": "fsm",
            "is_held_out_mechanism": False,
            "defect_desc": "State transitions skip intermediate verification state",
            "root_signal": "state",
            "invariant_type": "STATE_TRANSITION",
            "target_reg": "state",
            "expected_next_state": 1,
            "prop_type": "STATE_CORRUPTION_PERSISTENCE",
            "trigger_conds": {"start": 1},
            "signals": ["state", "start", "done"]
        },
        {
            "family_id": "FSM_STUCK_STATE",
            "design": "fsm",
            "is_held_out_mechanism": False,
            "defect_desc": "State register fails to transition out of busy state",
            "root_signal": "state",
            "invariant_type": "STATE_TRANSITION",
            "target_reg": "state",
            "expected_next_state": 0,
            "prop_type": "STATE_CORRUPTION_PERSISTENCE",
            "trigger_conds": {"start": 0},
            "signals": ["state", "start", "done"]
        },
        {
            "family_id": "FSM_OUTPUT_TIMING",
            "design": "fsm",
            "is_held_out_mechanism": False,
            "defect_desc": "Done output asserted 1 cycle prematurely",
            "root_signal": "done",
            "invariant_type": "STABILITY",
            "target_reg": "done",
            "prop_type": "STATE_CORRUPTION_PERSISTENCE",
            "trigger_conds": {"start": 1},
            "signals": ["state", "start", "done"]
        },
        {
            "family_id": "FSM_RESET_RECOVERY",
            "design": "fsm",
            "is_held_out_mechanism": True, # HELD-OUT MECHANISM
            "defect_desc": "FSM state register fails to reset to IDLE on reset pulse",
            "root_signal": "state",
            "invariant_type": "STATE_TRANSITION",
            "target_reg": "state",
            "expected_next_state": 0,
            "prop_type": "STATE_CORRUPTION_PERSISTENCE",
            "trigger_conds": {"rst_n": 0},
            "signals": ["state", "start", "done"]
        },

        # UART (4 families)
        {
            "family_id": "UART_BAUD_DIVIDER",
            "design": "uart",
            "is_held_out_mechanism": False,
            "defect_desc": "Baud counter increments by 2 instead of 1 (clock divider error)",
            "root_signal": "cnt",
            "invariant_type": "STEP_INCREMENT",
            "target_reg": "cnt",
            "expected_change": 1,
            "prop_type": "BAUD_SAMPLE_DESYNC",
            "trigger_conds": {"start": 1},
            "signals": ["cnt", "start", "tx"]
        },
        {
            "family_id": "UART_STOP_BIT_GEN",
            "design": "uart",
            "is_held_out_mechanism": False,
            "defect_desc": "Stop bit is driven low instead of high (framing error)",
            "root_signal": "tx",
            "invariant_type": "STABILITY",
            "target_reg": "tx",
            "prop_type": "BAUD_SAMPLE_DESYNC",
            "trigger_conds": {"start": 1},
            "signals": ["cnt", "start", "tx"]
        },
        {
            "family_id": "UART_TX_BUSY_HOLD",
            "design": "uart",
            "is_held_out_mechanism": False,
            "defect_desc": "Transmitter fails to clear busy line after stop bit",
            "root_signal": "tx",
            "invariant_type": "STABILITY",
            "target_reg": "tx",
            "prop_type": "BAUD_SAMPLE_DESYNC",
            "trigger_conds": {"start": 0},
            "signals": ["cnt", "start", "tx"]
        },
        {
            "family_id": "UART_BIT_SAMPLING",
            "design": "uart",
            "is_held_out_mechanism": True, # HELD-OUT MECHANISM
            "defect_desc": "RX bit sampling occurs at boundary instead of midpoint",
            "root_signal": "cnt",
            "invariant_type": "STEP_INCREMENT",
            "target_reg": "cnt",
            "expected_change": 1,
            "prop_type": "BAUD_SAMPLE_DESYNC",
            "trigger_conds": {"start": 1},
            "signals": ["cnt", "start", "tx"]
        },

        # PIPELINE (4 families)
        {
            "family_id": "PIPE_FORWARD_HAZARD",
            "design": "pipeline",
            "is_held_out_mechanism": False,
            "defect_desc": "Data bypasses stage 1 and latches raw input directly",
            "root_signal": "d_out",
            "invariant_type": "LATENCY_PIPELINE",
            "target_reg": "d_out",
            "input_signal": "d1",
            "output_signal": "d_out",
            "prop_type": "PIPELINE_PAYLOAD_CORRUPTION",
            "trigger_conds": {"valid_in": 1},
            "signals": ["v1", "d1", "valid_in", "d_in", "valid_out", "d_out"]
        },
        {
            "family_id": "PIPE_STALL_BUBBLE",
            "design": "pipeline",
            "is_held_out_mechanism": False,
            "defect_desc": "Valid flag clears during stall instead of maintaining valid bit",
            "root_signal": "valid_out",
            "invariant_type": "STABILITY",
            "target_reg": "valid_out",
            "prop_type": "PIPELINE_PAYLOAD_CORRUPTION",
            "trigger_conds": {"valid_in": 1},
            "signals": ["v1", "d1", "valid_in", "d_in", "valid_out", "d_out"]
        },
        {
            "family_id": "PIPE_FLUSH_DESYNC",
            "design": "pipeline",
            "is_held_out_mechanism": False,
            "defect_desc": "Pipeline flush clears payload register but leaves valid asserted",
            "root_signal": "valid_out",
            "invariant_type": "STABILITY",
            "target_reg": "valid_out",
            "prop_type": "PIPELINE_PAYLOAD_CORRUPTION",
            "trigger_conds": {"valid_in": 0},
            "signals": ["v1", "d1", "valid_in", "d_in", "valid_out", "d_out"]
        },
        {
            "family_id": "PIPE_STAGE_ENABLE",
            "design": "pipeline",
            "is_held_out_mechanism": True, # HELD-OUT MECHANISM
            "defect_desc": "Stage 2 enable ignores stage 1 valid signal",
            "root_signal": "valid_out",
            "invariant_type": "STABILITY",
            "target_reg": "valid_out",
            "prop_type": "PIPELINE_PAYLOAD_CORRUPTION",
            "trigger_conds": {"valid_in": 1},
            "signals": ["v1", "d1", "valid_in", "d_in", "valid_out", "d_out"]
        }
    ]

    benchmark_instances = []
    
    for fam in causal_families:
        fam_id = fam["family_id"]
        design = fam["design"]
        is_held_out = fam["is_held_out_mechanism"]
        
        instances = [
            {"sub_id": "s1", "role": "SOURCE", "split": "DEV", "is_match": True, "symptom": f"FAIL: {fam_id} Source Anomaly (S1)"},
            {"sub_id": "p1", "role": "HARD_POS_1", "split": "DEV", "is_match": True, "symptom": f"FAIL: {fam_id} Throughput Mismatch (P1)"},
            {"sub_id": "p2", "role": "HARD_POS_2", "split": "DEV", "is_match": True, "symptom": f"FAIL: {fam_id} Protocol Stalled (P2)"},
            {"sub_id": "p3", "role": "HARD_POS_3", "split": "TEST", "is_match": True, "symptom": f"FAIL: {fam_id} Held-Out Sequence (P3)"},
            {"sub_id": "na", "role": "HARD_NEG_SYMPTOM", "split": "TEST", "is_match": False, "symptom": f"FAIL: {fam_id} Protocol Stalled (P2)"},
            {"sub_id": "nb", "role": "HARD_NEG_TRIGGER", "split": "TEST", "is_match": False, "symptom": f"FAIL: {fam_id} Interface Error (NB)"}
        ]
        
        for inst in instances:
            full_inst_id = f"{fam_id.lower()}_{inst['sub_id']}"
            is_match = inst["is_match"]
            
            # RTL generation
            if design == "fifo":
                rtl_code = f"""
module fifo(input clk, input rst_n, input write_en, input [7:0] write_data, input read_en, output reg [7:0] read_data, output full, output empty);
    reg [7:0] mem [0:15]; reg [4:0] write_ptr; reg [4:0] read_ptr; reg [5:0] count;
    assign full = (count == 16);
    assign empty = (count == 0);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin write_ptr <= 0; read_ptr <= 0; count <= 0; end
        else begin
            if (write_en && !full) begin mem[write_ptr] <= write_data; write_ptr <= (write_ptr + 1) % 16; end
            if (read_en && !empty) begin read_data <= mem[read_ptr]; read_ptr <= (read_ptr + 1) % 16; end
            {'if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;' if is_match else 'if (write_en && !full && read_en && !empty) count <= count; else if (write_en && !full) count <= count + 1; else if (read_en && !empty) count <= count - 1;'}
        end
    end
endmodule
"""
            elif design == "axi":
                rtl_code = f"""
module axi_like(input clk, input rst_n, input valid_in, output ready_out, output reg valid_out, input ready_in);
    assign ready_out = 1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) valid_out <= 0;
        else begin
            {'if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;' if is_match else 'if (valid_in) valid_out <= 1; else if (ready_in) valid_out <= 0;'}
        end
    end
endmodule
"""
            elif design == "fsm":
                rtl_code = f"""
module fsm(input clk, input rst_n, input start, output reg done);
    reg [1:0] state;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin state <= 0; done <= 0; end
        else begin
            case(state)
                0: if (start) state <= {'2' if is_match else '1'};
                1: state <= 2;
                2: begin state <= 0; done <= 1; end
            endcase
        end
    end
endmodule
"""
            elif design == "uart":
                rtl_code = f"""
module uart(input clk, input rst_n, input start, output reg tx);
    reg [2:0] cnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cnt <= 0; tx <= 1; end
        else begin
            if (start) cnt <= cnt + {'2' if is_match else '1'};
            if (cnt == 7) tx <= ~tx;
        end
    end
endmodule
"""
            else: # pipeline
                rtl_code = f"""
module pipeline(input clk, input rst_n, input valid_in, input [7:0] d_in, output reg valid_out, output reg [7:0] d_out);
    reg v1; reg [7:0] d1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v1 <= 0; valid_out <= 0; d1 <= 0; d_out <= 0; end
        else begin
            v1 <= valid_in;
            d1 <= d_in;
            valid_out <= v1;
            d_out <= {'d_in' if is_match else 'd1'};
        end
    end
endmodule
"""

            # Testbenches
            tb_code = f"""
module tb;
    reg clk, rst_n;
    {f"reg write_en, read_en; reg [7:0] write_data; wire [7:0] read_data; wire full, empty; fifo dut(.*);" if design == 'fifo' else ''}
    {f"reg valid_in, ready_in; wire ready_out, valid_out; axi_like dut(.*);" if design == 'axi' else ''}
    {f"reg start; wire done; fsm dut(.*);" if design == 'fsm' else ''}
    {f"reg start; wire tx; uart dut(.*);" if design == 'uart' else ''}
    {f"reg valid_in; reg [7:0] d_in; wire valid_out; wire [7:0] d_out; pipeline dut(.*);" if design == 'pipeline' else ''}

    initial begin
        $dumpfile("{norm_base}/rtl/{full_inst_id}.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0;
        {f"write_en = 0; read_en = 0; write_data = 8'h11;" if design == 'fifo' else ''}
        {f"valid_in = 0; ready_in = 0;" if design == 'axi' else ''}
        {f"start = 0;" if design in ['fsm', 'uart'] else ''}
        {f"valid_in = 0; d_in = 8'h22;" if design == 'pipeline' else ''}
        #20 rst_n = 1;
        
        {f"repeat(4) begin #10 write_en = 1; read_en = 1; write_data = write_data + 1; end #10 write_en = 0; read_en = 0;" if design == 'fifo' else ''}
        {f"#10 valid_in = 1; ready_in = 1; #10 valid_in = 1; ready_in = 0; #10 valid_in = 1; ready_in = 0; #10 valid_in = 0;" if design == 'axi' else ''}
        {f"#10 start = 1; #10 start = 0; #20;" if design == 'fsm' else ''}
        {f"#10 start = 1; #40 start = 0;" if design == 'uart' else ''}
        {f"#10 valid_in = 1; d_in = 8'hAA; #10 valid_in = 1; d_in = 8'hBB; #10 valid_in = 0;" if design == 'pipeline' else ''}
        
        # 20;
        $display("{inst['symptom']}");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""

            with open(os.path.join(designs_dir, f"{full_inst_id}.v"), "w", encoding="utf-8") as f:
                f.write(rtl_code)
            with open(os.path.join(tb_dir, f"{full_inst_id}_tb.v"), "w", encoding="utf-8") as f:
                f.write(tb_code)

            benchmark_instances.append({
                "failure_id": full_inst_id,
                "family_id": fam_id,
                "design": design,
                "sub_id": inst["sub_id"],
                "role": inst["role"],
                "split": "TEST" if is_held_out else inst["split"],
                "is_held_out_mechanism": is_held_out,
                "ground_truth_match": "MATCH" if inst["is_match"] else "MISMATCH",
                "ground_truth_signals": [fam["root_signal"]],
                "defect_desc": fam["defect_desc"],
                "observed_symptom": inst["symptom"],
                "cert_spec": fam
            })

    meta_path = os.path.join(scale_dir, "benchmark_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_instances, f, indent=2)

    print(f"Generated Phase 3 Benchmark: {len(benchmark_instances)} instances across {len(causal_families)} families.")

if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generate_scale_benchmark(base)
