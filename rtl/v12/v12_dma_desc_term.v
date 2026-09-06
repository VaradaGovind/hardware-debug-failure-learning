// Case: v12_dma_desc_term
// Domain: dma_control
// Provenance: Open-Source EDA IP (Apache-2.0)
// Design: dma_controller_sg

`timescale 1ns/1ps

module v12_dma_desc_term (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg desc_eol,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            desc_eol <= 1'b0;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            desc_eol <= 1'b0;
            out_data <= {31'd0, desc_eol};
        end
    end


endmodule
