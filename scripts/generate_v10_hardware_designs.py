import os
import sys
import subprocess
from typing import Dict, Any, List, Tuple

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

DESIGNS_DIR = os.path.join(WORKSPACE_ROOT, "rtl", "designs")
TBS_DIR = os.path.join(WORKSPACE_ROOT, "rtl", "testbenches")
RTL_DIR = os.path.join(WORKSPACE_ROOT, "rtl")

os.makedirs(DESIGNS_DIR, exist_ok=True)
os.makedirs(TBS_DIR, exist_ok=True)

if "C:\\iverilog\\bin" not in os.environ.get("PATH", ""):
    os.environ["PATH"] = os.environ.get("PATH", "") + ";C:\\iverilog\\bin"


# Full clean suite of V10 hardware architectures across splits
V10_ARCHITECTURES = {
    # --------------------------------------------------------------------------
    # TRAIN PIPELINES
    # --------------------------------------------------------------------------
    "v10_pipe_2stage_decoupled": {
        "family": "pipeline",
        "split": "TRAIN",
        "signals": ["clk", "rst_n", "in_valid", "in_data", "s1_valid", "s1_data", "out_valid", "out_data"],
        "rtl": """
module v10_pipe_2stage_decoupled(
    input clk, input rst_n, input in_valid, input [7:0] in_data,
    output reg out_valid, output reg [7:0] out_data
);
    reg s1_valid; reg [7:0] s1_data;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s1_valid <= 1'b0; s1_data <= 8'h00; out_valid <= 1'b0; out_data <= 8'h00;
        end else begin
            s1_valid <= in_valid;
            s1_data <= in_data;
            out_valid <= (s1_valid && in_valid); // Stall drop on s1_valid
            out_data <= s1_data + 8'h01;
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_pipe_2stage_decoupled_tb;
    reg clk, rst_n, in_valid; reg [7:0] in_data;
    wire out_valid; wire [7:0] out_data;
    v10_pipe_2stage_decoupled dut(
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_data(in_data),
        .out_valid(out_valid), .out_data(out_data)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_pipe_2stage_decoupled.vcd");
        $dumpvars(0, v10_pipe_2stage_decoupled_tb);
        clk = 0; rst_n = 0; in_valid = 0; in_data = 8'h00;
        #15 rst_n = 1;
        #10 in_valid = 1; in_data = 8'h42;
        #10 in_valid = 0; in_data = 8'h00;
        #10;
        if (out_valid == 0) $display("[ASSERTION FAILURE] Cycle T=45: Pipeline token dropped on s1_valid!");
        #20 $finish;
    end
endmodule
"""
    },

    "v10_pipe_3stage_hazard": {
        "family": "pipeline",
        "split": "TRAIN",
        "signals": ["clk", "rst_n", "in_valid", "in_payload", "stage1_vld", "stage2_vld", "fwd_data", "op_reg", "out_valid", "out_payload"],
        "rtl": """
module v10_pipe_3stage_hazard(
    input clk, input rst_n, input in_valid, input [7:0] in_payload,
    output reg out_valid, output reg [7:0] out_payload
);
    reg stage1_vld, stage2_vld; reg [7:0] op_reg, fwd_data;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stage1_vld <= 0; stage2_vld <= 0; out_valid <= 0;
            op_reg <= 0; fwd_data <= 0; out_payload <= 0;
        end else begin
            stage1_vld <= in_valid;
            op_reg <= in_payload;
            stage2_vld <= stage1_vld;
            fwd_data <= op_reg; // RAW data hazard on fwd_data
            out_valid <= stage2_vld;
            out_payload <= fwd_data;
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_pipe_3stage_hazard_tb;
    reg clk, rst_n, in_valid; reg [7:0] in_payload;
    wire out_valid; wire [7:0] out_payload;
    v10_pipe_3stage_hazard dut(
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_payload(in_payload),
        .out_valid(out_valid), .out_payload(out_payload)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_pipe_3stage_hazard.vcd");
        $dumpvars(0, v10_pipe_3stage_hazard_tb);
        clk = 0; rst_n = 0; in_valid = 0; in_payload = 8'h00;
        #15 rst_n = 1;
        #10 in_valid = 1; in_payload = 8'hAA;
        #10 in_valid = 1; in_payload = 8'hBB;
        #20;
        if (out_payload != 8'hBB) $display("[ASSERTION FAILURE] Cycle T=55: RAW Data hazard on fwd_data: Stale operand!");
        #20 $finish;
    end
endmodule
"""
    },

    "v10_pipe_4stage_deep": {
        "family": "pipeline",
        "split": "TRAIN",
        "signals": ["clk", "rst_n", "val_in", "dat_in", "stg1_tok", "stg2_tok", "stg3_tok", "d1_reg", "d2_reg", "d3_reg", "val_out", "dat_out"],
        "rtl": """
module v10_pipe_4stage_deep(
    input clk, input rst_n, input val_in, input [7:0] dat_in,
    output reg val_out, output reg [7:0] dat_out
);
    reg stg1_tok, stg2_tok, stg3_tok; reg [7:0] d1_reg, d2_reg, d3_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stg1_tok <= 0; stg2_tok <= 0; stg3_tok <= 0; val_out <= 0;
            d1_reg <= 0; d2_reg <= 0; d3_reg <= 0; dat_out <= 0;
        end else begin
            stg1_tok <= val_in;
            d1_reg <= dat_in;
            stg2_tok <= stg1_tok && val_in; // Token drop on stg2_tok
            d2_reg <= d1_reg;
            stg3_tok <= stg2_tok;
            d3_reg <= d2_reg;
            val_out <= stg3_tok;
            dat_out <= d3_reg;
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_pipe_4stage_deep_tb;
    reg clk, rst_n, val_in; reg [7:0] dat_in;
    wire val_out; wire [7:0] dat_out;
    v10_pipe_4stage_deep dut(
        .clk(clk), .rst_n(rst_n), .val_in(val_in), .dat_in(dat_in),
        .val_out(val_out), .dat_out(dat_out)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_pipe_4stage_deep.vcd");
        $dumpvars(0, v10_pipe_4stage_deep_tb);
        clk = 0; rst_n = 0; val_in = 0; dat_in = 0;
        #15 rst_n = 1;
        #10 val_in = 1; dat_in = 8'h55;
        #10 val_in = 0; dat_in = 8'h00;
        #30;
        if (val_out == 0) $display("[ASSERTION FAILURE] Cycle T=65: Deep pipeline control token stg2_tok erased during stall!");
        #20 $finish;
    end
endmodule
"""
    },

    "v10_pipe_skid_elastic": {
        "family": "pipeline",
        "split": "TRAIN",
        "signals": ["clk", "rst_n", "push_val", "push_dat", "skid_vld", "skid_payload", "main_vld", "main_payload", "pop_rdy", "out_vld", "out_dat"],
        "rtl": """
module v10_pipe_skid_elastic(
    input clk, input rst_n, input push_val, input [7:0] push_dat, input pop_rdy,
    output reg out_vld, output reg [7:0] out_dat
);
    reg skid_vld, main_vld; reg [7:0] skid_payload, main_payload;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            skid_vld <= 0; main_vld <= 0; out_vld <= 0;
            skid_payload <= 0; main_payload <= 0; out_dat <= 0;
        end else begin
            if (push_val && !pop_rdy) begin
                skid_vld <= 1'b0; // Bug on skid_vld
                skid_payload <= push_dat;
            end
            if (pop_rdy) begin
                main_vld <= push_val;
                main_payload <= push_dat;
                out_vld <= main_vld;
                out_dat <= main_payload;
            end
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_pipe_skid_elastic_tb;
    reg clk, rst_n, push_val, pop_rdy; reg [7:0] push_dat;
    wire out_vld; wire [7:0] out_dat;
    v10_pipe_skid_elastic dut(
        .clk(clk), .rst_n(rst_n), .push_val(push_val), .push_dat(push_dat),
        .pop_rdy(pop_rdy), .out_vld(out_vld), .out_dat(out_dat)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_pipe_skid_elastic.vcd");
        $dumpvars(0, v10_pipe_skid_elastic_tb);
        clk = 0; rst_n = 0; push_val = 0; push_dat = 0; pop_rdy = 1;
        #15 rst_n = 1;
        #10 push_val = 1; push_dat = 8'h33; pop_rdy = 0;
        #10 push_val = 0; pop_rdy = 1;
        #20;
        if (out_vld == 0) $display("[ASSERTION FAILURE] Cycle T=45: Skid buffer drain failure on skid_vld during backpressure!");
        #20 $finish;
    end
endmodule
"""
    },

    "v10_pipe_credit_backpressure": {
        "family": "pipeline",
        "split": "TRAIN",
        "signals": ["clk", "rst_n", "tx_req", "tx_data", "credit_count", "tx_token", "pipe_d1", "rx_ack", "tx_valid", "tx_out"],
        "rtl": """
module v10_pipe_credit_backpressure(
    input clk, input rst_n, input tx_req, input [7:0] tx_data, input rx_ack,
    output reg tx_valid, output reg [7:0] tx_out
);
    reg [3:0] credit_count; reg tx_token; reg [7:0] pipe_d1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            credit_count <= 4'd4; tx_token <= 0; pipe_d1 <= 0; tx_valid <= 0; tx_out <= 0;
        end else begin
            if (tx_req && credit_count > 0) begin
                credit_count <= credit_count - 4'd2; // Bug on credit_count
                tx_token <= 1'b1; pipe_d1 <= tx_data;
            end else if (rx_ack) begin
                credit_count <= credit_count + 4'd1; tx_token <= 1'b0;
            end else begin
                tx_token <= 1'b0;
            end
            tx_valid <= tx_token; tx_out <= pipe_d1;
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_pipe_credit_backpressure_tb;
    reg clk, rst_n, tx_req, rx_ack; reg [7:0] tx_data;
    wire tx_valid; wire [7:0] tx_out;
    v10_pipe_credit_backpressure dut(
        .clk(clk), .rst_n(rst_n), .tx_req(tx_req), .tx_data(tx_data),
        .rx_ack(rx_ack), .tx_valid(tx_valid), .tx_out(tx_out)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_pipe_credit_backpressure.vcd");
        $dumpvars(0, v10_pipe_credit_backpressure_tb);
        clk = 0; rst_n = 0; tx_req = 0; tx_data = 0; rx_ack = 0;
        #15 rst_n = 1;
        #10 tx_req = 1; tx_data = 8'h77;
        #10 tx_req = 1; tx_data = 8'h88;
        #10 tx_req = 1; tx_data = 8'h99;
        #20;
        if (dut.credit_count == 0) $display("[ASSERTION FAILURE] Cycle T=45: Credit buffer exhaustion on credit_count!");
        #20 $finish;
    end
endmodule
"""
    },

    "v10_pipe_var_latency": {
        "family": "pipeline",
        "split": "TRAIN",
        "signals": ["clk", "rst_n", "start_calc", "op_val", "busy_cycles", "pipe_valid", "pipe_result", "done_strobe", "res_out"],
        "rtl": """
module v10_pipe_var_latency(
    input clk, input rst_n, input start_calc, input [7:0] op_val,
    output reg done_strobe, output reg [7:0] res_out
);
    reg [2:0] busy_cycles; reg pipe_valid; reg [7:0] pipe_result;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy_cycles <= 0; pipe_valid <= 0; pipe_result <= 0; done_strobe <= 0; res_out <= 0;
        end else begin
            if (start_calc) begin
                busy_cycles <= 3'd1; // Bug on busy_cycles
                pipe_valid <= 1; pipe_result <= op_val ^ 8'hFF;
            end else if (busy_cycles > 0) begin
                busy_cycles <= busy_cycles - 1;
                if (busy_cycles == 1) begin
                    done_strobe <= pipe_valid; res_out <= pipe_result;
                end
            end else begin
                done_strobe <= 0;
            end
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_pipe_var_latency_tb;
    reg clk, rst_n, start_calc; reg [7:0] op_val;
    wire done_strobe; wire [7:0] res_out;
    v10_pipe_var_latency dut(
        .clk(clk), .rst_n(rst_n), .start_calc(start_calc), .op_val(op_val),
        .done_strobe(done_strobe), .res_out(res_out)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_pipe_var_latency.vcd");
        $dumpvars(0, v10_pipe_var_latency_tb);
        clk = 0; rst_n = 0; start_calc = 0; op_val = 0;
        #15 rst_n = 1;
        #10 start_calc = 1; op_val = 8'hA5;
        #10 start_calc = 0;
        #30;
        if (done_strobe == 0) $display("[ASSERTION FAILURE] Cycle T=40: Multi-cycle completion flag busy_cycles drop!");
        #20 $finish;
    end
endmodule
"""
    },

    # --------------------------------------------------------------------------
    # TRAIN OTHER FAMILIES (FIFO, AXI, FSM, UART)
    # --------------------------------------------------------------------------
    "v10_fifo_gray_ptr": {
        "family": "fifo",
        "split": "TRAIN",
        "signals": ["clk", "rst_n", "wr_strobe", "rd_strobe", "wr_payload", "gray_wr_ptr", "gray_rd_ptr", "bin_wr_ptr", "bin_rd_ptr", "fifo_occ", "rd_payload", "buf_empty", "buf_full"],
        "rtl": """
module v10_fifo_gray_ptr(
    input clk, input rst_n, input wr_strobe, input rd_strobe, input [7:0] wr_payload,
    output reg [7:0] rd_payload, output reg buf_empty, output reg buf_full
);
    reg [3:0] bin_wr_ptr, bin_rd_ptr, gray_wr_ptr, gray_rd_ptr, fifo_occ;
    reg [7:0] mem [0:7];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bin_wr_ptr <= 0; bin_rd_ptr <= 0; gray_wr_ptr <= 0; gray_rd_ptr <= 0;
            fifo_occ <= 0; buf_empty <= 1; buf_full <= 0; rd_payload <= 0;
        end else begin
            if (wr_strobe && !buf_full) begin
                mem[bin_wr_ptr[2:0]] <= wr_payload;
                bin_wr_ptr <= bin_wr_ptr + 1;
                gray_wr_ptr <= (bin_wr_ptr >> 1); // Bug on gray_wr_ptr
            end
            if (rd_strobe && !buf_empty) begin
                rd_payload <= mem[bin_rd_ptr[2:0]];
                bin_rd_ptr <= bin_rd_ptr + 1;
                gray_rd_ptr <= (bin_rd_ptr ^ (bin_rd_ptr >> 1));
            end
            fifo_occ <= bin_wr_ptr - bin_rd_ptr;
            buf_empty <= (bin_wr_ptr == bin_rd_ptr);
            buf_full <= (fifo_occ == 4'd8);
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_fifo_gray_ptr_tb;
    reg clk, rst_n, wr_strobe, rd_strobe; reg [7:0] wr_payload;
    wire [7:0] rd_payload; wire buf_empty, buf_full;
    v10_fifo_gray_ptr dut(
        .clk(clk), .rst_n(rst_n), .wr_strobe(wr_strobe), .rd_strobe(rd_strobe),
        .wr_payload(wr_payload), .rd_payload(rd_payload),
        .buf_empty(buf_empty), .buf_full(buf_full)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_fifo_gray_ptr.vcd");
        $dumpvars(0, v10_fifo_gray_ptr_tb);
        clk = 0; rst_n = 0; wr_strobe = 0; rd_strobe = 0; wr_payload = 0;
        #15 rst_n = 1;
        #10 wr_strobe = 1; wr_payload = 8'h11;
        #10 wr_strobe = 1; wr_payload = 8'h22;
        #10 wr_strobe = 0; rd_strobe = 1;
        #20;
        if (dut.gray_wr_ptr != 4'h3) $display("[ASSERTION FAILURE] Cycle T=40: Gray code sync pointer anomaly on gray_wr_ptr!");
        #20 $finish;
    end
endmodule
"""
    },

    "v10_fifo_watermark": {
        "family": "fifo",
        "split": "TRAIN",
        "signals": ["clk", "rst_n", "w_en", "r_en", "w_data", "watermark_lvl", "prog_full", "prog_empty", "r_data"],
        "rtl": """
module v10_fifo_watermark(
    input clk, input rst_n, input w_en, input r_en, input [7:0] w_data,
    output reg prog_full, output reg prog_empty, output reg [7:0] r_data
);
    reg [4:0] watermark_lvl; reg [7:0] ram [0:15]; reg [3:0] w_idx, r_idx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            watermark_lvl <= 0; w_idx <= 0; r_idx <= 0;
            prog_full <= 0; prog_empty <= 1; r_data <= 0;
        end else begin
            if (w_en && !r_en) begin
                ram[w_idx] <= w_data; w_idx <= w_idx + 1;
                watermark_lvl <= watermark_lvl + 2; // Bug on watermark_lvl
            end else if (r_en && !w_en) begin
                r_data <= ram[r_idx]; r_idx <= r_idx + 1;
                watermark_lvl <= watermark_lvl - 1;
            end
            prog_full <= (watermark_lvl >= 5'd12);
            prog_empty <= (watermark_lvl <= 5'd2);
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_fifo_watermark_tb;
    reg clk, rst_n, w_en, r_en; reg [7:0] w_data;
    wire prog_full, prog_empty; wire [7:0] r_data;
    v10_fifo_watermark dut(
        .clk(clk), .rst_n(rst_n), .w_en(w_en), .r_en(r_en), .w_data(w_data),
        .prog_full(prog_full), .prog_empty(prog_empty), .r_data(r_data)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_fifo_watermark.vcd");
        $dumpvars(0, v10_fifo_watermark_tb);
        clk = 0; rst_n = 0; w_en = 0; r_en = 0; w_data = 0;
        #15 rst_n = 1;
        #10 w_en = 1; w_data = 8'hAA;
        #10 w_en = 1; w_data = 8'hBB;
        #20;
        if (dut.watermark_lvl != 5'd2) $display("[ASSERTION FAILURE] Cycle T=35: Watermark counter divergence on watermark_lvl!");
        #20 $finish;
    end
endmodule
"""
    },

    "v10_axi_split_transfer": {
        "family": "axi",
        "split": "TRAIN",
        "signals": ["clk", "rst_n", "tstart", "chunk_idx", "tvalid_out", "tready_in", "tlast_out", "tdata_out"],
        "rtl": """
module v10_axi_split_transfer(
    input clk, input rst_n, input tstart, input tready_in,
    output reg tvalid_out, output reg tlast_out, output reg [7:0] tdata_out
);
    reg [2:0] chunk_idx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            chunk_idx <= 0; tvalid_out <= 0; tlast_out <= 0; tdata_out <= 0;
        end else begin
            if (tstart) begin
                tvalid_out <= 1'b1; chunk_idx <= 3'd0; tdata_out <= 8'h10;
            end else if (tvalid_out && !tready_in) begin
                tvalid_out <= 1'b0; // Bug on tvalid_out
            end else if (tvalid_out && tready_in) begin
                chunk_idx <= chunk_idx + 1; tdata_out <= tdata_out + 8'h10;
                if (chunk_idx == 3'd3) begin
                    tlast_out <= 1'b1; tvalid_out <= 1'b0;
                end
            end
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_axi_split_transfer_tb;
    reg clk, rst_n, tstart, tready_in;
    wire tvalid_out, tlast_out; wire [7:0] tdata_out;
    v10_axi_split_transfer dut(
        .clk(clk), .rst_n(rst_n), .tstart(tstart), .tready_in(tready_in),
        .tvalid_out(tvalid_out), .tlast_out(tlast_out), .tdata_out(tdata_out)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_axi_split_transfer.vcd");
        $dumpvars(0, v10_axi_split_transfer_tb);
        clk = 0; rst_n = 0; tstart = 0; tready_in = 0;
        #15 rst_n = 1;
        #10 tstart = 1;
        #10 tstart = 0; tready_in = 0;
        #20;
        if (tvalid_out == 0) $display("[ASSERTION FAILURE] Cycle T=35: AXI Handshake Hold violation on tvalid_out!");
        #20 $finish;
    end
endmodule
"""
    },

    "v10_fsm_hierarchical_seq": {
        "family": "fsm",
        "split": "TRAIN",
        "signals": ["clk", "rst_n", "start_pulse", "main_state", "sub_state", "seq_done", "out_flag"],
        "rtl": """
module v10_fsm_hierarchical_seq(
    input clk, input rst_n, input start_pulse, output reg seq_done, output reg out_flag
);
    reg [1:0] main_state; reg [2:0] sub_state;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            main_state <= 2'd0; sub_state <= 3'd0; seq_done <= 0; out_flag <= 0;
        end else begin
            case (main_state)
                2'd0: begin
                    seq_done <= 0;
                    if (start_pulse) begin main_state <= 2'd1; sub_state <= 3'd0; end
                end
                2'd1: begin
                    if (sub_state == 3'd1) sub_state <= 3'd4; // Bug on sub_state
                    else sub_state <= sub_state + 1;
                    if (sub_state == 3'd4) main_state <= 2'd2;
                end
                2'd2: begin
                    seq_done <= 1'b1; out_flag <= (sub_state == 3'd4); main_state <= 2'd0;
                end
            endcase
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_fsm_hierarchical_seq_tb;
    reg clk, rst_n, start_pulse;
    wire seq_done, out_flag;
    v10_fsm_hierarchical_seq dut(
        .clk(clk), .rst_n(rst_n), .start_pulse(start_pulse),
        .seq_done(seq_done), .out_flag(out_flag)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_fsm_hierarchical_seq.vcd");
        $dumpvars(0, v10_fsm_hierarchical_seq_tb);
        clk = 0; rst_n = 0; start_pulse = 0;
        #15 rst_n = 1;
        #10 start_pulse = 1;
        #10 start_pulse = 0;
        #40;
        if (dut.sub_state != 3'd4) $display("[ASSERTION FAILURE] Cycle T=45: FSM sub-state skip on sub_state!");
        #20 $finish;
    end
endmodule
"""
    },

    "v10_uart_fractional_baud": {
        "family": "uart",
        "split": "TRAIN",
        "signals": ["clk", "rst_n", "tx_enable", "tx_byte", "frac_acc", "baud_tick", "tx_bit_cnt", "serial_tx", "tx_busy"],
        "rtl": """
module v10_uart_fractional_baud(
    input clk, input rst_n, input tx_enable, input [7:0] tx_byte,
    output reg serial_tx, output reg tx_busy
);
    reg [4:0] frac_acc; reg [3:0] tx_bit_cnt; reg baud_tick; reg [7:0] shift_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            frac_acc <= 0; baud_tick <= 0; tx_bit_cnt <= 0; serial_tx <= 1; tx_busy <= 0; shift_reg <= 0;
        end else begin
            if (frac_acc >= 5'd6) begin // Bug on frac_acc
                frac_acc <= 0; baud_tick <= 1'b1;
            end else begin
                frac_acc <= frac_acc + 1; baud_tick <= 1'b0;
            end
            if (tx_enable && !tx_busy) begin
                tx_busy <= 1; shift_reg <= tx_byte; tx_bit_cnt <= 0; serial_tx <= 0;
            end else if (tx_busy && baud_tick) begin
                tx_bit_cnt <= tx_bit_cnt + 1;
                if (tx_bit_cnt < 8) begin
                    serial_tx <= shift_reg[0]; shift_reg <= (shift_reg >> 1);
                end else begin
                    serial_tx <= 1; tx_busy <= 0;
                end
            end
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_uart_fractional_baud_tb;
    reg clk, rst_n, tx_enable; reg [7:0] tx_byte;
    wire serial_tx, tx_busy;
    v10_uart_fractional_baud dut(
        .clk(clk), .rst_n(rst_n), .tx_enable(tx_enable), .tx_byte(tx_byte),
        .serial_tx(serial_tx), .tx_busy(tx_busy)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_uart_fractional_baud.vcd");
        $dumpvars(0, v10_uart_fractional_baud_tb);
        clk = 0; rst_n = 0; tx_enable = 0; tx_byte = 8'hA5;
        #15 rst_n = 1;
        #10 tx_enable = 1;
        #10 tx_enable = 0;
        #50;
        if (dut.frac_acc != 0 && tx_busy == 0) $display("[ASSERTION FAILURE] Cycle T=60: UART fractional baud rate accumulator anomaly on frac_acc!");
        #20 $finish;
    end
endmodule
"""
    },

    # --------------------------------------------------------------------------
    # VALIDATION ARCHITECTURES (Architecture-Disjoint: Never seen in Training)
    # --------------------------------------------------------------------------
    "v10_val_pipe_3stage_split": {
        "family": "pipeline",
        "split": "VALIDATION",
        "signals": ["clk", "rst_n", "p_in_val", "p_in_dat", "p1_val", "p1_dat", "p2_val", "p2_dat", "p_out_val", "p_out_dat"],
        "rtl": """
module v10_val_pipe_3stage_split(
    input clk, input rst_n, input p_in_val, input [7:0] p_in_dat,
    output reg p_out_val, output reg [7:0] p_out_dat
);
    reg p1_val, p2_val; reg [7:0] p1_dat, p2_dat;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            p1_val <= 0; p2_val <= 0; p_out_val <= 0; p1_dat <= 0; p2_dat <= 0; p_out_dat <= 0;
        end else begin
            p1_val <= p_in_val; p1_dat <= p_in_dat;
            p2_val <= (p1_val && p_in_val); // Bug on p1_val
            p2_dat <= p1_dat;
            p_out_val <= p2_val; p_out_dat <= p2_dat;
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_val_pipe_3stage_split_tb;
    reg clk, rst_n, p_in_val; reg [7:0] p_in_dat;
    wire p_out_val; wire [7:0] p_out_dat;
    v10_val_pipe_3stage_split dut(
        .clk(clk), .rst_n(rst_n), .p_in_val(p_in_val), .p_in_dat(p_in_dat),
        .p_out_val(p_out_val), .p_out_dat(p_out_dat)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_val_pipe_3stage_split.vcd");
        $dumpvars(0, v10_val_pipe_3stage_split_tb);
        clk = 0; rst_n = 0; p_in_val = 0; p_in_dat = 0;
        #15 rst_n = 1;
        #10 p_in_val = 1; p_in_dat = 8'hCC;
        #10 p_in_val = 0; p_in_dat = 8'h00;
        #25;
        if (p_out_val == 0) $display("[ASSERTION FAILURE] Cycle T=45: Disjoint validation pipeline token dropped on p1_val!");
        #20 $finish;
    end
endmodule
"""
    },

    "v10_val_fifo_ring_buf": {
        "family": "fifo",
        "split": "VALIDATION",
        "signals": ["clk", "rst_n", "push_cmd", "pop_cmd", "data_in", "head_idx", "tail_idx", "items_avail", "data_out"],
        "rtl": """
module v10_val_fifo_ring_buf(
    input clk, input rst_n, input push_cmd, input pop_cmd, input [7:0] data_in,
    output reg [7:0] data_out
);
    reg [3:0] head_idx, tail_idx; reg [3:0] items_avail; reg [7:0] ring_mem [0:15];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            head_idx <= 0; tail_idx <= 0; items_avail <= 0; data_out <= 0;
        end else begin
            if (push_cmd && !pop_cmd) begin
                ring_mem[head_idx] <= data_in; head_idx <= head_idx + 1;
                items_avail <= items_avail; // Bug on items_avail
            end else if (pop_cmd && !push_cmd) begin
                data_out <= ring_mem[tail_idx]; tail_idx <= tail_idx + 1;
                items_avail <= items_avail - 1;
            end
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_val_fifo_ring_buf_tb;
    reg clk, rst_n, push_cmd, pop_cmd; reg [7:0] data_in;
    wire [7:0] data_out;
    v10_val_fifo_ring_buf dut(
        .clk(clk), .rst_n(rst_n), .push_cmd(push_cmd), .pop_cmd(pop_cmd),
        .data_in(data_in), .data_out(data_out)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_val_fifo_ring_buf.vcd");
        $dumpvars(0, v10_val_fifo_ring_buf_tb);
        clk = 0; rst_n = 0; push_cmd = 0; pop_cmd = 0; data_in = 0;
        #15 rst_n = 1;
        #10 push_cmd = 1; data_in = 8'h88;
        #10 push_cmd = 0; pop_cmd = 1;
        #20;
        if (dut.items_avail != 4'd0) $display("[ASSERTION FAILURE] Cycle T=35: Ring buffer items counter corruption on items_avail!");
        #20 $finish;
    end
endmodule
"""
    },

    "v10_val_axi_stream_fifo": {
        "family": "axi",
        "split": "VALIDATION",
        "signals": ["clk", "rst_n", "strm_val_in", "strm_rdy_out", "strm_val", "strm_rdy", "occupancy_tok", "strm_val_out"],
        "rtl": """
module v10_val_axi_stream_fifo(
    input clk, input rst_n, input strm_val_in, output reg strm_rdy_out, output reg strm_val_out
);
    reg strm_val, strm_rdy; reg [2:0] occupancy_tok;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            strm_val <= 0; strm_rdy <= 1; occupancy_tok <= 0; strm_rdy_out <= 1; strm_val_out <= 0;
        end else begin
            if (strm_val_in && strm_rdy_out) begin
                occupancy_tok <= occupancy_tok + 1; strm_val <= 1'b1;
            end else begin
                strm_val <= 1'b0; // Bug on strm_val
            end
            strm_val_out <= strm_val;
            strm_rdy_out <= (occupancy_tok < 3'd4);
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_val_axi_stream_fifo_tb;
    reg clk, rst_n, strm_val_in;
    wire strm_rdy_out, strm_val_out;
    v10_val_axi_stream_fifo dut(
        .clk(clk), .rst_n(rst_n), .strm_val_in(strm_val_in),
        .strm_rdy_out(strm_rdy_out), .strm_val_out(strm_val_out)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_val_axi_stream_fifo.vcd");
        $dumpvars(0, v10_val_axi_stream_fifo_tb);
        clk = 0; rst_n = 0; strm_val_in = 0;
        #15 rst_n = 1;
        #10 strm_val_in = 1;
        #10 strm_val_in = 0;
        #20;
        if (strm_val_out == 0) $display("[ASSERTION FAILURE] Cycle T=35: Stream handshake stability drop on strm_val!");
        #20 $finish;
    end
endmodule
"""
    },

    # --------------------------------------------------------------------------
    # GENERALIZATION ARCHITECTURES (Completely Unseen Topology Families)
    # --------------------------------------------------------------------------
    "v10_gen_pipe_5stage_branch": {
        "family": "pipeline",
        "split": "GENERALIZATION",
        "signals": ["clk", "rst_n", "fetch_req", "fetch_v", "dec_v", "ex_v", "mem_v", "wb_v", "byp_reg", "branch_flush", "retire_v"],
        "rtl": """
module v10_gen_pipe_5stage_branch(
    input clk, input rst_n, input fetch_req, input branch_flush, output reg retire_v
);
    reg fetch_v, dec_v, ex_v, mem_v, wb_v; reg [7:0] byp_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fetch_v <= 0; dec_v <= 0; ex_v <= 0; mem_v <= 0; wb_v <= 0;
            byp_reg <= 0; retire_v <= 0;
        end else begin
            if (branch_flush) begin
                fetch_v <= 0; dec_v <= 0;
                ex_v <= 1'b1; // Bug on ex_v
            end else begin
                fetch_v <= fetch_req; dec_v <= fetch_v; ex_v <= dec_v;
            end
            mem_v <= ex_v; wb_v <= mem_v; retire_v <= wb_v;
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_gen_pipe_5stage_branch_tb;
    reg clk, rst_n, fetch_req, branch_flush;
    wire retire_v;
    v10_gen_pipe_5stage_branch dut(
        .clk(clk), .rst_n(rst_n), .fetch_req(fetch_req), .branch_flush(branch_flush),
        .retire_v(retire_v)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_gen_pipe_5stage_branch.vcd");
        $dumpvars(0, v10_gen_pipe_5stage_branch_tb);
        clk = 0; rst_n = 0; fetch_req = 0; branch_flush = 0;
        #15 rst_n = 1;
        #10 fetch_req = 1;
        #10 branch_flush = 1; fetch_req = 0;
        #30;
        if (retire_v != 0) $display("[ASSERTION FAILURE] Cycle T=55: Branch misprediction flush leak on ex_v!");
        #20 $finish;
    end
endmodule
"""
    },

    "v10_gen_pipe_elastic_ring": {
        "family": "pipeline",
        "split": "GENERALIZATION",
        "signals": ["clk", "rst_n", "ring_inject", "token_ring", "packet_id", "route_valid", "ring_eject"],
        "rtl": """
module v10_gen_pipe_elastic_ring(
    input clk, input rst_n, input ring_inject, input [7:0] packet_id,
    output reg route_valid, output reg ring_eject
);
    reg [3:0] token_ring; reg [7:0] p_storage;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            token_ring <= 4'b0001; p_storage <= 0; route_valid <= 0; ring_eject <= 0;
        end else begin
            if (ring_inject) begin
                p_storage <= packet_id;
                token_ring <= {token_ring[2:0], 1'b0}; // Bug on token_ring
            end else begin
                token_ring <= {token_ring[2:0], token_ring[3]};
            end
            route_valid <= (token_ring != 4'b0000);
            ring_eject <= (token_ring[3] == 1'b1);
        end
    end
endmodule
""",
        "tb": """
`timescale 1ns/1ps
module v10_gen_pipe_elastic_ring_tb;
    reg clk, rst_n, ring_inject; reg [7:0] packet_id;
    wire route_valid, ring_eject;
    v10_gen_pipe_elastic_ring dut(
        .clk(clk), .rst_n(rst_n), .ring_inject(ring_inject), .packet_id(packet_id),
        .route_valid(route_valid), .ring_eject(ring_eject)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_gen_pipe_elastic_ring.vcd");
        $dumpvars(0, v10_gen_pipe_elastic_ring_tb);
        clk = 0; rst_n = 0; ring_inject = 0; packet_id = 8'hAA;
        #15 rst_n = 1;
        #10 ring_inject = 1;
        #10 ring_inject = 0;
        #30;
        if (route_valid == 0) $display("[ASSERTION FAILURE] Cycle T=45: Circulating token collapse on token_ring!");
        #20 $finish;
    end
endmodule
"""
    }
}


