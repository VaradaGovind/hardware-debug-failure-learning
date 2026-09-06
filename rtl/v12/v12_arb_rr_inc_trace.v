// Case: v12_arb_rr_inc_trace
// Domain: arbitration
// Provenance: Open-Source EDA IP (Apache-2.0)
// Design: arbiter_round_robin

`timescale 1ns/1ps

module v12_arb_rr_inc_trace (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [1:0] last_granted,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            last_granted <= 2'd0;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            last_granted <= 2'd0;
            out_data <= {30'd0, last_granted};
        end
    end


endmodule
