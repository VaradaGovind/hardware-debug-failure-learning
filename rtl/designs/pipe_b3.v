
module pipeline(input clk, input rst_n, input valid_in, input [7:0] d_in, output reg valid_out, output reg [7:0] d_out);
    reg v1; reg [7:0] d1;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin v1<=0; valid_out<=0; end else begin v1<=valid_in; d1<=d_in; valid_out<=valid_in; d_out<=d1; end
    end
endmodule
