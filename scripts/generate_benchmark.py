import os
import json

def generate_benchmark(base_dir):
    designs_dir = os.path.join(base_dir, "rtl", "designs")
    tb_dir = os.path.join(base_dir, "rtl", "testbenches")
    meta_dir = os.path.join(base_dir, "datasets", "metadata")
    
    os.makedirs(designs_dir, exist_ok=True)
    os.makedirs(tb_dir, exist_ok=True)
    os.makedirs(meta_dir, exist_ok=True)

    bugs_metadata = []

# Fifo
    fifo_base = """
module fifo(input clk, input rst_n, input write_en, input [7:0] write_data, input read_en, output reg [7:0] read_data, output full, output empty);
    reg [7:0] mem [0:15]; reg [4:0] write_ptr; reg [4:0] read_ptr; reg [5:0] count;
    {full_empty_assign}
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin write_ptr <= 0; read_ptr <= 0; count <= 0; end else begin
            if (write_en && !full) begin mem[write_ptr] <= write_data; {write_ptr_assign} end
            if (read_en && !empty) begin read_data <= mem[read_ptr]; {read_ptr_assign} end
            {count_assign}
        end
    end
endmodule
"""
    fifo_tb = """
module tb;
    reg clk, rst_n, write_en, read_en; reg [7:0] write_data; wire [7:0] read_data; wire full, empty;
    fifo dut(.*);
    initial begin
        $dumpfile("VCD_PATH"); $dumpvars(0, tb); clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 0;
        #10 rst_n = 1; #10 write_en = 1; write_data = 8'hAA; #10 write_en = 0; #10 read_en = 1; #10 read_en = 0;
        if (read_data !== 8'hAA) $display("FAIL: Data Mismatch");
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""
    def write_fifo(name, bg_cls, fea, wpa, rpa, ca, symp, gs):
        bugs_metadata.append({"bug_id": name, "family": "fifo", "bug_class": bg_cls, "symptom": symp, "ground_truth_module": "fifo", "ground_truth_signals": gs})
        with open(os.path.join(designs_dir, f"{name}.v"), "w") as f: f.write(fifo_base.format(full_empty_assign=fea, write_ptr_assign=wpa, read_ptr_assign=rpa, count_assign=ca))
        with open(os.path.join(tb_dir, f"{name}_tb.v"), "w") as f: f.write(fifo_tb.replace("VCD_PATH", f"{base_dir}/rtl/{name}.vcd"))
        
    write_fifo("fifo_b1", "off_by_one", "assign full=(count==15); assign empty=(count==0);", "write_ptr<=(write_ptr+1)%16;", "read_ptr<=(read_ptr+1)%16;", "if(write_en&&!full&&read_en&&!empty) count<=count; else if(write_en&&!full) count<=count+1; else if(read_en&&!empty) count<=count-1;", "Data Mismatch", ["count"])
    write_fifo("fifo_b2", "ptr_update", "assign full=(count==16); assign empty=(count==0);", "write_ptr<=write_ptr+1;", "read_ptr<=(read_ptr+1)%16;", "if(write_en&&!full&&read_en&&!empty) count<=count; else if(write_en&&!full) count<=count+1; else if(read_en&&!empty) count<=count-1;", "Data Mismatch", ["write_ptr"])
    write_fifo("fifo_b3", "ptr_update", "assign full=(count==16); assign empty=(count==0);", "write_ptr<=(write_ptr+1)%16;", "read_ptr<=read_ptr+1;", "if(write_en&&!full&&read_en&&!empty) count<=count; else if(write_en&&!full) count<=count+1; else if(read_en&&!empty) count<=count-1;", "Data Mismatch", ["read_ptr"])
    write_fifo("fifo_b4", "simultaneous_rw", "assign full=(count==16); assign empty=(count==0);", "write_ptr<=(write_ptr+1)%16;", "read_ptr<=(read_ptr+1)%16;", "if(write_en&&!full) count<=count+1; else if(read_en&&!empty) count<=count-1;", "Data Mismatch", ["count"])
    write_fifo("fifo_b5", "count_overflow", "assign full=(count==16); assign empty=(count==0);", "write_ptr<=(write_ptr+1)%16;", "read_ptr<=(read_ptr+1)%16;", "if(write_en&&!full&&read_en&&!empty) count<=count; else if(write_en&&!full) count<=count+2; else if(read_en&&!empty) count<=count-1;", "Data Mismatch", ["count"])
    # Adversarial (Bug 6): The bug is actually the clock/reset (clk inverted or reset held), but the symptom is the same. Usually clk is a dead-end to query. We simulate this by breaking the write enable via a phantom reset block
    write_fifo("fifo_b6", "rst_bug", "assign full=(count==16); assign empty=(count==0);", "write_ptr<=(write_ptr+1)%16;", "read_ptr<=(read_ptr+1)%16;", "if(!rst_n) count<=0; else if(write_en&&!full&&read_en&&!empty) count<=count; else if(write_en&&!full) count<=count+1; else if(read_en&&!empty) count<=count-1;", "Data Mismatch", ["rst_n"])

    # AXI-like
    axi_base = """
