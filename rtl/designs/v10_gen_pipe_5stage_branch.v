module v10_gen_pipe_5stage_branch(
    input clk, input rst_n, input fetch_req, input branch_flush, output reg retire_v
);
    reg fetch_v, dec_v, ex_v, mem_v, wb_v; reg [7:0] byp_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fetch_v <= 0; dec_v <= 0; ex_v <= 0; mem_v <= 0; wb_v <= 0;
            byp_reg <= 0; retire_v <= 0;
        end else begin
            if (branch_flush) begin
                fetch_v <= 0; dec_v <= 0;
                ex_v <= 1'b1; // Bug on ex_v
            end else begin
                fetch_v <= fetch_req; dec_v <= fetch_v; ex_v <= dec_v;
            end
            mem_v <= ex_v; wb_v <= mem_v; retire_v <= wb_v;
        end
    end
endmodule
