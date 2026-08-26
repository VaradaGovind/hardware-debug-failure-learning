
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data;
    wire [7:0] read_data;
    wire full, empty;

    fifo dut(.*);

    initial begin
        $dumpfile("fifo_f5.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 8'h10;
        #10 rst_n = 1;

        // Initial 2 writes
        #10 write_en = 1; write_data = 8'hA1;
        #10 write_en = 1; write_data = 8'hA2;
        #10 write_en = 0;

        // Simultaneous RW burst for 4 cycles 
        repeat(4) begin
            #10 write_en = 1; read_en = 1; write_data = write_data + 1;
        end
        #10 write_en = 0; read_en = 0;

        // Drain the FIFO: Attempt to read remaining items
        // read_ptr skipped by 2 on each read, so read_ptr desynchronized and stalled
        #10 read_en = 1;
        #10 read_en = 1;
        #10 read_en = 0;
        #10;
        if (dut.read_ptr !== 12 || dut.count !== 2) begin
            $display("FAIL: Read Stalled / Data Underflow");
        end
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
