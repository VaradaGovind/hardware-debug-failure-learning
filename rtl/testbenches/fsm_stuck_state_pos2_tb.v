
module tb;
    reg clk, rst_n, start;
    wire done;
    fsm dut(.*);
    initial begin
        $dumpfile("fsm_stuck_state_pos2.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; start = 0;
        #20 rst_n = 1;
        #10 start = 1; #10 start = 0; #10 start = 1; #10 start = 0; #20;
        #20;
        $display("FAIL: FSM Stuck in IDLE (Pos 2)");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
