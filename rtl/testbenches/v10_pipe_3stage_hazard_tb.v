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
