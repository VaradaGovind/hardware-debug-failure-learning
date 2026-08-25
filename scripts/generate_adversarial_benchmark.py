import os
import json

def generate_adversarial_benchmark(base_dir: str):
    designs_dir = os.path.join(base_dir, "rtl", "designs")
    tb_dir = os.path.join(base_dir, "rtl", "testbenches")
    audit_dir = os.path.join(base_dir, "results", "causal_reuse_poc", "adversarial_audit")
    
    os.makedirs(designs_dir, exist_ok=True)
    os.makedirs(tb_dir, exist_ok=True)
    os.makedirs(audit_dir, exist_ok=True)
    
    norm_base = base_dir.replace("\\", "/")
    
# Rtl designs
    
    # Defect X (F1, F2, F3, F6): Missing simultaneous R/W counter hold logic
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

    # Defect Y (F4): Early Empty Threshold Bug (empty = count <= 1)
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

    # Defect Z (F5 - Primary Hard Negative): Same Simultaneous R/W Trigger, but Read Pointer Skip
    # Count is properly preserved during simultaneous R/W, but read_ptr skips by 2 when reading
    rtl_defect_z = """
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
                // DEFECT Z: Read pointer skips by 2 instead of 1 on read
                read_ptr <= (read_ptr + 2) % 16;
            end
            // Simultaneous RW is handled correctly in Defect Z (count is preserved!)
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

    # Defect W (F7 - Propagation-Only Hard Negative):
    # Simultaneous RW occurs AND count overincrements by 1 on cycle 2,
    # BUT on cycle 3 an internal correction clamps count back, and the actual testbench failure
    # is caused by a completely unrelated static output driver fault (read_data stuck at 0 on high address).
    rtl_defect_w = """
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
    reg transient_glitch;

    assign full = (count == 16);
    assign empty = (count == 0);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            write_ptr <= 0;
            read_ptr <= 0;
            count <= 0;
            transient_glitch <= 1;
        end else begin
            if (write_en && !full) begin
                mem[write_ptr] <= write_data;
                write_ptr <= (write_ptr + 1) % 16;
            end
            if (read_en && !empty) begin
                // DEFECT W: Static output corruption on specific read address (unrelated to RW count)
                if (read_ptr == 2)
                    read_data <= 8'h00;
                else
                    read_data <= mem[read_ptr];
                read_ptr <= (read_ptr + 1) % 16;
            end
            // Transient 1-step count anomaly on first simultaneous RW, then corrected
            if (write_en && !full && read_en && !empty) begin
                if (transient_glitch) begin
                    count <= count + 1; // 1-step anomaly occurs
                    transient_glitch <= 0;
                end else begin
                    count <= count; // then properly maintained
                end
            end else if (write_en && !full) begin
                count <= count + 1;
            end else if (read_en && !empty) begin
                count <= count - 1;
            end
            // Self-correct count to pointer distance after 2 cycles, so no propagation occurs
            if (!transient_glitch && count != ((write_ptr - read_ptr) % 16)) begin
                count <= (write_ptr - read_ptr) % 16;
            end
        end
    end
