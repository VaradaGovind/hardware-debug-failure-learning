module v10_val_fifo_ring_buf(
    input clk, input rst_n, input push_cmd, input pop_cmd, input [7:0] data_in,
    output reg [7:0] data_out
);
    reg [3:0] head_idx, tail_idx; reg [3:0] items_avail; reg [7:0] ring_mem [0:15];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            head_idx <= 0; tail_idx <= 0; items_avail <= 0; data_out <= 0;
        end else begin
            if (push_cmd && !pop_cmd) begin
                ring_mem[head_idx] <= data_in; head_idx <= head_idx + 1;
                items_avail <= items_avail; // Bug on items_avail
            end else if (pop_cmd && !push_cmd) begin
                data_out <= ring_mem[tail_idx]; tail_idx <= tail_idx + 1;
                items_avail <= items_avail - 1;
            end
        end
    end
endmodule
