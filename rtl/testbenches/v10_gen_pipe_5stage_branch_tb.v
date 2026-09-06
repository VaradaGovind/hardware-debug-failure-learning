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