module axi_like(input clk, input rst_n, input valid_in, output ready_out, output reg valid_out, input ready_in);
    {logic}
endmodule
"""
    axi_tb = """
module tb;
    reg clk, rst_n, valid_in, ready_in; wire ready_out, valid_out;
    axi_like dut(.*);
    initial begin
        $dumpfile("VCD_PATH"); $dumpvars(0, tb); clk=0; rst_n=0; valid_in=0; ready_in=0;
        #10 rst_n=1; valid_in=1; ready_in=1; #10 if(!valid_out) $display("FAIL: Timeout"); #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""
    def write_axi(name, bg_cls, logic, symp, gs):
        bugs_metadata.append({"bug_id": name, "family": "axi", "bug_class": bg_cls, "symptom": symp, "ground_truth_module": "axi_like", "ground_truth_signals": gs})
        with open(os.path.join(designs_dir, f"{name}.v"), "w") as f: f.write(axi_base.format(logic=logic))
        with open(os.path.join(tb_dir, f"{name}_tb.v"), "w") as f: f.write(axi_tb.replace("VCD_PATH", f"{base_dir}/rtl/{name}.vcd"))
        
    write_axi("axi_b1", "handshake_loss", "assign ready_out=1; always @(posedge clk) valid_out <= valid_in & ~ready_in;", "Timeout", ["valid_out"])
    write_axi("axi_b2", "incorrect_backpressure", "assign ready_out=0; always @(posedge clk) valid_out <= valid_in;", "Timeout", ["ready_out"])
    write_axi("axi_b3", "early_ready", "assign ready_out=1; always @(posedge clk) valid_out <= valid_in & ready_in;", "Timeout", ["valid_out"])
    write_axi("axi_b4", "dropped_tx", "assign ready_out=ready_in; always @(posedge clk) valid_out <= 0;", "Timeout", ["valid_out"])
    write_axi("axi_b5", "stuck_ready", "assign ready_out=1; always @(posedge clk) valid_out <= 0;", "Timeout", ["valid_out"])
    write_axi("axi_b6", "adv_valid_in_drop", "assign ready_out=1; always @(posedge clk) valid_out <= valid_in & 0;", "Timeout", ["valid_in"]) # Adversarial: usually valid_in is given, but we drop it internally simulating a downstream drop

# FSM
    fsm_base = """
module fsm(input clk, input rst_n, input start, output reg done);
    reg [1:0] state;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) {rst} else begin {trans} end
    end
endmodule
"""
    fsm_tb = """
module tb;
    reg clk, rst_n, start; wire done;
    fsm dut(.*);
    initial begin
        $dumpfile("VCD_PATH"); $dumpvars(0, tb); clk=0; rst_n=0; start=0;
        #10 rst_n=1; start=1; #30 if(!done) $display("FAIL: Stuck State"); #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""
    def write_fsm(name, bg_cls, rst, trans, symp, gs):
        bugs_metadata.append({"bug_id": name, "family": "fsm", "bug_class": bg_cls, "symptom": symp, "ground_truth_module": "fsm", "ground_truth_signals": gs})
        with open(os.path.join(designs_dir, f"{name}.v"), "w") as f: f.write(fsm_base.format(rst=rst, trans=trans))
        with open(os.path.join(tb_dir, f"{name}_tb.v"), "w") as f: f.write(fsm_tb.replace("VCD_PATH", f"{base_dir}/rtl/{name}.vcd"))
        
    write_fsm("fsm_b1", "incorrect_trans", "state<=0;done<=0;", "case(state) 0: if(start) state<=2; 1: state<=2; 2: begin state<=0; done<=1; end endcase", "Stuck State", ["state"])
    write_fsm("fsm_b2", "missing_trans", "state<=0;done<=0;", "case(state) 0: if(start) state<=0; 1: state<=2; 2: begin state<=0; done<=1; end endcase", "Stuck State", ["state"])
    write_fsm("fsm_b3", "stuck_state", "state<=0;done<=0;", "case(state) 0: if(start) state<=1; 1: state<=1; 2: begin state<=0; done<=1; end endcase", "Stuck State", ["state"])
    write_fsm("fsm_b4", "reset_bug", "state<=1;done<=0;", "case(state) 0: if(start) state<=1; 1: state<=2; 2: begin state<=0; done<=1; end endcase", "Stuck State", ["state"])
    write_fsm("fsm_b5", "done_glitch", "state<=0;done<=0;", "case(state) 0: if(start) state<=1; 1: state<=2; 2: begin state<=0; done<=0; end endcase", "Stuck State", ["done"])
    write_fsm("fsm_b6", "start_ignored", "state<=0;done<=0;", "case(state) 0: if(!start) state<=1; 1: state<=2; 2: begin state<=0; done<=1; end endcase", "Stuck State", ["start"]) # Adv

    # Pipeline
    pipe_base = """
module pipeline(input clk, input rst_n, input valid_in, input [7:0] d_in, output reg valid_out, output reg [7:0] d_out);
    reg v1; reg [7:0] d1;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin {rst} end else begin {trans} end
    end
