// Testbench for: v12_mem_sdram_refresh
`timescale 1ns/1ps

module v12_mem_sdram_refresh_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire [3:0] refresh_cnt;
    wire busy;
    wire err_flag;

    integer errors;

    v12_mem_sdram_refresh uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .refresh_cnt(refresh_cnt),
        .busy(busy),
        .err_flag(err_flag)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0;
        rst_n = 0;
        enable = 0;
        in_data = 32'd0;
        errors = 0;


        // Enable bus activity for 12 cycles
        #20 rst_n = 1;
        #10 enable = 1;
        #120;
        // In correct fix, refresh_cnt decrements and reaches 0, latching out_data == FEED0001
        if (out_data != 32'hFEED0001) begin
            $display("[ASSERTION_FAIL] Case v12_mem_sdram_refresh: Refresh counter failed to trigger refresh pulse!");
            errors = errors + 1;
        end


        if (errors > 0) begin
            $display("TEST FAILED with %0d errors.", errors);
            $finish(1);
        end else begin
            $display("TEST PASSED.");
            $finish(0);
        end
    end

endmodule
