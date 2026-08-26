
module tb;
    reg clk, rst_n;
    
    
    reg start; wire done; fsm dut(.*);
    
    

    initial begin
        $dumpfile("fsm_output_timing_na.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0;
        
        
        start = 0;
        
        #20 rst_n = 1;
        
        
        
        #10 start = 1; #10 start = 0; #20;
        
        
        
        #20;
        $display("FAIL: FSM_OUTPUT_TIMING Protocol Stalled (P2)");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
