// Case: v12_acc_sha3_adv_neg
// Domain: crypto_arithmetic
// Provenance: CirFix_ASPLOS22 / OpenCores (MIT)
// Design: sha3_keccak_padder

`timescale 1ns/1ps

module v12_acc_sha3_adv_neg (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [4:0] round_cnt,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            round_cnt <= 5'd22;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            round_cnt <= (round_cnt == 5'd22) ? 5'd0 : round_cnt + 1;
            out_data <= {27'd0, round_cnt};
        end
    end


endmodule
