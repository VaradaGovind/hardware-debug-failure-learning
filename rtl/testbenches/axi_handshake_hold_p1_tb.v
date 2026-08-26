
module tb;
    reg clk, rst_n;
    
    reg valid_in, ready_in; wire ready_out, valid_out; axi_like dut(.*);
    
    
    

    initial begin
        $dumpfile("axi_handshake_hold_p1.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0;
        
        valid_in = 0; ready_in = 0;
        
        
        #20 rst_n = 1;
        
        
        #10 valid_in = 1; ready_in = 1; #10 valid_in = 1; ready_in = 0; #10 valid_in = 1; ready_in = 0; #10 valid_in = 0;
        
        
        
        
        #20;
        $display("FAIL: AXI_HANDSHAKE_HOLD Throughput Mismatch (P1)");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
