
module uart(input clk, input rst_n, input start, output reg tx);
    reg [2:0] cnt;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin cnt<=0; tx<=1; end else begin if(start) cnt<=cnt+1; if(cnt==8) tx<=0; end
    end
endmodule
