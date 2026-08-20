
module tb;
    reg clk, rst_n, start;
    wire done;
    fsm dut(.*);
    initial begin
        $dumpfile("C:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/rtl/fsm_stuck_state_pos1.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; start = 0;
        #20 rst_n = 1;
        #30 start = 1; #10 start = 0; #20;
        #20;
        $display("FAIL: FSM Stuck in IDLE (Pos 1)");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
