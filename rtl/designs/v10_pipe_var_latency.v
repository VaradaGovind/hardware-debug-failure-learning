module v10_pipe_var_latency(
    input clk, input rst_n, input start_calc, input [7:0] op_val,
    output reg done_strobe, output reg [7:0] res_out
);
    reg [2:0] busy_cycles; reg pipe_valid; reg [7:0] pipe_result;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy_cycles <= 0; pipe_valid <= 0; pipe_result <= 0; done_strobe <= 0; res_out <= 0;
        end else begin
            if (start_calc) begin
                busy_cycles <= 3'd1; // Bug on busy_cycles
                pipe_valid <= 1; pipe_result <= op_val ^ 8'hFF;
            end else if (busy_cycles > 0) begin
                busy_cycles <= busy_cycles - 1;
                if (busy_cycles == 1) begin
                    done_strobe <= pipe_valid; res_out <= pipe_result;
                end
            end else begin
                done_strobe <= 0;
            end
        end
    end
endmodule
