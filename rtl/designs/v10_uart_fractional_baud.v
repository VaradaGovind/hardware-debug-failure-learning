module v10_uart_fractional_baud(
    input clk, input rst_n, input tx_enable, input [7:0] tx_byte,
    output reg serial_tx, output reg tx_busy
);
    reg [4:0] frac_acc; reg [3:0] tx_bit_cnt; reg baud_tick; reg [7:0] shift_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            frac_acc <= 0; baud_tick <= 0; tx_bit_cnt <= 0; serial_tx <= 1; tx_busy <= 0; shift_reg <= 0;
        end else begin
            if (frac_acc >= 5'd6) begin // Bug on frac_acc
                frac_acc <= 0; baud_tick <= 1'b1;
            end else begin
                frac_acc <= frac_acc + 1; baud_tick <= 1'b0;
            end
            if (tx_enable && !tx_busy) begin
                tx_busy <= 1; shift_reg <= tx_byte; tx_bit_cnt <= 0; serial_tx <= 0;
            end else if (tx_busy && baud_tick) begin
                tx_bit_cnt <= tx_bit_cnt + 1;
                if (tx_bit_cnt < 8) begin
                    serial_tx <= shift_reg[0]; shift_reg <= (shift_reg >> 1);
                end else begin
                    serial_tx <= 1; tx_busy <= 0;
                end
            end
        end
    end
endmodule
