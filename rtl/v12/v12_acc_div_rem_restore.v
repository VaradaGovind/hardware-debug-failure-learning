// Case: v12_acc_div_rem_restore
// Domain: crypto_arithmetic
// Provenance: CirFix_ASPLOS22 / OpenCores (MIT)
// Design: divider_radix2

`timescale 1ns/1ps

module v12_acc_div_rem_restore (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [15:0] rem_reg,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rem_reg <= 16'hFFFE; // Negative remainder (-2)
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // divisor = 4; restore adds 4 to yield +2
            // Buggy line:
            rem_reg <= rem_reg;
            out_data <= {16'd0, rem_reg};
        end
    end


endmodule
