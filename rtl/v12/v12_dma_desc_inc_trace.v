// Case: v12_dma_desc_inc_trace
// Domain: dma_control
// Provenance: Open-Source EDA IP (Apache-2.0)
// Design: dma_controller_sg

`timescale 1ns/1ps

module v12_dma_desc_inc_trace (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [1:0] dma_state,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dma_state <= 2'd1; // ACTIVE
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // in_data[0] is bus_ack
            // Buggy line:
            dma_state <= 2'd2;
            out_data <= {30'd0, dma_state};
        end
    end


endmodule
