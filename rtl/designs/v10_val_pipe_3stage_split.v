module v10_val_pipe_3stage_split(
    input clk, input rst_n, input p_in_val, input [7:0] p_in_dat,
    output reg p_out_val, output reg [7:0] p_out_dat
);
    reg p1_val, p2_val; reg [7:0] p1_dat, p2_dat;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            p1_val <= 0; p2_val <= 0; p_out_val <= 0; p1_dat <= 0; p2_dat <= 0; p_out_dat <= 0;
        end else begin
            p1_val <= p_in_val; p1_dat <= p_in_dat;
            p2_val <= (p1_val && p_in_val); // Bug on p1_val
            p2_dat <= p1_dat;
            p_out_val <= p2_val; p_out_dat <= p2_dat;
        end
    end
endmodule
