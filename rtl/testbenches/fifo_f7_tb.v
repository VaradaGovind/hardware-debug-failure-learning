
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data;
    wire [7:0] read_data;
    wire full, empty;

    fifo dut(.*);

    initial begin
        $dumpfile("C:/Users/varad/Documents/Coding/Debugging/hardware-debug-failure-learning/rtl/fifo_f7.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 8'h70;
        #10 rst_n = 1;

        // Initial 2 items
        #10 write_en = 1; write_data = 8'h81;
        #10 write_en = 1; write_data = 8'h82;
        #10 write_en = 0;

        // Simultaneous RW cycle (Trigger occurs, 1-step anomaly occurs!)
        #10 write_en = 1; read_en = 1; write_data = 8'h83;
        #10 write_en = 0; read_en = 0;

        // Read items
        #10 read_en = 1;
        #10 read_en = 1;
        #10 read_en = 0;
        #10;
        // The failure symptom is due to read_data corrupted at read_ptr == 2, NOT count propagation
        if (read_data !== 8'h83) begin
            $display("FAIL: Data Corruption / Unrelated Bus Fault");
        end
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
