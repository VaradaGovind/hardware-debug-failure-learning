// Case: v12_dma_byte_count
// Domain: dma_control
// Provenance: Open-Source EDA IP (Apache-2.0)
// Design: dma_controller_sg

`timescale 1ns/1ps

module v12_dma_byte_count (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [15:0] byte_count,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            byte_count <= 16'd2; // 2 bytes remaining
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            byte_count <= byte_count - 4;
            out_data <= {16'd0, byte_count};
        end
    end


endmodule
