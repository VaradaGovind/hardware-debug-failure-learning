// Case: v12_bus_spi_cpolphase
// Domain: bus_controller
// Provenance: Open-Source EDA IP (BSD)
// Design: spi_master_fifo

`timescale 1ns/1ps

module v12_bus_spi_cpolphase (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire [31:0] in_data,
    output reg [31:0] out_data,
    output reg sck_reg,
    output reg busy,
    output reg err_flag
);


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sck_reg <= 1'b0;
            busy <= 1'b0;
            out_data <= 32'd0;
            err_flag <= 1'b0;
        end else if (enable) begin
            // in_data[0] is CPOL control bit (1=idle high, 0=idle low)
            // Buggy line:
            sck_reg <= (in_data[0]) ? 1'b0 : 1'b1;
            out_data <= {31'd0, sck_reg};
        end
    end


endmodule
