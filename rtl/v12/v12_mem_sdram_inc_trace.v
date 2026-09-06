// Case: v12_mem_sdram_inc_trace
// Domain: memory_controller
// Provenance: CirFix_ASPLOS22 / OpenCores (MIT)
// Design: sdram_controller

`timescale 1ns/1ps

module v12_mem_sdram_inc_trace (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [1:0] cas_timer,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cas_timer <= 2'd0;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            cas_timer <= cas_timer - 1;
            out_data <= {30'd0, cas_timer};
        end
    end


endmodule
