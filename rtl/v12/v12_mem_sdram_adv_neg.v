// Case: v12_mem_sdram_adv_neg
// Domain: memory_controller
// Provenance: CirFix_ASPLOS22 / OpenCores (MIT)
// Design: sdram_controller

`timescale 1ns/1ps

module v12_mem_sdram_adv_neg (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [2:0] col_mask,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            col_mask <= 3'd0;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            col_mask <= ~in_data[2:0];
            out_data <= {29'd0, col_mask};
        end
    end


endmodule
