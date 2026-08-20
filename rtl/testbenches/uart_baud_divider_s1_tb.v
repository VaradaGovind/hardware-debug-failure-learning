
module tb;
    reg clk, rst_n;
    
    
    
    reg start; wire tx; uart dut(.*);
    

    initial begin
        $dumpfile("C:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/rtl/uart_baud_divider_s1.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0;
        
        
        start = 0;
        
        #20 rst_n = 1;
        
        
        
        
        #10 start = 1; #40 start = 0;
        
        
        #20;
        $display("FAIL: UART_BAUD_DIVIDER Source Anomaly (S1)");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
