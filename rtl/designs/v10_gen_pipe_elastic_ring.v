module v10_gen_pipe_elastic_ring(
    input clk, input rst_n, input ring_inject, input [7:0] packet_id,
    output reg route_valid, output reg ring_eject
);
    reg [3:0] token_ring; reg [7:0] p_storage;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            token_ring <= 4'b0001; p_storage <= 0; route_valid <= 0; ring_eject <= 0;
        end else begin
            if (ring_inject) begin
                p_storage <= packet_id;
                token_ring <= {token_ring[2:0], 1'b0}; // Bug on token_ring
            end else begin
                token_ring <= {token_ring[2:0], token_ring[3]};
            end
            route_valid <= (token_ring != 4'b0000);
            ring_eject <= (token_ring[3] == 1'b1);
        end
    end
endmodule
