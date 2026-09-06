// Testbench for: v12_arb_rr_adv_neg
`timescale 1ns/1ps

module v12_arb_rr_adv_neg_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire [1:0] comb_grant;
    wire busy;
    wire err_flag;

    integer errors;

    v12_arb_rr_adv_neg uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .comb_grant(comb_grant),
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
        #10 enable = 1; in_data = 32'h3; // Both requests active
        #20;
        if (comb_grant == 2'b11) begin
            $display("[ASSERTION_FAIL] Case v12_arb_rr_adv_neg: Simultaneous dual grant glitch occurred!");
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
