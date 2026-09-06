module v10_fifo_gray_ptr(
    input clk, input rst_n, input wr_strobe, input rd_strobe, input [7:0] wr_payload,
    output reg [7:0] rd_payload, output reg buf_empty, output reg buf_full
);
    reg [3:0] bin_wr_ptr, bin_rd_ptr, gray_wr_ptr, gray_rd_ptr, fifo_occ;
    reg [7:0] mem [0:7];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bin_wr_ptr <= 0; bin_rd_ptr <= 0; gray_wr_ptr <= 0; gray_rd_ptr <= 0;
            fifo_occ <= 0; buf_empty <= 1; buf_full <= 0; rd_payload <= 0;
        end else begin
            if (wr_strobe && !buf_full) begin
                mem[bin_wr_ptr[2:0]] <= wr_payload;
                bin_wr_ptr <= bin_wr_ptr + 1;
                gray_wr_ptr <= (bin_wr_ptr >> 1); // Bug on gray_wr_ptr
            end
            if (rd_strobe && !buf_empty) begin
                rd_payload <= mem[bin_rd_ptr[2:0]];
                bin_rd_ptr <= bin_rd_ptr + 1;
                gray_rd_ptr <= (bin_rd_ptr ^ (bin_rd_ptr >> 1));
            end
            fifo_occ <= bin_wr_ptr - bin_rd_ptr;
            buf_empty <= (bin_wr_ptr == bin_rd_ptr);
            buf_full <= (fifo_occ == 4'd8);
        end
    end
endmodule
