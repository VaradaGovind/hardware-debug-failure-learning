module v10_pipe_4stage_deep(
    input clk, input rst_n, input val_in, input [7:0] dat_in,
    output reg val_out, output reg [7:0] dat_out
);
    reg stg1_tok, stg2_tok, stg3_tok; reg [7:0] d1_reg, d2_reg, d3_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stg1_tok <= 0; stg2_tok <= 0; stg3_tok <= 0; val_out <= 0;
            d1_reg <= 0; d2_reg <= 0; d3_reg <= 0; dat_out <= 0;
        end else begin
            stg1_tok <= val_in;
            d1_reg <= dat_in;
            stg2_tok <= stg1_tok && val_in; // Token drop on stg2_tok
            d2_reg <= d1_reg;
            stg3_tok <= stg2_tok;
            d3_reg <= d2_reg;
            val_out <= stg3_tok;
            dat_out <= d3_reg;
        end
    end
endmodule
