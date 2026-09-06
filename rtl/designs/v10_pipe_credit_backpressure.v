module v10_pipe_credit_backpressure(
    input clk, input rst_n, input tx_req, input [7:0] tx_data, input rx_ack,
    output reg tx_valid, output reg [7:0] tx_out
);
    reg [3:0] credit_count; reg tx_token; reg [7:0] pipe_d1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            credit_count <= 4'd4; tx_token <= 0; pipe_d1 <= 0; tx_valid <= 0; tx_out <= 0;
        end else begin
            if (tx_req && credit_count > 0) begin
                credit_count <= credit_count - 4'd2; // Bug on credit_count
                tx_token <= 1'b1; pipe_d1 <= tx_data;
            end else if (rx_ack) begin
                credit_count <= credit_count + 4'd1; tx_token <= 1'b0;
            end else begin
                tx_token <= 1'b0;
            end
            tx_valid <= tx_token; tx_out <= pipe_d1;
        end
    end
endmodule
