// Testbench for: v12_bus_spi_cpolphase
`timescale 1ns/1ps

module v12_bus_spi_cpolphase_tb;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] in_data;
    wire [31:0] out_data;
    wire sck_reg;
    wire busy;
    wire err_flag;

    integer errors;

    v12_bus_spi_cpolphase uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .in_data(in_data),
        .out_data(out_data),
        .sck_reg(sck_reg),
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
        #10 enable = 1; in_data = 32'h1; // CPOL=1, idle state must be 1
        #30;
        if (sck_reg != 1'b1) begin
            $display("[ASSERTION_FAIL] Case v12_bus_spi_cpolphase: sck_reg was %0d, expected 1 when CPOL=1!", sck_reg);
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
