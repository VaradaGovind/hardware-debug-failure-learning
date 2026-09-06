// Case: v12_dma_desc_adv_neg
// Domain: dma_control
// Provenance: Open-Source EDA IP (Apache-2.0)
// Design: dma_controller_sg

`timescale 1ns/1ps

module v12_dma_desc_adv_neg (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [1:0] chan_prio,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            chan_prio <= 2'b00;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            chan_prio <= (in_data[0]) ? 2'b10 : 2'b01;
            out_data <= {30'd0, chan_prio};
        end
    end


endmodule
