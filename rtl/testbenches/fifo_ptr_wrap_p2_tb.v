
module tb;
    reg clk, rst_n;
    reg write_en, read_en; reg [7:0] write_data; wire [7:0] read_data; wire full, empty; fifo dut(.*);
    
    
    
    

    initial begin
        $dumpfile("fifo_ptr_wrap_p2.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0;
        write_en = 0; read_en = 0; write_data = 8'h11;
        
        
        
        #20 rst_n = 1;
        
        repeat(4) begin #10 write_en = 1; read_en = 1; write_data = write_data + 1; end #10 write_en = 0; read_en = 0;
        
        
        
        
        
        #20;
        $display("FAIL: FIFO_PTR_WRAP Protocol Stalled (P2)");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