endmodule
"""
    pipe_tb = """
module tb;
    reg clk, rst_n, valid_in; reg [7:0] d_in; wire valid_out; wire [7:0] d_out;
    pipeline dut(.*);
    initial begin
        $dumpfile("VCD_PATH"); $dumpvars(0, tb); clk=0; rst_n=0; valid_in=0; d_in=0;
        #10 rst_n=1; valid_in=1; d_in=8'hFF; #10 valid_in=0; #30 if(d_out!==8'hFF) $display("FAIL: Data Loss"); #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""
    def write_pipe(name, bg_cls, rst, trans, symp, gs):
        bugs_metadata.append({"bug_id": name, "family": "pipeline", "bug_class": bg_cls, "symptom": symp, "ground_truth_module": "pipeline", "ground_truth_signals": gs})
        with open(os.path.join(designs_dir, f"{name}.v"), "w") as f: f.write(pipe_base.format(rst=rst, trans=trans))
        with open(os.path.join(tb_dir, f"{name}_tb.v"), "w") as f: f.write(pipe_tb.replace("VCD_PATH", f"{base_dir}/rtl/{name}.vcd"))
        
    write_pipe("pipe_b1", "misalignment", "v1<=0; valid_out<=0;", "v1<=valid_in; d1<=d_in; valid_out<=v1; d_out<=d_in;", "Data Loss", ["valid_out"])
    write_pipe("pipe_b2", "stall_prop", "v1<=0; valid_out<=0;", "v1<=0; d1<=d_in; valid_out<=v1; d_out<=d1;", "Data Loss", ["v1"])
    write_pipe("pipe_b3", "control_delay", "v1<=0; valid_out<=0;", "v1<=valid_in; d1<=d_in; valid_out<=valid_in; d_out<=d1;", "Data Loss", ["valid_out"])
    write_pipe("pipe_b4", "flush_bug", "v1<=1; valid_out<=1;", "v1<=valid_in; d1<=d_in; valid_out<=v1; d_out<=d1;", "Data Loss", ["v1"])
    write_pipe("pipe_b5", "data_corrupt", "v1<=0; valid_out<=0;", "v1<=valid_in; d1<=d_in; valid_out<=v1; d_out<=0;", "Data Loss", ["d_out"])
    write_pipe("pipe_b6", "d_in_corrupt", "v1<=0; valid_out<=0;", "v1<=valid_in; d1<=0; valid_out<=v1; d_out<=d1;", "Data Loss", ["d_in"])

# Uart
    uart_base = """
module uart(input clk, input rst_n, input start, output reg tx);
    reg [2:0] cnt;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin {rst} end else begin {trans} end
    end
endmodule
"""
    uart_tb = """
module tb;
    reg clk, rst_n, start; wire tx;
    uart dut(.*);
    initial begin
        $dumpfile("VCD_PATH"); $dumpvars(0, tb); clk=0; rst_n=0; start=0;
        #10 rst_n=1; start=1; #100 if(tx!==1) $display("FAIL: Bad Output"); #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""
    def write_uart(name, bg_cls, rst, trans, symp, gs):
        bugs_metadata.append({"bug_id": name, "family": "uart", "bug_class": bg_cls, "symptom": symp, "ground_truth_module": "uart", "ground_truth_signals": gs})
        with open(os.path.join(designs_dir, f"{name}.v"), "w") as f: f.write(uart_base.format(rst=rst, trans=trans))
        with open(os.path.join(tb_dir, f"{name}_tb.v"), "w") as f: f.write(uart_tb.replace("VCD_PATH", f"{base_dir}/rtl/{name}.vcd"))
        
    write_uart("uart_b1", "off_by_one", "cnt<=0; tx<=1;", "if(start) cnt<=cnt+2; if(cnt==7) tx<=~tx;", "Bad Output", ["cnt"])
    write_uart("uart_b2", "state_trans", "cnt<=0; tx<=1;", "if(start) cnt<=0; if(cnt==7) tx<=~tx;", "Bad Output", ["cnt"])
    write_uart("uart_b3", "timing", "cnt<=0; tx<=1;", "if(start) cnt<=cnt+1; if(cnt==8) tx<=0;", "Bad Output", ["cnt"])
    write_uart("uart_b4", "output_timing", "cnt<=0; tx<=1;", "if(start) cnt<=cnt+1; tx<=0;", "Bad Output", ["tx"])
    write_uart("uart_b5", "stuck_tx", "cnt<=0; tx<=1;", "if(start) cnt<=cnt+1; tx<=1;", "Bad Output", ["tx"])
    write_uart("uart_b6", "start_edge", "cnt<=0; tx<=1;", "if(!start) cnt<=cnt+1; if(cnt==7) tx<=~tx;", "Bad Output", ["start"])

    with open(os.path.join(meta_dir, "bugs.json"), "w") as f:
        json.dump(bugs_metadata, f, indent=2)

if __name__ == "__main__":
    generate_benchmark(".")
