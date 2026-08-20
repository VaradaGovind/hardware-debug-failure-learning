
module axi_like(input clk, input rst_n, input valid_in, output ready_out, output reg valid_out, input ready_in);
    assign ready_out=ready_in; always @(posedge clk) valid_out <= 0;
endmodule
