module v10_fsm_hierarchical_seq(
    input clk, input rst_n, input start_pulse, output reg seq_done, output reg out_flag
);
    reg [1:0] main_state; reg [2:0] sub_state;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            main_state <= 2'd0; sub_state <= 3'd0; seq_done <= 0; out_flag <= 0;
        end else begin
            case (main_state)
                2'd0: begin
                    seq_done <= 0;
                    if (start_pulse) begin main_state <= 2'd1; sub_state <= 3'd0; end
                end
                2'd1: begin
                    if (sub_state == 3'd1) sub_state <= 3'd4; // Bug on sub_state
                    else sub_state <= sub_state + 1;
                    if (sub_state == 3'd4) main_state <= 2'd2;
                end
                2'd2: begin
                    seq_done <= 1'b1; out_flag <= (sub_state == 3'd4); main_state <= 2'd0;
                end
            endcase
        end
    end
endmodule
