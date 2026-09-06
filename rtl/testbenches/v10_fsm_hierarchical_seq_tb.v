`timescale 1ns/1ps
module v10_fsm_hierarchical_seq_tb;
    reg clk, rst_n, start_pulse;
    wire seq_done, out_flag;
    v10_fsm_hierarchical_seq dut(
        .clk(clk), .rst_n(rst_n), .start_pulse(start_pulse),
        .seq_done(seq_done), .out_flag(out_flag)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_fsm_hierarchical_seq.vcd");
        $dumpvars(0, v10_fsm_hierarchical_seq_tb);
        clk = 0; rst_n = 0; start_pulse = 0;
        #15 rst_n = 1;
        #10 start_pulse = 1;
        #10 start_pulse = 0;
        #40;
        if (dut.sub_state != 3'd4) $display("[ASSERTION FAILURE] Cycle T=45: FSM sub-state skip on sub_state!");
        #20 $finish;
    end
endmodule