endmodule
"""

    with open(os.path.join(designs_dir, "fifo_f1.v"), "w", encoding="utf-8") as f: f.write(rtl_defect_x)
    with open(os.path.join(designs_dir, "fifo_f2.v"), "w", encoding="utf-8") as f: f.write(rtl_defect_x)
    with open(os.path.join(designs_dir, "fifo_f3.v"), "w", encoding="utf-8") as f: f.write(rtl_defect_x)
    with open(os.path.join(designs_dir, "fifo_f4.v"), "w", encoding="utf-8") as f: f.write(rtl_defect_y)
    with open(os.path.join(designs_dir, "fifo_f5.v"), "w", encoding="utf-8") as f: f.write(rtl_defect_z)
    with open(os.path.join(designs_dir, "fifo_f6.v"), "w", encoding="utf-8") as f: f.write(rtl_defect_x)
    with open(os.path.join(designs_dir, "fifo_f7.v"), "w", encoding="utf-8") as f: f.write(rtl_defect_w)

# Testbenches

    # F5 Testbench: Exercises Simultaneous R/W Trigger, manifests Symptom B (Read Stalled / Data Underflow)
    tb_f5 = f"""
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data;
    wire [7:0] read_data;
    wire full, empty;

    fifo dut(.*);

    initial begin
        $dumpfile("{norm_base}/rtl/fifo_f5.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 8'h10;
        #10 rst_n = 1;

        // Initial 2 writes
        #10 write_en = 1; write_data = 8'hA1;
        #10 write_en = 1; write_data = 8'hA2;
        #10 write_en = 0;

        // Simultaneous RW burst for 4 cycles (EXERCISES THE TRIGGER!)
        repeat(4) begin
            #10 write_en = 1; read_en = 1; write_data = write_data + 1;
        end
        #10 write_en = 0; read_en = 0;

        // Drain the FIFO: Attempt to read remaining items
        // In Defect Z, read_ptr skipped by 2 on each read, so read_ptr desynchronized and stalled
        #10 read_en = 1;
        #10 read_en = 1;
        #10 read_en = 0;
        # 10;
        if (dut.read_ptr !== 12 || dut.count !== 2) begin
            $display("FAIL: Read Stalled / Data Underflow");
        end
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""

    # F6 Testbench: Defect X with Low Initial Occupancy & Interleaved Trigger Pattern
    tb_f6 = f"""
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data;
    wire [7:0] read_data;
    wire full, empty;

    fifo dut(.*);

    initial begin
        $dumpfile("{norm_base}/rtl/fifo_f6.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 8'h40;
        #50 rst_n = 1; // 50ns startup delay

        // Single write (occupancy = 1)
        #10 write_en = 1; write_data = 8'hC1;
        #10 write_en = 0;

        // 3 interleaved simultaneous RW cycles
        #10 write_en = 1; read_en = 1; write_data = 8'hC2;
        #10 write_en = 0; read_en = 0;
        #20 write_en = 1; read_en = 1; write_data = 8'hC3;
        #10 write_en = 0; read_en = 0;
        #20 write_en = 1; read_en = 1; write_data = 8'hC4;
        #10 write_en = 0; read_en = 0;

        // Check occupancy: count should be 1, but in Defect X count is 4!
        # 10;
        if (dut.count !== 1) begin
            $display("FAIL: Occupancy Desynchronization / Flag Glitch");
        end
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""

    # F7 Testbench: Propagation-Only Negative (Trigger occurs, 1-step count bump occurs, but self-corrects and failure is output short)
    tb_f7 = f"""
module tb;
    reg clk, rst_n, write_en, read_en;
    reg [7:0] write_data;
    wire [7:0] read_data;
    wire full, empty;

    fifo dut(.*);

    initial begin
        $dumpfile("{norm_base}/rtl/fifo_f7.vcd");
        $dumpvars(0, tb);
        clk = 0; rst_n = 0; write_en = 0; read_en = 0; write_data = 8'h70;
        #10 rst_n = 1;

        // Initial 2 items
        #10 write_en = 1; write_data = 8'h81;
        #10 write_en = 1; write_data = 8'h82;
        #10 write_en = 0;

        // Simultaneous RW cycle (Trigger occurs, 1-step anomaly occurs!)
        #10 write_en = 1; read_en = 1; write_data = 8'h83;
        #10 write_en = 0; read_en = 0;

        // Read items
        #10 read_en = 1;
        #10 read_en = 1;
        #10 read_en = 0;
        # 10;
        // The failure symptom is due to read_data corrupted at read_ptr == 2, NOT count propagation
        if (read_data !== 8'h83) begin
            $display("FAIL: Data Corruption / Unrelated Bus Fault");
        end
        #10 $finish;
    end
    always #5 clk = ~clk;
endmodule
"""

    with open(os.path.join(tb_dir, "fifo_f5_tb.v"), "w", encoding="utf-8") as f: f.write(tb_f5)
    with open(os.path.join(tb_dir, "fifo_f6_tb.v"), "w", encoding="utf-8") as f: f.write(tb_f6)
    with open(os.path.join(tb_dir, "fifo_f7_tb.v"), "w", encoding="utf-8") as f: f.write(tb_f7)

# Ground truth metadata
    gt_adversarial = [
        {
            "failure_id": "fifo_f1",
            "defect_id": "Defect_X",
            "mechanism": "Simultaneous write_en & read_en increments count instead of maintaining occupancy",
            "trigger_condition": "write_en == 1 && read_en == 1 && !full && !empty",
            "has_trigger": True,
            "has_count_anomaly": True,
            "has_causal_propagation": True,
            "observed_symptom": "FAIL: Premature Full Flag / Capacity Mismatch",
            "causal_family": "Defect_X_Simultaneous_RW"
        },
        {
            "failure_id": "fifo_f2",
            "defect_id": "Defect_X",
            "mechanism": "Simultaneous write_en & read_en increments count instead of maintaining occupancy",
            "trigger_condition": "write_en == 1 && read_en == 1 && !full && !empty",
            "has_trigger": True,
            "has_count_anomaly": True,
            "has_causal_propagation": True,
            "observed_symptom": "FAIL: Read Stalled / Data Underflow",
            "causal_family": "Defect_X_Simultaneous_RW"
        },
        {
            "failure_id": "fifo_f3",
            "defect_id": "Defect_X",
            "mechanism": "Simultaneous write_en & read_en increments count instead of maintaining occupancy",
            "trigger_condition": "write_en == 1 && read_en == 1 && !full && !empty",
            "has_trigger": True,
            "has_count_anomaly": True,
            "has_causal_propagation": True,
            "observed_symptom": "FAIL: Memory Overwrite / Checksum Mismatch",
            "causal_family": "Defect_X_Simultaneous_RW"
        },
        {
            "failure_id": "fifo_f4",
            "defect_id": "Defect_Y",
            "mechanism": "Early empty flag threshold (count <= 1)",
            "trigger_condition": "count == 1 && read_en == 1",
            "has_trigger": False,
            "has_count_anomaly": False,
            "has_causal_propagation": False,
            "observed_symptom": "FAIL: Read Stalled / Data Underflow",
            "causal_family": "Defect_Y_Early_Empty_Threshold"
        },
        {
            "failure_id": "fifo_f5",
            "defect_id": "Defect_Z",
            "mechanism": "Read pointer skips by 2 on read; count is properly held during simultaneous R/W",
            "trigger_condition": "write_en == 1 && read_en == 1 && !full && !empty",
            "has_trigger": True,
            "has_count_anomaly": False,
            "has_causal_propagation": False,
            "observed_symptom": "FAIL: Read Stalled / Data Underflow",
            "causal_family": "Defect_Z_Read_Pointer_Skip"
        },
        {
            "failure_id": "fifo_f6",
            "defect_id": "Defect_X",
            "mechanism": "Simultaneous write_en & read_en increments count instead of maintaining occupancy (Interleaved Pattern)",
            "trigger_condition": "write_en == 1 && read_en == 1 && !full && !empty",
            "has_trigger": True,
            "has_count_anomaly": True,
            "has_causal_propagation": True,
            "observed_symptom": "FAIL: Occupancy Desynchronization / Flag Glitch",
            "causal_family": "Defect_X_Simultaneous_RW"
        },
        {
            "failure_id": "fifo_f7",
            "defect_id": "Defect_W",
            "mechanism": "Transient non-propagating count bump + unrelated memory read data bus fault",
            "trigger_condition": "write_en == 1 && read_en == 1 && !full && !empty",
            "has_trigger": True,
            "has_count_anomaly": True,
            "has_causal_propagation": False,
            "observed_symptom": "FAIL: Data Corruption / Unrelated Bus Fault",
            "causal_family": "Defect_W_Unrelated_Bus_Fault"
        }
    ]

    gt_file = os.path.join(audit_dir, "adversarial_ground_truth.json")
    with open(gt_file, "w", encoding="utf-8") as f:
        json.dump(gt_adversarial, f, indent=2)
        
    print(f"Generated extended adversarial benchmark (F1 - F7) with ground truth saved to {gt_file}")

if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generate_adversarial_benchmark(base)
