module v10_axi_split_transfer(
    input clk, input rst_n, input tstart, input tready_in,
    output reg tvalid_out, output reg tlast_out, output reg [7:0] tdata_out
);
    reg [2:0] chunk_idx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            chunk_idx <= 0; tvalid_out <= 0; tlast_out <= 0; tdata_out <= 0;
        end else begin
            if (tstart) begin
                tvalid_out <= 1'b1; chunk_idx <= 3'd0; tdata_out <= 8'h10;
            end else if (tvalid_out && !tready_in) begin
                tvalid_out <= 1'b0; // Bug on tvalid_out
            end else if (tvalid_out && tready_in) begin
                chunk_idx <= chunk_idx + 1; tdata_out <= tdata_out + 8'h10;
                if (chunk_idx == 3'd3) begin
                    tlast_out <= 1'b1; tvalid_out <= 1'b0;
                end
            end
        end
    end
endmodule
