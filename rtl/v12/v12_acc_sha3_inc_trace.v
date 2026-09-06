// Case: v12_acc_sha3_inc_trace
// Domain: crypto_arithmetic
// Provenance: CirFix_ASPLOS22 / OpenCores (MIT)
// Design: sha3_keccak_padder

`timescale 1ns/1ps

module v12_acc_sha3_inc_trace (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [1:0] sponge_state,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sponge_state <= 2'd1; // ABSORB
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // in_data[0] is pad_ready
            // Buggy line:
            sponge_state <= 2'd2;
            out_data <= {30'd0, sponge_state};
        end
    end


endmodule
