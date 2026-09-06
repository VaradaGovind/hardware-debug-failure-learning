module v10_pipe_3stage_hazard(
    input clk, input rst_n, input in_valid, input [7:0] in_payload,
    output reg out_valid, output reg [7:0] out_payload
);
    reg stage1_vld, stage2_vld; reg [7:0] op_reg, fwd_data;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stage1_vld <= 0; stage2_vld <= 0; out_valid <= 0;
            op_reg <= 0; fwd_data <= 0; out_payload <= 0;
        end else begin
            stage1_vld <= in_valid;
            op_reg <= in_payload;
            stage2_vld <= stage1_vld;
            fwd_data <= op_reg; // RAW data hazard on fwd_data
            out_valid <= stage2_vld;
            out_payload <= fwd_data;
        end
    end
endmodule
