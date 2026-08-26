
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data;
    wire [7:0] read_data;
    wire full, empty;

    fifo dut(.*);

    initial begin
        $dumpfile("fifo_f3.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 8'h50;
        #10 rst_n = 1;

        // Fill partially
        repeat(4) begin
            #10 write_en = 1; write_data = write_data + 1;
        end
        #10 write_en = 0;

        // 12 Simultaneous push-pop cycles
        repeat(12) begin
            #10 write_en = 1; read_en = 1; write_data = write_data + 1;
        end
        #10 write_en = 0; read_en = 0;

        // Read out next data item and verify it was not overwritten
        #10 read_en = 1;
        #10 read_en = 0;
        #10;
        if (read_data !== 8'h51) begin
            $display("FAIL: Memory Overwrite / Checksum Mismatch");
        end
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
