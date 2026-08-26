import os
import json

def generate_reuse_poc_benchmark(base_dir: str):
    designs_dir = os.path.join(base_dir, "rtl", "designs")
    tb_dir = os.path.join(base_dir, "rtl", "testbenches")
    poc_dir = os.path.join(base_dir, "results", "causal_reuse_poc")
    
    os.makedirs(designs_dir, exist_ok=True)
    os.makedirs(tb_dir, exist_ok=True)
    os.makedirs(poc_dir, exist_ok=True)
    
    # Normalized path with forward slashes for Verilog $dumpfile
    norm_base = base_dir.replace("\\", "/")
    
# Rtl designs
    
    # Defect X (F1, F2, F3): Missing simultaneous R/W counter hold logic
    rtl_defect_x = """
module fifo(
    input clk,
    input rst_n,
    input write_en,
    input [7:0] write_data,
    input read_en,
    output reg [7:0] read_data,
    output full,
    output empty
);
    reg [7:0] mem [0:15];
    reg [4:0] write_ptr;
    reg [4:0] read_ptr;
    reg [5:0] count;

    assign full = (count == 16);
    assign empty = (count == 0);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            write_ptr <= 0;
            read_ptr <= 0;
            count <= 0;
        end else begin
            if (write_en && !full) begin
                mem[write_ptr] <= write_data;
                write_ptr <= (write_ptr + 1) % 16;
            end
            if (read_en && !empty) begin
                read_data <= mem[read_ptr];
                read_ptr <= (read_ptr + 1) % 16;
            end
            // DEFECT X: Missing simultaneous RW handling (increments on simultaneous RW)
            if (write_en && !full)
                count <= count + 1;
            else if (read_en && !empty)
                count <= count - 1;
        end
    end
endmodule
"""

    # Defect Y (F4 - Hard Negative): Early Empty Threshold Bug (empty = count <= 1)
    rtl_defect_y = """
module fifo(
    input clk,
    input rst_n,
    input write_en,
    input [7:0] write_data,
    input read_en,
    output reg [7:0] read_data,
    output full,
    output empty
);
    reg [7:0] mem [0:15];
    reg [4:0] write_ptr;
    reg [4:0] read_ptr;
    reg [5:0] count;

    assign full = (count == 16);
    // DEFECT Y: Off-by-one early empty threshold (count <= 1)
    assign empty = (count <= 1);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            write_ptr <= 0;
            read_ptr <= 0;
            count <= 0;
        end else begin
            if (write_en && !full) begin
                mem[write_ptr] <= write_data;
                write_ptr <= (write_ptr + 1) % 16;
            end
            if (read_en && !empty) begin
                read_data <= mem[read_ptr];
                read_ptr <= (read_ptr + 1) % 16;
            end
            // Simultaneous RW is handled correctly in Defect Y
            if (write_en && !full && read_en && !empty)
                count <= count;
            else if (write_en && !full)
                count <= count + 1;
            else if (read_en && !empty)
                count <= count - 1;
        end
    end
endmodule
"""

    with open(os.path.join(designs_dir, "fifo_f1.v"), "w", encoding="utf-8") as f:
        f.write(rtl_defect_x)
    with open(os.path.join(designs_dir, "fifo_f2.v"), "w", encoding="utf-8") as f:
        f.write(rtl_defect_x)
    with open(os.path.join(designs_dir, "fifo_f3.v"), "w", encoding="utf-8") as f:
        f.write(rtl_defect_x)
    with open(os.path.join(designs_dir, "fifo_f4.v"), "w", encoding="utf-8") as f:
        f.write(rtl_defect_y)

