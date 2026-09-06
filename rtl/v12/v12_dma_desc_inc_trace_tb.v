// Testbench for: v12_dma_desc_inc_trace
`timescale 1ns/1ps

module v12_dma_desc_inc_trace_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire [1:0] dma_state;
    wire busy;
    wire err_flag;

    integer errors;

    v12_dma_desc_inc_trace uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .dma_state(dma_state),
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
        #10 enable = 1; in_data = 32'h0; // bus_ack = 0
        #20;
        if (dma_state == 2'd2) begin
            $display("[ASSERTION_FAIL] Case v12_dma_desc_inc_trace: dma_state exited before bus_ack!");
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
