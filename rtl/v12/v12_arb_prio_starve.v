// Case: v12_arb_prio_starve
// Domain: arbitration
// Provenance: Open-Source EDA IP (Apache-2.0)
// Design: arbiter_priority

`timescale 1ns/1ps

module v12_arb_prio_starve (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg [3:0] starve_timeout,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            starve_timeout <= 4'd0;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            starve_timeout <= 4'd0;
            out_data <= {28'd0, starve_timeout};
        end
    end


endmodule
