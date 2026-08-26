
module tb;
    reg clk, rst_n, start;
    wire done;
    fsm dut(.*);
    initial begin
        $dumpfile("fsm_stuck_state_neg_c.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; start = 0;
        #20 rst_n = 1;
        #50 start = 0;
        #20;
        $display("FAIL: Unrelated test assertion timeout (Neg C)");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
