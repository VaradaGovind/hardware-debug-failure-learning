// Case: v12_bus_i2c_ackphase
// Domain: bus_controller
// Provenance: CirFix_ASPLOS22 / OpenCores (LGPL)
// Design: i2c_master_bit_ctrl

`timescale 1ns/1ps

module v12_bus_i2c_ackphase (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg ack_rec,
    output reg busy,
    output reg err_flag
);


    reg [2:0] phase_cnt;
    wire sample_pulse = (phase_cnt == 3'd3);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase_cnt <= 3'd0;
            ack_rec <= 1'b1;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            phase_cnt <= phase_cnt + 1;
            // Buggy line:
            ack_rec <= in_data[0];
            out_data <= {31'd0, ack_rec};
        end
    end


endmodule
