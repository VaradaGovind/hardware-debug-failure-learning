
module tb;
    reg clk, rst_n, start; wire tx;
    uart dut(.*);
    initial begin
        $dumpfile("uart_b5.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; start=0;
        #10 rst_n=1; start=1; #100 if(tx!==1) $display("FAIL: Bad Output"); #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
