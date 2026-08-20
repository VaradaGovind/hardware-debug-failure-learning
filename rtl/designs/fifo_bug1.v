`timescale 1ns / 1ps

module fifo #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16
) (
    input wire clk,
    input wire rst_n,
    input wire write_en,
    input wire [DATA_WIDTH-1:0] write_data,
    input wire read_en,
    output reg [DATA_WIDTH-1:0] read_data,
    output wire full,
    output wire empty
);

    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    reg [4:0] write_ptr;
    reg [4:0] read_ptr;
    reg [5:0] count;

    // BUG 1: full condition is count == DEPTH - 1 (off by one)
    assign full = (count == DEPTH - 1); 
    assign empty = (count == 0);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            write_ptr <= 0;
            read_ptr <= 0;
            count <= 0;
        end else begin
            if (write_en && !full) begin
                mem[write_ptr] <= write_data;
                write_ptr <= (write_ptr + 1) % DEPTH;
                count <= count + 1;
            end
            if (read_en && !empty) begin
                read_data <= mem[read_ptr];
                read_ptr <= (read_ptr + 1) % DEPTH;
                count <= count - 1;
            end
            // Handle simultaneous read and write count update correctly
            if (write_en && !full && read_en && !empty) begin
                count <= count; // count stays same
            end
        end
    end

endmodule
