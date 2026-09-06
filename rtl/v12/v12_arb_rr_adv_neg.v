// Case: v12_arb_rr_adv_neg
// Domain: arbitration
// Provenance: Open-Source EDA IP (Apache-2.0)
// Design: arbiter_round_robin

`timescale 1ns/1ps

module v12_arb_rr_adv_neg (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [1:0] comb_grant,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            comb_grant <= 2'b00;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            comb_grant <= in_data[1:0];
            out_data <= {30'd0, comb_grant};
        end
    end


endmodule
