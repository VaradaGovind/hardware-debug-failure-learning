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
