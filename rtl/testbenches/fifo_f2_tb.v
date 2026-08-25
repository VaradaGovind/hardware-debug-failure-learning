
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data;
    wire [7:0] read_data;
    wire full, empty;

    fifo dut(.*);

    initial begin
        $dumpfile("C:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/rtl/fifo_f2.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 8'h10;
        #10 rst_n = 1;

        // Initial 2 items
        #10 write_en = 1; write_data = 8'hA1;
        #10 write_en = 1; write_data = 8'hA2;
        #10 write_en = 0;

        // Simultaneous RW burst for 4 cycles
        repeat(4) begin
            #10 write_en = 1; read_en = 1; write_data = write_data + 1;
        end
        #10 write_en = 0; read_en = 0;

        // Drain the FIFO: 2 valid remaining items
        #10 read_en = 1;
        #10 read_en = 1;
        #10 read_en = 0;
        #10;
        // Verify count and pointer alignment: count should be 0
        if (dut.count !== 0 || dut.read_ptr !== dut.write_ptr) begin
            $display("FAIL: Read Stalled / Data Underflow");
        end
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
