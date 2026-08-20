
module axi_like(input clk, input rst_n, input valid_in, output ready_out, output reg valid_out, input ready_in);
    assign ready_out = 1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) valid_out <= 0;
        else begin
            if (valid_in && !ready_in) valid_out <= 0; else if (valid_in) valid_out <= 1;
        end
    end
endmodule
