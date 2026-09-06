`timescale 1ns/1ps
module v10_val_pipe_3stage_split_tb;
    reg clk, rst_n, p_in_val; reg [7:0] p_in_dat;
    wire p_out_val; wire [7:0] p_out_dat;
    v10_val_pipe_3stage_split dut(
        .clk(clk), .rst_n(rst_n), .p_in_val(p_in_val), .p_in_dat(p_in_dat),
        .p_out_val(p_out_val), .p_out_dat(p_out_dat)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_val_pipe_3stage_split.vcd");
        $dumpvars(0, v10_val_pipe_3stage_split_tb);
        clk = 0; rst_n = 0; p_in_val = 0; p_in_dat = 0;
        #15 rst_n = 1;
        #10 p_in_val = 1; p_in_dat = 8'hCC;
        #10 p_in_val = 0; p_in_dat = 8'h00;
        #25;
        if (p_out_val == 0) $display("[ASSERTION FAILURE] Cycle T=45: Disjoint validation pipeline token dropped on p1_val!");
        #20 $finish;
    end
endmodule
