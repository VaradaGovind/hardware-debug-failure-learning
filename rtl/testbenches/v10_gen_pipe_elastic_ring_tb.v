`timescale 1ns/1ps
module v10_gen_pipe_elastic_ring_tb;
    reg clk, rst_n, ring_inject; reg [7:0] packet_id;
    wire route_valid, ring_eject;
    v10_gen_pipe_elastic_ring dut(
        .clk(clk), .rst_n(rst_n), .ring_inject(ring_inject), .packet_id(packet_id),
        .route_valid(route_valid), .ring_eject(ring_eject)
    );
    always #5 clk = ~clk;
    initial begin
        $dumpfile("v10_gen_pipe_elastic_ring.vcd");
        $dumpvars(0, v10_gen_pipe_elastic_ring_tb);
        clk = 0; rst_n = 0; ring_inject = 0; packet_id = 8'hAA;
        #15 rst_n = 1;
        #10 ring_inject = 1;
        #10 ring_inject = 0;
        #30;
        if (route_valid == 0) $display("[ASSERTION FAILURE] Cycle T=45: Circulating token collapse on token_ring!");
        #20 $finish;
    end
endmodule
