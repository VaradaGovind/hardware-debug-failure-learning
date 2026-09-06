// Testbench for: v12_bus_i2c_stretch
`timescale 1ns/1ps

module v12_bus_i2c_stretch_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire slave_wait;
    wire busy;
    wire err_flag;

    integer errors;

    v12_bus_i2c_stretch uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .slave_wait(slave_wait),
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
        #10 enable = 1; in_data = 32'h0; // SCL line is 0 (slave is stretching clock)
        #30;
        if (slave_wait != 1'b1) begin
            $display("[ASSERTION_FAIL] Case v12_bus_i2c_stretch: slave_wait failed to assert when SCL stretched low!");
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
