
module tb;
    reg clk, rst_n;
    
    
    
    
    reg valid_in; reg [7:0] d_in; wire valid_out; wire [7:0] d_out; pipeline dut(.*);

    initial begin
        $dumpfile("C:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/rtl/pipe_stall_bubble_p1.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0;
        
        
        
        valid_in = 0; d_in = 8'h22;
        #20 rst_n = 1;
        
        
        
        
        
        #10 valid_in = 1; d_in = 8'hAA; #10 valid_in = 1; d_in = 8'hBB; #10 valid_in = 0;
        
        #20;
        $display("FAIL: PIPE_STALL_BUBBLE Throughput Mismatch (P1)");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
