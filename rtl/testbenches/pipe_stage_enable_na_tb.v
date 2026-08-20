
module tb;
    reg clk, rst_n, valid_in;
    reg [7:0] d_in;
    wire valid_out;
    wire [7:0] d_out;
    pipeline dut(.*);
    initial begin
        $dumpfile("C:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/rtl/pipe_stage_enable_na.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; valid_in = 0; d_in = 8'h00;
        #20 rst_n = 1;
        #10 valid_in = 1; d_in = 8'h99; #10 valid_in = 0; #20;
        #20;
        $display("FAIL: Protocol Stalled (P2)");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
