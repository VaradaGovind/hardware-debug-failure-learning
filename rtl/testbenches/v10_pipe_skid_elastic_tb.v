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
