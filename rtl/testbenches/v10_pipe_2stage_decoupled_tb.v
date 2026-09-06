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
