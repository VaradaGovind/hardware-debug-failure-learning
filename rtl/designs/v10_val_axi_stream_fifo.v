module v10_val_axi_stream_fifo(
    input clk, input rst_n, input strm_val_in, output reg strm_rdy_out, output reg strm_val_out
);
    reg strm_val, strm_rdy; reg [2:0] occupancy_tok;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            strm_val <= 0; strm_rdy <= 1; occupancy_tok <= 0; strm_rdy_out <= 1; strm_val_out <= 0;
        end else begin
            if (strm_val_in && strm_rdy_out) begin
                occupancy_tok <= occupancy_tok + 1; strm_val <= 1'b1;
            end else begin
                strm_val <= 1'b0; // Bug on strm_val
            end
            strm_val_out <= strm_val;
            strm_rdy_out <= (occupancy_tok < 3'd4);
        end
    end
endmodule
