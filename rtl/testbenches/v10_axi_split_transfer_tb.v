`timescale 1ns/1ps
module v10_axi_split_transfer_tb;
    reg clk, rst_n, tstart, tready_in;
    wire tvalid_out, tlast_out; wire [7:0] tdata_out;
    v10_axi_split_transfer dut(
        .clk(clk), .rst_n(rst_n), .tstart(tstart), .tready_in(tready_in),
        .tvalid_out(tvalid_out), .tlast_out(tlast_out), .tdata_out(tdata_out)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_axi_split_transfer.vcd");
        $dumpvars(0, v10_axi_split_transfer_tb);
        clk = 0; rst_n = 0; tstart = 0; tready_in = 0;
        #15 rst_n = 1;
        #10 tstart = 1;
        #10 tstart = 0; tready_in = 0;
        #20;
        if (tvalid_out == 0) $display("[ASSERTION FAILURE] Cycle T=35: AXI Handshake Hold violation on tvalid_out!");
        #20 $finish;
    end
endmodule
