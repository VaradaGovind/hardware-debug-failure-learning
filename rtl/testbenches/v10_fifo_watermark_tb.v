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
