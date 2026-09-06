// Case: v12_mem_sdram_bankdec
// Domain: memory_controller
// Provenance: CirFix_ASPLOS22 / OpenCores (MIT)
// Design: sdram_controller

`timescale 1ns/1ps

module v12_mem_sdram_bankdec (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [1:0] bank_addr,
    output reg busy,
    output reg err_flag
);


    wire [31:0] haddr = in_data;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bank_addr <= 2'b00;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            bank_addr <= haddr[23:22];
            out_data <= {30'd0, bank_addr};
        end
    end


endmodule
