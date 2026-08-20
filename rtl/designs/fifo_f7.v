
module fifo(
    input clk,
    input rst_n,
    input write_en,
    input [7:0] write_data,
    input read_en,
    output reg [7:0] read_data,
    output full,
    output empty
);
    reg [7:0] mem [0:15];
    reg [4:0] write_ptr;
    reg [4:0] read_ptr;
    reg [5:0] count;
    reg transient_glitch;

    assign full = (count == 16);
    assign empty = (count == 0);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            write_ptr <= 0;
            read_ptr <= 0;
            count <= 0;
            transient_glitch <= 1;
        end else begin
            if (write_en && !full) begin
                mem[write_ptr] <= write_data;
                write_ptr <= (write_ptr + 1) % 16;
            end
            if (read_en && !empty) begin
                // DEFECT W: Static output corruption on specific read address (unrelated to RW count)
                if (read_ptr == 2)
                    read_data <= 8'h00;
                else
                    read_data <= mem[read_ptr];
                read_ptr <= (read_ptr + 1) % 16;
            end
            // Transient 1-step count anomaly on first simultaneous RW, then corrected
            if (write_en && !full && read_en && !empty) begin
                if (transient_glitch) begin
                    count <= count + 1; // 1-step anomaly occurs
                    transient_glitch <= 0;
                end else begin
                    count <= count; // then properly maintained
                end
            end else if (write_en && !full) begin
                count <= count + 1;
            end else if (read_en && !empty) begin
                count <= count - 1;
            end
            // Self-correct count to pointer distance after 2 cycles, so no propagation occurs
            if (!transient_glitch && count != ((write_ptr - read_ptr) % 16)) begin
                count <= (write_ptr - read_ptr) % 16;
            end
        end
    end
endmodule
