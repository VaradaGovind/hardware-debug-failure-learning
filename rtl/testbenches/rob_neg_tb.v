
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data; wire [7:0] read_data; wire full, empty;
    fifo dut(.*);
    initial begin
        $dumpfile("rob_neg.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 8'h44;
        #60 rst_n = 1;
        #20 write_en = 1; write_data = 8'h55;
        #10 write_en = 0;
        #10 read_en = 1;
        #10 read_en = 0;
        #30 $finish;
    end
    always #5 clk = ~clk;
endmodule
