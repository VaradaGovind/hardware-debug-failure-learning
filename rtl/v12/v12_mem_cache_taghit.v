// Case: v12_mem_cache_taghit
// Domain: memory_controller
// Provenance: Open-Source EDA IP (Apache-2.0)
// Design: cache_controller_l1

`timescale 1ns/1ps

module v12_mem_cache_taghit (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg tag_hit,
    output reg busy,
    output reg err_flag
);


    reg [15:0] stored_tag;
    reg line_valid;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stored_tag <= 16'hA5A5;
            line_valid <= 1'b0; // Uninitialized line
            tag_hit <= 1'b0;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // Buggy line:
            tag_hit <= (stored_tag == in_data[31:16]);
            out_data <= {31'd0, tag_hit};
        end
    end


endmodule
