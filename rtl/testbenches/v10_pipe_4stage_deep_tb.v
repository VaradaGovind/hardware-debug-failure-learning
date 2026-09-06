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
