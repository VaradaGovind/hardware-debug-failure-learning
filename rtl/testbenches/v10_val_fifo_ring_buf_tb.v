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
