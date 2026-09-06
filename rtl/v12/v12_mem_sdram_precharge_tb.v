// Testbench for: v12_mem_sdram_precharge
`timescale 1ns/1ps

module v12_mem_sdram_precharge_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire [2:0] precharge_timer;
    wire busy;
    wire err_flag;

    integer errors;

    v12_mem_sdram_precharge uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .precharge_timer(precharge_timer),
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


        #20 rst_n = 1;
        #35; // At T=55 (3 cycles into precharge), timer should be 3
        if (precharge_timer < 3) begin
            $display("[ASSERTION_FAIL] Case v12_mem_sdram_precharge: Exited precharge with timer=%0d < 3!", precharge_timer);
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
