// Testbench for: v12_mem_sdram_adv_neg
`timescale 1ns/1ps

module v12_mem_sdram_adv_neg_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire [2:0] col_mask;
    wire busy;
    wire err_flag;

    integer errors;

    v12_mem_sdram_adv_neg uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .col_mask(col_mask),
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
        #10 enable = 1; in_data = 32'h00000005; // 3'b101
        #30;
        if (col_mask != 3'b101) begin
            $display("[ASSERTION_FAIL] Case v12_mem_sdram_adv_neg: col_mask was 3'b%b, expected 3'b101!", col_mask);
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
