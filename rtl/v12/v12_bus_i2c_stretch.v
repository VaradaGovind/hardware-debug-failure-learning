// Case: v12_bus_i2c_stretch
// Domain: bus_controller
// Provenance: CirFix_ASPLOS22 / OpenCores (LGPL)
// Design: i2c_master_bit_ctrl

`timescale 1ns/1ps

module v12_bus_i2c_stretch (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg slave_wait,
    output reg busy,
    output reg err_flag
);


    wire scl_oen = 1'b1;
    wire scl_sync = in_data[0]; // SCL line state (0 = stretched by slave)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            slave_wait <= 1'b0;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            slave_wait <= 1'b0;
            out_data <= {31'd0, slave_wait};
        end
    end


endmodule
