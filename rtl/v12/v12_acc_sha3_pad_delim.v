// Case: v12_acc_sha3_pad_delim
// Domain: crypto_arithmetic
// Provenance: CirFix_ASPLOS22 / OpenCores (MIT)
// Design: sha3_keccak_padder

`timescale 1ns/1ps

module v12_acc_sha3_pad_delim (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [7:0] delim_byte,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            delim_byte <= 8'h00;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            delim_byte <= 8'h01;
            out_data <= {24'd0, delim_byte};
        end
    end


endmodule
