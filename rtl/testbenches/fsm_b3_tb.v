
module tb;
    reg clk, rst_n, start; wire done;
    fsm dut(.*);
    initial begin
        $dumpfile("./rtl/fsm_b3.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; start=0;
        #10 rst_n=1; start=1; #30 if(!done) $display("FAIL: Stuck State"); #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
