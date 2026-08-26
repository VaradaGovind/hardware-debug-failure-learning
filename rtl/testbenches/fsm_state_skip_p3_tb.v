
module tb;
    reg clk, rst_n;
    
    
    reg start; wire done; fsm dut(.*);
    
    

    initial begin
        $dumpfile("fsm_state_skip_p3.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0;
        
        
        start = 0;
        
        #20 rst_n = 1;
        
        
        
        #10 start = 1; #10 start = 0; #20;
        
        
        
        #20;
        $display("FAIL: FSM_STATE_SKIP Held-Out Sequence (P3)");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
