// Testbench for: v12_acc_div_quot_sign
`timescale 1ns/1ps

module v12_acc_div_quot_sign_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire sign_q;
    wire busy;
    wire err_flag;

    integer errors;

    v12_acc_div_quot_sign uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .sign_q(sign_q),
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
        #10 enable = 1; in_data = 32'h2; // dividend_sign=0, divisor_sign=1 (result should be negative 1)
        #20;
        if (sign_q != 1'b1) begin
            $display("[ASSERTION_FAIL] Case v12_acc_div_quot_sign: sign_q was %0d, expected 1 for +/- division!", sign_q);
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
