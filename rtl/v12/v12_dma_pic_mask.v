// Case: v12_dma_pic_mask
// Domain: dma_control
// Provenance: Open-Source EDA IP (Apache-2.0)
// Design: interrupt_controller_pic

`timescale 1ns/1ps

module v12_dma_pic_mask (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg irq_pending,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            irq_pending <= 1'b1; // Interrupt arrived
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // in_data[0] is cpu_ack
            // Buggy line:
            irq_pending <= 1'b0;
            out_data <= {31'd0, irq_pending};
        end
    end


endmodule
