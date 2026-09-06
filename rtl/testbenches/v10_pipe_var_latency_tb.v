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
