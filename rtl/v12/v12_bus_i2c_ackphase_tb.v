// Testbench for: v12_bus_i2c_ackphase
`timescale 1ns/1ps

module v12_bus_i2c_ackphase_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire ack_rec;
    wire busy;
    wire err_flag;

    integer errors;

    v12_bus_i2c_ackphase uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .ack_rec(ack_rec),
        .busy(busy),
        .err_flag(err_flag)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0;
        rst_n = 0;
        enable = 0;
        in_data = 32'd0;
        errors = 0;


        #20 rst_n = 1;
        #10 enable = 1; in_data = 32'h1; // Idle line (T=30)
        #10 in_data = 32'h0; // T=40: slave pulls SDA low for ACK window
        #30 in_data = 32'h1; // T=70: slave releases SDA after sample pulse at T=65
        #15; // T=85: inspect holding state after phase 4
        if (ack_rec != 1'b0) begin
            $display("[ASSERTION_FAIL] Case v12_bus_i2c_ackphase: ack_rec failed to hold slave ACK!");
            errors = errors + 1;
        end


        if (errors > 0) begin
            $display("TEST FAILED with %0d errors.", errors);
            $finish(1);
        end else begin
            $display("TEST PASSED.");
            $finish(0);
        end
    end

endmodule