def compile_and_simulate_all():
    print("=" * 88)
    print("EXPERIMENT V10: COMPILING & SIMULATING V10 HARDWARE DESIGNS")
    print("=" * 88)
    compiled = 0
    simulated = 0
    for task_id, spec in V10_ARCHITECTURES.items():
        v_path = os.path.join(DESIGNS_DIR, f"{task_id}.v")
        tb_path = os.path.join(TBS_DIR, f"{task_id}_tb.v")
        vvp_path = os.path.join(RTL_DIR, f"{task_id}.vvp")
        with open(v_path, "w", encoding="utf-8") as fp:
            fp.write(spec["rtl"].strip() + "\n")
        with open(tb_path, "w", encoding="utf-8") as fp:
            fp.write(spec["tb"].strip() + "\n")
        comp_cmd = ["C:\\iverilog\\bin\\iverilog.exe", "-o", vvp_path, v_path, tb_path]
        res = subprocess.run(comp_cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            print(f"[!] Compilation ERROR on {task_id}: {res.stderr}")
            continue
        compiled += 1
        run_cmd = ["C:\\iverilog\\bin\\vvp.exe", f"{task_id}.vvp"]
        run_res = subprocess.run(run_cmd, cwd=RTL_DIR, capture_output=True, text=True, check=False)
        simulated += 1
        vcd_path = os.path.join(RTL_DIR, f"{task_id}.vcd")
        vcd_exists = os.path.exists(vcd_path)
        print(f"  [{spec['split']}] {task_id:32s} | VVP: OK | VCD: {'OK' if vcd_exists else 'MISSING'}")
    print(f"\n[PASS] Successfully compiled and simulated {compiled}/{len(V10_ARCHITECTURES)} V10 hardware architectures.")


if __name__ == "__main__":
    compile_and_simulate_all()
