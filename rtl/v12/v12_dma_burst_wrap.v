// Case: v12_dma_burst_wrap
// Domain: dma_control
// Provenance: Open-Source EDA IP (Apache-2.0)
// Design: dma_controller_sg

`timescale 1ns/1ps

module v12_dma_burst_wrap (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [31:0] burst_addr,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            burst_addr <= 32'h10000FFC; // Top of 4KB page
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            burst_addr <= burst_addr + 4;
            out_data <= burst_addr;
        end
    end


endmodule
