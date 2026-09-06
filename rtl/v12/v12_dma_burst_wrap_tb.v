// Testbench for: v12_dma_burst_wrap
`timescale 1ns/1ps

module v12_dma_burst_wrap_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire [31:0] burst_addr;
    wire busy;
    wire err_flag;

    integer errors;

    v12_dma_burst_wrap uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .burst_addr(burst_addr),
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
        #10 enable = 1;
        #20; // When wrapping at 4KB boundary, upper bits [31:12] must stay 10000
        if (burst_addr[31:12] != 20'h10000) begin
            $display("[ASSERTION_FAIL] Case v12_dma_burst_wrap: burst_addr crossed 4KB boundary to %h!", burst_addr);
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
