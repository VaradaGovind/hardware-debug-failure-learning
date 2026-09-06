`timescale 1ns/1ps
module v10_pipe_credit_backpressure_tb;
    reg clk, rst_n, tx_req, rx_ack; reg [7:0] tx_data;
    wire tx_valid; wire [7:0] tx_out;
    v10_pipe_credit_backpressure dut(
        .clk(clk), .rst_n(rst_n), .tx_req(tx_req), .tx_data(tx_data),
        .rx_ack(rx_ack), .tx_valid(tx_valid), .tx_out(tx_out)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_pipe_credit_backpressure.vcd");
        $dumpvars(0, v10_pipe_credit_backpressure_tb);
        clk = 0; rst_n = 0; tx_req = 0; tx_data = 0; rx_ack = 0;
        #15 rst_n = 1;
        #10 tx_req = 1; tx_data = 8'h77;
        #10 tx_req = 1; tx_data = 8'h88;
        #10 tx_req = 1; tx_data = 8'h99;
        #20;
        if (dut.credit_count == 0) $display("[ASSERTION FAILURE] Cycle T=45: Credit buffer exhaustion on credit_count!");
        #20 $finish;
    end
endmodule
