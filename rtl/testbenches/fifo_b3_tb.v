
module tb;
    reg clk, rst_n, write_en, read_en; reg [7:0] write_data; wire [7:0] read_data; wire full, empty;
    fifo dut(.*);
    initial begin
        $dumpfile("fifo_b3.vcd"); $dumpvars(0, tb); clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 0;
        #10 rst_n = 1; #10 write_en = 1; write_data = 8'hAA; #10 write_en = 0; #10 read_en = 1; #10 read_en = 0;
        if (read_data !== 8'hAA) $display("FAIL: Data Mismatch");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
