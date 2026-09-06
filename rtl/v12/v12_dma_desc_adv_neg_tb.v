// Testbench for: v12_dma_desc_adv_neg
`timescale 1ns/1ps

module v12_dma_desc_adv_neg_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire [1:0] chan_prio;
    wire busy;
    wire err_flag;

    integer errors;

    v12_dma_desc_adv_neg uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .chan_prio(chan_prio),
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
        #10 enable = 1; in_data = 32'h1; // Higher priority on Channel 0
        #20;
        if (chan_prio != 2'b01) begin
            $display("[ASSERTION_FAIL] Case v12_dma_desc_adv_neg: chan_prio was %0d, expected 1!", chan_prio);
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
