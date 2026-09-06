// Case: v12_arb_grant_lock
// Domain: arbitration
// Provenance: Open-Source EDA IP (Apache-2.0)
// Design: arbiter_round_robin

`timescale 1ns/1ps

module v12_arb_grant_lock (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg grant_locked,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            grant_locked <= 1'b0;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            grant_locked <= 1'b1;
            out_data <= {31'd0, grant_locked};
        end
    end


endmodule
