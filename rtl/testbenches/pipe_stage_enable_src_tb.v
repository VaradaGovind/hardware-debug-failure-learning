
module tb;
    reg clk, rst_n, valid_in;
    reg [7:0] d_in;
    wire valid_out;
    wire [7:0] d_out;
    pipeline dut(.*);
    initial begin
        $dumpfile("pipe_stage_enable_src.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; valid_in = 0; d_in = 8'h00;
        #20 rst_n = 1;
        #10 valid_in = 0; #20;
        #20;
        $display("FAIL: Pipeline Spurious Valid (Source)");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
