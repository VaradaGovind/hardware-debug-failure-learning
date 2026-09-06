// Case: v12_bus_i2c_startsetup
// Domain: bus_controller
// Provenance: CirFix_ASPLOS22 / OpenCores (LGPL)
// Design: i2c_master_bit_ctrl

`timescale 1ns/1ps

module v12_bus_i2c_startsetup (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg sda_oen,
    output reg busy,
    output reg err_flag
);


    reg [2:0] scl_hold_timer;
    wire scl_hold = (scl_hold_timer >= 3'd3);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            scl_hold_timer <= 3'd0;
            sda_oen <= 1'b1;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            scl_hold_timer <= scl_hold_timer + 1;
            // Buggy line:
            sda_oen <= (in_data[0]) ? 1'b0 : 1'b1;
            out_data <= {31'd0, sda_oen};
        end
    end


endmodule
