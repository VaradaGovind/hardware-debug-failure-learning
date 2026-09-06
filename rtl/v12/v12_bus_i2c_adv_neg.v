// Case: v12_bus_i2c_adv_neg
// Domain: bus_controller
// Provenance: CirFix_ASPLOS22 / OpenCores (LGPL)
// Design: i2c_master_bit_ctrl

`timescale 1ns/1ps

module v12_bus_i2c_adv_neg (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg al_flag,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            al_flag <= 1'b0;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // in_data[0]=bus_mismatch, in_data[1]=stop_condition
            // Buggy line:
            al_flag <= (in_data[0]);
            out_data <= {31'd0, al_flag};
        end
    end


endmodule
