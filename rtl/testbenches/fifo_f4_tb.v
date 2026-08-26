
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data;
    wire [7:0] read_data;
    wire full, empty;

    fifo dut(.*);

    initial begin
        $dumpfile("fifo_f4.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 8'h20;
        #10 rst_n = 1;

        // Write 1 item into empty FIFO
        #10 write_en = 1; write_data = 8'hBB;
        #10 write_en = 0;

        // Attempt to read that 1 item back.
        // empty is TRUE even though 1 item is present!
        #10 read_en = 1;
        #10 read_en = 0;
        #10;
        if (empty) begin
            $display("FAIL: Read Stalled / Data Underflow");
        end
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
