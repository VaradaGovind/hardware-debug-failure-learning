
module fsm(input clk, input rst_n, input start, output reg done);
    reg [1:0] state;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin state <= 0; done <= 0; end
        else begin
            case(state)
                0: if (start) begin if (start) state <= 1; else state <= 0; end
                1: state <= 2;
                2: begin state <= 0; done <= 1; end
            endcase
        end
    end
endmodule
