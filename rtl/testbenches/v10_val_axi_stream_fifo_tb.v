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
