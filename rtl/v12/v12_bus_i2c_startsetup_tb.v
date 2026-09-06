// Testbench for: v12_bus_i2c_startsetup
`timescale 1ns/1ps

module v12_bus_i2c_startsetup_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire sda_oen;
    wire busy;
    wire err_flag;

    integer errors;

    v12_bus_i2c_startsetup uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .sda_oen(sda_oen),
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
        #10 enable = 1; in_data = 32'h1; // Start command active
        #15; // At T=45 (scl_hold_timer=1 < 3), sda_oen must not have fallen yet
        if (sda_oen == 1'b0) begin
            $display("[ASSERTION_FAIL] Case v12_bus_i2c_startsetup: sda_oen fell before SCL hold duration satisfied!");
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
