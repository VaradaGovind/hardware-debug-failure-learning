// Case: v12_mem_sdram_precharge
// Domain: memory_controller
// Provenance: CirFix_ASPLOS22 / OpenCores (MIT)
// Design: sdram_controller

`timescale 1ns/1ps

module v12_mem_sdram_precharge (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [2:0] precharge_timer,
    output reg busy,
    output reg err_flag
);


    reg [3:0] state;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            precharge_timer <= 3'd0;
            state <= 4'd1; // PRECHARGE state
            busy <= 1'b1;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else begin
            if (state == 4'd1) begin
                precharge_timer <= precharge_timer + 1;
                // Buggy line:
                if (precharge_timer == 1) state <= 4'd0;
            end else begin
                busy <= 1'b0;
                out_data <= {29'd0, precharge_timer};
            end
        end
    end


endmodule
