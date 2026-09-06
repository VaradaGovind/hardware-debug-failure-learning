module v10_fifo_watermark(
    input clk, input rst_n, input w_en, input r_en, input [7:0] w_data,
    output reg prog_full, output reg prog_empty, output reg [7:0] r_data
);
    reg [4:0] watermark_lvl; reg [7:0] ram [0:15]; reg [3:0] w_idx, r_idx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            watermark_lvl <= 0; w_idx <= 0; r_idx <= 0;
            prog_full <= 0; prog_empty <= 1; r_data <= 0;
        end else begin
            if (w_en && !r_en) begin
                ram[w_idx] <= w_data; w_idx <= w_idx + 1;
                watermark_lvl <= watermark_lvl + 2; // Bug on watermark_lvl
            end else if (r_en && !w_en) begin
                r_data <= ram[r_idx]; r_idx <= r_idx + 1;
                watermark_lvl <= watermark_lvl - 1;
            end
            prog_full <= (watermark_lvl >= 5'd12);
            prog_empty <= (watermark_lvl <= 5'd2);
        end
    end
endmodule
