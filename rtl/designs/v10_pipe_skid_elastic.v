module v10_pipe_skid_elastic(
    input clk, input rst_n, input push_val, input [7:0] push_dat, input pop_rdy,
    output reg out_vld, output reg [7:0] out_dat
);
    reg skid_vld, main_vld; reg [7:0] skid_payload, main_payload;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            skid_vld <= 0; main_vld <= 0; out_vld <= 0;
            skid_payload <= 0; main_payload <= 0; out_dat <= 0;
        end else begin
            if (push_val && !pop_rdy) begin
                skid_vld <= 1'b0; // Bug on skid_vld
                skid_payload <= push_dat;
            end
            if (pop_rdy) begin
                main_vld <= push_val;
                main_payload <= push_dat;
                out_vld <= main_vld;
                out_dat <= main_payload;
            end
        end
    end
endmodule
