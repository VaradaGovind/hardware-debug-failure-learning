
module tb;
    reg clk, rst_n, valid_in; reg [7:0] d_in; wire valid_out; wire [7:0] d_out;
    pipeline dut(.*);
    initial begin
        $dumpfile("pipe_b5.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; valid_in=0; d_in=0;
        #10 rst_n=1; valid_in=1; d_in=8'hFF; #10 valid_in=0; #30 if(d_out!==8'hFF) $display("FAIL: Data Loss"); #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
