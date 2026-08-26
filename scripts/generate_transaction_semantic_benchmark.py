import os
import json

def generate_transaction_semantic_benchmark(base_dir: str):
    designs_dir = os.path.join(base_dir, "rtl", "designs")
    tb_dir = os.path.join(base_dir, "rtl", "testbenches")
    phase4_dir = os.path.join(base_dir, "results", "transaction_semantic_certs")
    
    os.makedirs(designs_dir, exist_ok=True)
    os.makedirs(tb_dir, exist_ok=True)
    os.makedirs(phase4_dir, exist_ok=True)
    
    norm_base = base_dir.replace("\\", "/")
    
    # GATE 1 TEST SUITE: 6 Phase 3.1 Cases + Positive Controls + Negative C Controls
    
    gate1_cases = [
        # FSM Stuck State Family
        {
            "id": "fsm_stuck_state_src",
            "family": "FSM_STUCK_STATE",
            "design": "fsm",
            "role": "SOURCE",
            "category": "SOURCE",
            "is_match": True,
            "desc": "FSM state fails to transition on start pulse (stuck in IDLE)",
            "rtl_defect": "state <= 0;", # stuck at 0 on start
            "tb_stim": "#10 start = 1; #10 start = 0; #30;",
            "symptom": "FAIL: FSM Stuck in IDLE (Source)"
        },
        {
            "id": "fsm_stuck_state_pos1",
            "family": "FSM_STUCK_STATE",
            "design": "fsm",
            "role": "POSITIVE_CONTROL_1",
            "category": "POSITIVE_CONTROL",
            "is_match": True,
            "desc": "FSM stuck state with delayed start pulse",
            "rtl_defect": "state <= 0;",
            "tb_stim": "#30 start = 1; #10 start = 0; #20;",
            "symptom": "FAIL: FSM Stuck in IDLE (Pos 1)"
        },
        {
            "id": "fsm_stuck_state_pos2",
            "family": "FSM_STUCK_STATE",
            "design": "fsm",
            "role": "POSITIVE_CONTROL_2",
            "category": "POSITIVE_CONTROL",
            "is_match": True,
            "desc": "FSM stuck state with consecutive start pulses",
            "rtl_defect": "state <= 0;",
            "tb_stim": "#10 start = 1; #10 start = 0; #10 start = 1; #10 start = 0; #20;",
            "symptom": "FAIL: FSM Stuck in IDLE (Pos 2)"
        },
        {
            "id": "fsm_stuck_state_na",
            "family": "FSM_STUCK_STATE",
            "design": "fsm",
            "role": "HARD_NEG_SYMPTOM",
            "category": "PHASE3_1_FAILURE_CASE",
            "is_match": False,
            "desc": "FSM state advances to 1 but fails to advance to 2 (different defect, same symptom)",
            "rtl_defect": "state <= 1;",
            "tb_stim": "#10 start = 1; #10 start = 0; #30;",
            "symptom": "FAIL: FSM Timeout / Stalled (P2)"
        },
        {
            "id": "fsm_stuck_state_nb",
            "family": "FSM_STUCK_STATE",
            "design": "fsm",
            "role": "HARD_NEG_TRIGGER",
            "category": "PHASE3_1_FAILURE_CASE",
            "is_match": False,
            "desc": "FSM skips to state 2 directly on start (different defect, same trigger)",
            "rtl_defect": "state <= 2;",
            "tb_stim": "#10 start = 1; #10 start = 0; #30;",
            "symptom": "FAIL: FSM Interface Error (NB)"
        },
        {
            "id": "fsm_stuck_state_neg_c",
            "family": "FSM_STUCK_STATE",
            "design": "fsm",
            "role": "HARD_NEG_C_TRANSACTION",
            "category": "NEGATIVE_C_CONTROL",
            "is_match": False,
            "desc": "FSM state remains 0 legitimately because NO start pulse occurred (same signal stability, different transaction semantics)",
            "rtl_defect": "if (start) state <= 1; else state <= 0;", # Correct RTL!
            "tb_stim": "#50 start = 0;", # No start pulse!
            "symptom": "FAIL: Unrelated test assertion timeout (Neg C)"
        },

        # Pipeline Stall Bubble Family
        {
            "id": "pipe_stall_bubble_src",
            "family": "PIPE_STALL_BUBBLE",
            "design": "pipeline",
            "role": "SOURCE",
            "category": "SOURCE",
            "is_match": True,
            "desc": "Pipeline stage 2 clears valid_out unexpectedly during active flow",
            "rtl_defect": "valid_out <= 0; d_out <= 0;",
            "tb_stim": "#10 valid_in = 1; d_in = 8'hAA; #10 valid_in = 0; #20;",
            "symptom": "FAIL: Pipeline Output Dropped (Source)"
        },
        {
            "id": "pipe_stall_bubble_pos1",
            "family": "PIPE_STALL_BUBBLE",
            "design": "pipeline",
            "role": "POSITIVE_CONTROL_1",
            "category": "POSITIVE_CONTROL",
            "is_match": True,
            "desc": "Pipeline bubble with alternating payload",
            "rtl_defect": "valid_out <= 0; d_out <= 0;",
            "tb_stim": "#10 valid_in = 1; d_in = 8'h55; #10 valid_in = 0; #20;",
            "symptom": "FAIL: Pipeline Output Dropped (Pos 1)"
        },
        {
            "id": "pipe_stall_bubble_pos2",
            "family": "PIPE_STALL_BUBBLE",
            "design": "pipeline",
            "role": "POSITIVE_CONTROL_2",
            "category": "POSITIVE_CONTROL",
            "is_match": True,
            "desc": "Pipeline bubble with multi-beat burst",
            "rtl_defect": "valid_out <= 0; d_out <= 0;",
            "tb_stim": "#10 valid_in = 1; d_in = 8'h11; #10 valid_in = 1; d_in = 8'h22; #10 valid_in = 0; #20;",
            "symptom": "FAIL: Pipeline Output Dropped (Pos 2)"
        },
        {
            "id": "pipe_stall_bubble_na",
            "family": "PIPE_STALL_BUBBLE",
            "design": "pipeline",
            "role": "HARD_NEG_SYMPTOM",
            "category": "PHASE3_1_FAILURE_CASE",
            "is_match": False,
            "desc": "Pipeline forward bypass hazard (different defect, same symptom)",
            "rtl_defect": "valid_out <= v1; d_out <= d_in;", # Bypass hazard
            "tb_stim": "#10 valid_in = 1; d_in = 8'hAA; #10 valid_in = 0; #20;",
            "symptom": "FAIL: Protocol Stalled (P2)"
        },
        {
            "id": "pipe_stall_bubble_nb",
            "family": "PIPE_STALL_BUBBLE",
            "design": "pipeline",
            "role": "HARD_NEG_TRIGGER",
            "category": "PHASE3_1_FAILURE_CASE",
            "is_match": False,
            "desc": "Pipeline payload corruption on valid beats (different defect, same trigger)",
            "rtl_defect": "valid_out <= v1; d_out <= 8'hFF;",
            "tb_stim": "#10 valid_in = 1; d_in = 8'hAA; #10 valid_in = 0; #20;",
            "symptom": "FAIL: Interface Error (NB)"
        },
        {
            "id": "pipe_stall_bubble_neg_c",
            "family": "PIPE_STALL_BUBBLE",
            "design": "pipeline",
            "role": "HARD_NEG_C_TRANSACTION",
            "category": "NEGATIVE_C_CONTROL",
            "is_match": False,
            "desc": "Legitimate pipeline bubble drainage (valid_out=0 when valid_in=0, but valid_out=1 when valid_in=1) -> same signal stability, different transaction semantics",
            "rtl_defect": "valid_out <= v1; d_out <= d1;", # Correct Pipeline RTL!
            "tb_stim": "#10 valid_in = 0; #30 valid_in = 1; d_in = 8'hAA;",
            "symptom": "FAIL: Downstream consumer timeout (Neg C)"
        },

        # Pipeline Stage Enable Family
        {
            "id": "pipe_stage_enable_src",
            "family": "PIPE_STAGE_ENABLE",
            "design": "pipeline",
            "role": "SOURCE",
            "category": "SOURCE",
            "is_match": True,
            "desc": "Pipeline stage 2 enables unconditionally without checking stage 1 valid",
            "rtl_defect": "valid_out <= 1; d_out <= d1;", # Unconditional valid_out = 1
            "tb_stim": "#10 valid_in = 0; #20;",
            "symptom": "FAIL: Pipeline Spurious Valid (Source)"
        },
        {
            "id": "pipe_stage_enable_pos1",
            "family": "PIPE_STAGE_ENABLE",
            "design": "pipeline",
            "role": "POSITIVE_CONTROL_1",
            "category": "POSITIVE_CONTROL",
            "is_match": True,
            "desc": "Spurious valid on post-reset idle",
            "rtl_defect": "valid_out <= 1; d_out <= d1;",
            "tb_stim": "#20 valid_in = 0; #20;",
            "symptom": "FAIL: Pipeline Spurious Valid (Pos 1)"
        },
        {
            "id": "pipe_stage_enable_pos2",
            "family": "PIPE_STAGE_ENABLE",
            "design": "pipeline",
            "role": "POSITIVE_CONTROL_2",
            "category": "POSITIVE_CONTROL",
            "is_match": True,
            "desc": "Spurious valid after stream termination",
            "rtl_defect": "valid_out <= 1; d_out <= d1;",
            "tb_stim": "#10 valid_in = 1; d_in = 8'h99; #10 valid_in = 0; #20;",
            "symptom": "FAIL: Pipeline Spurious Valid (Pos 2)"
        },
        {
            "id": "pipe_stage_enable_na",
            "family": "PIPE_STAGE_ENABLE",
            "design": "pipeline",
            "role": "HARD_NEG_SYMPTOM",
            "category": "PHASE3_1_FAILURE_CASE",
            "is_match": False,
            "desc": "Pipeline data corruption without spurious valid (different defect, same symptom)",
            "rtl_defect": "valid_out <= v1; d_out <= ~d1;",
            "tb_stim": "#10 valid_in = 1; d_in = 8'h99; #10 valid_in = 0; #20;",
            "symptom": "FAIL: Protocol Stalled (P2)"
        },
        {
            "id": "pipe_stage_enable_nb",
            "family": "PIPE_STAGE_ENABLE",
            "design": "pipeline",
            "role": "HARD_NEG_TRIGGER",
            "category": "PHASE3_1_FAILURE_CASE",
            "is_match": False,
            "desc": "Pipeline forward bypass hazard (different defect, same trigger)",
            "rtl_defect": "valid_out <= v1; d_out <= d_in;",
            "tb_stim": "#10 valid_in = 1; d_in = 8'h99; #10 valid_in = 0; #20;",
            "symptom": "FAIL: Interface Error (NB)"
        },
        {
            "id": "pipe_stage_enable_neg_c",
            "family": "PIPE_STAGE_ENABLE",
            "design": "pipeline",
            "role": "HARD_NEG_C_TRANSACTION",
            "category": "NEGATIVE_C_CONTROL",
            "is_match": False,
            "desc": "Legitimate pipeline stage enable with valid data transfer (valid_out matches v1) -> same signal stability, different transaction semantics",
            "rtl_defect": "valid_out <= v1; d_out <= d1;", # Correct Pipeline RTL!
            "tb_stim": "#10 valid_in = 1; d_in = 8'hCC; #10 valid_in = 0; #20;",
            "symptom": "FAIL: Downstream check timeout (Neg C)"
        }
    ]

    for case in gate1_cases:
        c_id = case["id"]
        design = case["design"]
        
        # Write Verilog files
        if design == "fsm":
            rtl_code = f"""
module fsm(input clk, input rst_n, input start, output reg done);
    reg [1:0] state;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin state <= 0; done <= 0; end
        else begin
            case(state)
                0: if (start) begin {case['rtl_defect']} end
                1: state <= 2;
                2: begin state <= 0; done <= 1; end
            endcase
        end
    end
endmodule
"""
            tb_code = f"""
module tb;
    reg clk, rst_n, start;
    wire done;
    fsm dut(.*);
    initial begin
        $dumpfile("{c_id}.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; start = 0;
        #20 rst_n = 1;
        {case['tb_stim']}
        # 20;
        $display("{case['symptom']}");
        #10 $finish;
    end
    always #5 clk = ~clk;
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
            {case['rtl_defect']}
        end
    end
endmodule
"""
            tb_code = f"""
module tb;
    reg clk, rst_n, valid_in;
    reg [7:0] d_in;
    wire valid_out;
    wire [7:0] d_out;
    pipeline dut(.*);
    initial begin
        $dumpfile("{c_id}.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; valid_in = 0; d_in = 8'h00;
        #20 rst_n = 1;
        {case['tb_stim']}
        # 20;
        $display("{case['symptom']}");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""
        with open(os.path.join(designs_dir, f"{c_id}.v"), "w", encoding="utf-8") as f:
            f.write(rtl_code)
        with open(os.path.join(tb_dir, f"{c_id}_tb.v"), "w", encoding="utf-8") as f:
            f.write(tb_code)

    meta_path = os.path.join(phase4_dir, "gate1_benchmark_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(gate1_cases, f, indent=2)

    print(f"Generated Phase 4 Gate 1 Benchmark: {len(gate1_cases)} controlled instances.")

if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generate_transaction_semantic_benchmark(base)
