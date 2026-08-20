
module tb;
    reg clk, rst_n, valid_in, ready_in; wire ready_out, valid_out;
    axi_like dut(.*);
    initial begin
        $dumpfile("./rtl/axi_b4.vcd"); $dumpvars(0, tb); clk=0; rst_n=0; valid_in=0; ready_in=0;
        #10 rst_n=1; valid_in=1; ready_in=1; #10 if(!valid_out) $display("FAIL: Timeout"); #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
