// Case: v12_bus_i2c_inc_trace
// Domain: bus_controller
// Provenance: CirFix_ASPLOS22 / OpenCores (LGPL)
// Design: i2c_master_bit_ctrl

`timescale 1ns/1ps

module v12_bus_i2c_inc_trace (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [1:0] scl_timer,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            scl_timer <= 2'd0;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            scl_timer <= scl_timer + 1;
            out_data <= {30'd0, scl_timer};
        end
    end


endmodule
