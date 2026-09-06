// Case: v12_mem_sdram_refresh
// Domain: memory_controller
// Provenance: CirFix_ASPLOS22 / OpenCores (MIT)
// Design: sdram_controller

`timescale 1ns/1ps

module v12_mem_sdram_refresh (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [3:0] refresh_cnt,
    output reg busy,
    output reg err_flag
);


    localparam REFRESH_PERIOD = 4'd8;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            refresh_cnt <= REFRESH_PERIOD;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else begin
            busy <= enable;
            // Buggy line:
            refresh_cnt <= (busy) ? refresh_cnt : refresh_cnt - 1;
            if (refresh_cnt == 0) begin
                out_data <= 32'hFEED0001;
            end
        end
    end


endmodule
