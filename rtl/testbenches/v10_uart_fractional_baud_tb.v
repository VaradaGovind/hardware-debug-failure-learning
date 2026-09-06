`timescale 1ns/1ps
module v10_uart_fractional_baud_tb;
    reg clk, rst_n, tx_enable; reg [7:0] tx_byte;
    wire serial_tx, tx_busy;
    v10_uart_fractional_baud dut(
        .clk(clk), .rst_n(rst_n), .tx_enable(tx_enable), .tx_byte(tx_byte),
        .serial_tx(serial_tx), .tx_busy(tx_busy)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_uart_fractional_baud.vcd");
        $dumpvars(0, v10_uart_fractional_baud_tb);
        clk = 0; rst_n = 0; tx_enable = 0; tx_byte = 8'hA5;
        #15 rst_n = 1;
        #10 tx_enable = 1;
        #10 tx_enable = 0;
        #50;
        if (dut.frac_acc != 0 && tx_busy == 0) $display("[ASSERTION FAILURE] Cycle T=60: UART fractional baud rate accumulator anomaly on frac_acc!");
        #20 $finish;
    end
endmodule