# Testbenches

    # F1: Premature Full Flag / Capacity Mismatch
    tb_f1 = f"""
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data;
    wire [7:0] read_data;
    wire full, empty;

    fifo dut(.*);

    initial begin
        $dumpfile("fifo_f1.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 0;
        #10 rst_n = 1;

        // Write 8 initial items
        repeat(8) begin
            #10 write_en = 1; write_data = write_data + 1;
        end
        #10 write_en = 0;

        // Simultaneous write & read for 8 cycles
        repeat(8) begin
            #10 write_en = 1; read_en = 1; write_data = write_data + 1;
        end
        #10 write_en = 0; read_en = 0;

        // Attempt next write: should have space, but full is falsely high
        #10 write_en = 1; write_data = 8'hEE;
        # 10;
        if (full) begin
            $display("FAIL: Premature Full Flag / Capacity Mismatch");
        end
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""

    # F2: Read Stalled / Data Underflow
    tb_f2 = f"""
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data;
    wire [7:0] read_data;
    wire full, empty;

    fifo dut(.*);

    initial begin
        $dumpfile("fifo_f2.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 8'h10;
        #10 rst_n = 1;

        // Initial 2 items
        #10 write_en = 1; write_data = 8'hA1;
        #10 write_en = 1; write_data = 8'hA2;
        #10 write_en = 0;

        // Simultaneous RW burst for 4 cycles
        repeat(4) begin
            #10 write_en = 1; read_en = 1; write_data = write_data + 1;
        end
        #10 write_en = 0; read_en = 0;

        // Drain the FIFO: 2 valid remaining items
        #10 read_en = 1;
        #10 read_en = 1;
        #10 read_en = 0;
        # 10;
        // Verify count and pointer alignment: count should be 0, but due to Defect X count is 4!
        if (dut.count !== 0 || dut.read_ptr !== dut.write_ptr) begin
            $display("FAIL: Read Stalled / Data Underflow");
        end
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""

    # F3: Memory Overwrite / Checksum Mismatch
    tb_f3 = f"""
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data;
    wire [7:0] read_data;
    wire full, empty;

    fifo dut(.*);

    initial begin
        $dumpfile("fifo_f3.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 8'h50;
        #10 rst_n = 1;

        // Fill partially
        repeat(4) begin
            #10 write_en = 1; write_data = write_data + 1;
        end
        #10 write_en = 0;

        // 12 Simultaneous push-pop cycles
        repeat(12) begin
            #10 write_en = 1; read_en = 1; write_data = write_data + 1;
        end
        #10 write_en = 0; read_en = 0;

        // Read out next data item and verify it was not overwritten
        #10 read_en = 1;
        #10 read_en = 0;
        # 10;
        if (read_data !== 8'h51) begin
            $display("FAIL: Memory Overwrite / Checksum Mismatch");
        end
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""

    # F4: Defect Y (Early Empty Threshold) -> Symptom B: "FAIL: Read Stalled / Data Underflow"
    tb_f4 = f"""
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data;
    wire [7:0] read_data;
    wire full, empty;

    fifo dut(.*);

    initial begin
        $dumpfile("fifo_f4.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 8'h20;
        #10 rst_n = 1;

        // Write 1 item into empty FIFO
        #10 write_en = 1; write_data = 8'hBB;
        #10 write_en = 0;

        // Attempt to read that 1 item back.
        // Due to Defect Y (empty = count <= 1), empty is TRUE even though 1 item is present!
        #10 read_en = 1;
        #10 read_en = 0;
        # 10;
        if (empty) begin
            $display("FAIL: Read Stalled / Data Underflow");
        end
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""

    with open(os.path.join(tb_dir, "fifo_f1_tb.v"), "w", encoding="utf-8") as f:
        f.write(tb_f1)
    with open(os.path.join(tb_dir, "fifo_f2_tb.v"), "w", encoding="utf-8") as f:
        f.write(tb_f2)
    with open(os.path.join(tb_dir, "fifo_f3_tb.v"), "w", encoding="utf-8") as f:
        f.write(tb_f3)
    with open(os.path.join(tb_dir, "fifo_f4_tb.v"), "w", encoding="utf-8") as f:
        f.write(tb_f4)

# Ground truth metadata
    ground_truth = [
        {
            "failure_id": "fifo_f1",
            "design": "fifo",
            "injected_defect": "Defect X: Missing simultaneous R/W counter hold logic",
            "root_location": "fifo.count",
            "mechanism": "Simultaneous write_en & read_en increments count instead of maintaining net occupancy",
            "trigger_condition": "write_en == 1 && read_en == 1 && !full && !empty",
            "propagation_path": "simultaneous_rw -> count_overincrement -> premature_full_asserted -> write_blocked",
            "observed_symptom": "FAIL: Premature Full Flag / Capacity Mismatch",
            "causal_family": "Defect_X_Simultaneous_RW_Count_Corruption"
        },
        {
            "failure_id": "fifo_f2",
            "design": "fifo",
            "injected_defect": "Defect X: Missing simultaneous R/W counter hold logic",
            "root_location": "fifo.count",
            "mechanism": "Simultaneous write_en & read_en increments count instead of maintaining net occupancy",
            "trigger_condition": "write_en == 1 && read_en == 1 && !full && !empty",
            "propagation_path": "simultaneous_rw -> count_overincrement -> count_pointer_desync -> empty_flag_desync -> read_stalled",
            "observed_symptom": "FAIL: Read Stalled / Data Underflow",
            "causal_family": "Defect_X_Simultaneous_RW_Count_Corruption"
        },
        {
            "failure_id": "fifo_f3",
            "design": "fifo",
            "injected_defect": "Defect X: Missing simultaneous R/W counter hold logic",
            "root_location": "fifo.count",
            "mechanism": "Simultaneous write_en & read_en increments count instead of maintaining net occupancy",
            "trigger_condition": "write_en == 1 && read_en == 1 && !full && !empty",
            "propagation_path": "simultaneous_rw -> count_overincrement -> write_ptr_past_unread_data -> memory_array_overwrite",
            "observed_symptom": "FAIL: Memory Overwrite / Checksum Mismatch",
            "causal_family": "Defect_X_Simultaneous_RW_Count_Corruption"
        },
        {
            "failure_id": "fifo_f4",
            "design": "fifo",
            "injected_defect": "Defect Y: Off-by-one early empty threshold (count <= 1)",
            "root_location": "fifo.empty",
            "mechanism": "Empty flag threshold evaluates true when count is 1, blocking single-item reads",
            "trigger_condition": "count == 1 && read_en == 1",
            "propagation_path": "count_equals_one -> empty_falsely_asserted -> read_en_ignored -> read_stalled",
            "observed_symptom": "FAIL: Read Stalled / Data Underflow",
            "causal_family": "Defect_Y_Early_Empty_Flag_Threshold"
        }
    ]

    gt_path = os.path.join(poc_dir, "ground_truth.json")
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)
        
    print(f"Generated 4-Failure Proof-of-Concept benchmark with clean normalized paths.")
    print(f"Saved ground truth to {gt_path}")

if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generate_reuse_poc_benchmark(base)
