// Case: v12_arb_rr_mask
// Domain: arbitration
// Provenance: Open-Source EDA IP (Apache-2.0)
// Design: arbiter_round_robin

`timescale 1ns/1ps

module v12_arb_rr_mask (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [3:0] req_mask,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            req_mask <= 4'd0;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            req_mask <= in_data[3:0] & 4'b0111;
            out_data <= {28'd0, req_mask};
        end
    end


endmodule
