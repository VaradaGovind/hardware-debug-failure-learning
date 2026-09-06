module v10_pipe_2stage_decoupled(
    input clk, input rst_n, input in_valid, input [7:0] in_data,
    output reg out_valid, output reg [7:0] out_data
);
    reg s1_valid; reg [7:0] s1_data;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s1_valid <= 1'b0; s1_data <= 8'h00; out_valid <= 1'b0; out_data <= 8'h00;
        end else begin
            s1_valid <= in_valid;
            s1_data <= in_data;
            out_valid <= (s1_valid && in_valid); // Stall drop on s1_valid
            out_data <= s1_data + 8'h01;
        end
    end
endmodule
