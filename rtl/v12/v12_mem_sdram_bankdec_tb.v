// Testbench for: v12_mem_sdram_bankdec
`timescale 1ns/1ps

module v12_mem_sdram_bankdec_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire [1:0] bank_addr;
    wire busy;
    wire err_flag;

    integer errors;

    v12_mem_sdram_bankdec uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .bank_addr(bank_addr),
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
        #10 enable = 1; in_data = 32'h01800000; // haddr[24:23] = 2'b11, haddr[23:22] = 2'b10
        #30;
        if (bank_addr != 2'b11) begin
            $display("[ASSERTION_FAIL] Case v12_mem_sdram_bankdec: Bank address decoded 2'b%b, expected 2'b11!", bank_addr);
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
