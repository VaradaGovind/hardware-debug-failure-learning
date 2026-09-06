"""
scripts/build_v11_benchmark.py

Generates the canonical 100-case manifest for Experiment V11:
Benchmark Expansion & Generalization Evaluation.

Spans 5 hardware families (FIFO, AXI, FSM, UART, Pipeline) across 3 categories:
- Category A: In-Family Generalization (40 cases; 8 per family)
- Category B: Structural Generalization (30 cases; 6 per family)
- Category C: Negative and Safety Stress Tests (30 cases; 6 per family)
  (15 Adversarial Negatives + 15 Incomplete Trace Negatives)

Total: 100 independent benchmark cases.
"""

import os
import sys
import json

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORTS_DIR = os.path.join(WORKSPACE_ROOT, "results", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

FAMILIES = ["fifo", "axi", "fsm", "uart", "pipeline"]

# ------------------------------------------------------------------------------
# Category A: In-Family Generalization (8 per family = 40 cases)
# Varies: Signal names, parameter widths, surrounding wrappers, clock offsets
# ------------------------------------------------------------------------------
CAT_A_TEMPLATES = {
    "fifo": [
        ("v11_fifo_ren_occupancy", "occupancy", ["occupancy", "wr_en", "rd_en", "is_full", "is_empty"], "FIFO_SIMULTANEOUS_RW", "Renamed count to occupancy; 16-bit depth"),
        ("v11_fifo_ren_level", "fifo_level", ["fifo_level", "push", "pop", "full_flag", "empty_flag"], "FIFO_SIMULTANEOUS_RW", "Renamed signals to push/pop and fifo_level"),
        ("v11_fifo_ren_depthcnt", "depth_cnt", ["depth_cnt", "wr_req", "rd_req", "fifo_full", "fifo_empty"], "FIFO_SIMULTANEOUS_RW", "Renamed request lines and depth_cnt"),
        ("v11_fifo_ren_items", "items_in_flight", ["items_in_flight", "put", "get", "q_full", "q_empty"], "FIFO_SIMULTANEOUS_RW", "Queue terminology put/get/items_in_flight"),
        ("v11_fifo_ren_buflvl", "buf_lvl", ["buf_lvl", "write_strobe", "read_strobe", "full_out", "empty_out"], "FIFO_SIMULTANEOUS_RW", "Strobe-based interface with buf_lvl"),
        ("v11_fifo_ren_fillcnt", "fill_count", ["fill_count", "in_push", "out_pop", "full_status", "empty_status"], "FIFO_SIMULTANEOUS_RW", "Status flags with fill_count"),
        ("v11_fifo_ren_entrynum", "entry_num", ["entry_num", "valid_in", "ready_out", "overflow", "underflow"], "FIFO_SIMULTANEOUS_RW", "Streaming wrapper around FIFO count"),
        ("v11_fifo_ren_qdepth", "q_depth", ["q_depth", "w_en", "r_en", "buf_full", "buf_empty"], "FIFO_SIMULTANEOUS_RW", "Abbreviated control signals with q_depth")
    ],
    "axi": [
        ("v11_axi_ren_rxvld", "rx_vld", ["rx_vld", "rx_rdy", "rx_data", "rx_done"], "AXI_HANDSHAKE_LOCK", "Renamed valid/ready to rx_vld/rx_rdy"),
        ("v11_axi_ren_saxis", "s_axis_tvalid", ["s_axis_tvalid", "s_axis_tready", "s_axis_tdata", "s_axis_tlast"], "AXI_HANDSHAKE_LOCK", "AXI4-Stream formal port naming conventions"),
        ("v11_axi_ren_mrdy", "m_rdy", ["m_vld", "m_rdy", "m_payload", "m_strobe"], "AXI_HANDSHAKE_LOCK", "Master channel terminology m_vld/m_rdy"),
        ("v11_axi_ren_chvalid", "ch_valid", ["ch_valid", "ch_ready", "ch_data", "ch_ack"], "AXI_HANDSHAKE_LOCK", "Channel interconnect prefix naming ch_valid"),
        ("v11_axi_ren_stream", "stream_vld", ["stream_vld", "stream_rdy", "stream_data", "stream_keep"], "AXI_HANDSHAKE_LOCK", "Streaming bus prefix stream_vld"),
        ("v11_axi_ren_txvld", "tx_vld", ["tx_vld", "tx_rdy", "tx_data", "tx_active"], "AXI_HANDSHAKE_LOCK", "Transmitter interface tx_vld/tx_rdy"),
        ("v11_axi_ren_datavld", "data_vld", ["data_vld", "data_rdy", "data_bits", "data_last"], "AXI_HANDSHAKE_LOCK", "Data-centric bus naming data_vld"),
        ("v11_axi_ren_axvld", "ax_valid", ["ax_valid", "ax_ready", "ax_addr", "ax_prot"], "AXI_HANDSHAKE_LOCK", "Address read/write handshake naming ax_valid")
    ],
    "fsm": [
        ("v11_fsm_ren_fsmst", "fsm_st", ["fsm_st", "nxt_st", "token_in", "detect_out"], "FSM_STATE_TRANSITION", "Renamed state register to fsm_st"),
        ("v11_fsm_ren_currst", "curr_state", ["curr_state", "next_state", "in_bit", "seq_found"], "FSM_STATE_TRANSITION", "Canonical curr_state/next_state nomenclature"),
        ("v11_fsm_ren_streg", "st_reg", ["st_reg", "st_nxt", "din", "match_flag"], "FSM_STATE_TRANSITION", "Abbreviated st_reg/st_nxt naming"),
        ("v11_fsm_ren_seqstate", "seq_state", ["seq_state", "seq_next", "symbol_in", "pulse_out"], "FSM_STATE_TRANSITION", "Symbol sequencer naming seq_state"),
        ("v11_fsm_ren_detstate", "detector_state", ["detector_state", "next_det", "sample_in", "valid_flag"], "FSM_STATE_TRANSITION", "Detector nomenclature detector_state"),
        ("v11_fsm_ren_arbstate", "arb_state", ["arb_state", "arb_next", "req_vec", "grant_vec"], "FSM_STATE_TRANSITION", "Arbiter state machine transition naming"),
        ("v11_fsm_ren_ctrlstate", "ctrl_state", ["ctrl_state", "ctrl_next", "cmd_in", "exec_out"], "FSM_STATE_TRANSITION", "Command controller naming ctrl_state"),
        ("v11_fsm_ren_machst", "mach_st", ["mach_st", "mach_nxt", "step_en", "status_led"], "FSM_STATE_TRANSITION", "Step machine naming mach_st")
    ],
    "uart": [
        ("v11_uart_ren_bauddiv", "baud_div", ["baud_div", "clk_en", "tx_bit", "busy_reg"], "UART_BAUD_ACCUM", "Renamed baud counter to baud_div"),
        ("v11_uart_ren_accum", "accum", ["accum", "step_tick", "tx_pin", "active_flag"], "UART_BAUD_ACCUM", "Phase accumulator naming accum"),
        ("v11_uart_ren_tickcnt", "tick_cnt", ["tick_cnt", "baud_pulse", "ser_out", "tx_busy"], "UART_BAUD_ACCUM", "Tick counter terminology tick_cnt"),
        ("v11_uart_ren_clkdiv", "clk_div", ["clk_div", "sample_edge", "sdo", "sending"], "UART_BAUD_ACCUM", "Clock divider naming clk_div"),
        ("v11_uart_ren_samplecnt", "sample_cnt", ["sample_cnt", "oversample_tick", "txd", "tx_ready"], "UART_BAUD_ACCUM", "Oversampling counter naming sample_cnt"),
        ("v11_uart_ren_subctr", "sub_counter", ["sub_counter", "bit_strobe", "tx_wire", "hold_state"], "UART_BAUD_ACCUM", "Sub-counter terminology sub_counter"),
        ("v11_uart_ren_rollover", "rollover_cnt", ["rollover_cnt", "rollover_pulse", "data_pin", "line_idle"], "UART_BAUD_ACCUM", "Rollover counter naming rollover_cnt"),
        ("v11_uart_ren_baudctr", "baud_ctr", ["baud_ctr", "baud_edge", "tx_serial", "run_state"], "UART_BAUD_ACCUM", "Abbreviated baud counter baud_ctr")
    ],
    "pipeline": [
        ("v11_pipe_ren_stgvld", "stg1_vld", ["stg1_vld", "stg2_vld", "p_data", "pipe_out"], "PIPELINE_HAZARD_STALL", "Renamed pipeline registers to stg1_vld/stg2_vld"),
        ("v11_pipe_ren_pvalid", "p1_valid", ["p1_valid", "p2_valid", "p1_data", "p2_data"], "PIPELINE_HAZARD_STALL", "Pipeline numbered stages p1_valid/p2_valid"),
        ("v11_pipe_ren_fwdvld", "fwd_vld", ["fwd_vld", "pipe_vld", "raw_hazard", "bubble_reg"], "PIPELINE_HAZARD_STALL", "Forwarding valid signal naming fwd_vld"),
        ("v11_pipe_ren_sactive", "s1_active", ["s1_active", "s2_active", "tok_data", "drain_vld"], "PIPELINE_HAZARD_STALL", "Stage active naming s1_active/s2_active"),
        ("v11_pipe_ren_idvld", "id_vld", ["id_vld", "ex_vld", "inst_data", "alu_out"], "PIPELINE_HAZARD_STALL", "Instruction Decode / Execute naming id_vld/ex_vld"),
        ("v11_pipe_ren_stagevld", "stage_a_vld", ["stage_a_vld", "stage_b_vld", "bus_a", "bus_b"], "PIPELINE_HAZARD_STALL", "Alphabetical stage naming stage_a_vld"),
        ("v11_pipe_ren_tokvld", "tok_vld1", ["tok_vld1", "tok_vld2", "token_payload", "final_valid"], "PIPELINE_HAZARD_STALL", "Token pipeline terminology tok_vld1"),
        ("v11_pipe_ren_sready", "s1_ready_sig", ["s1_ready_sig", "s2_ready_sig", "lane_data", "lane_valid"], "PIPELINE_HAZARD_STALL", "Decoupled lane naming s1_ready_sig")
    ]
}

# ------------------------------------------------------------------------------
# Category B: Structural Generalization (6 per family = 30 cases)
# Varies: Split always blocks, skid buffers, state encodings, decomposed logic
# ------------------------------------------------------------------------------
CAT_B_TEMPLATES = {
    "fifo": [
        ("v11_fifo_str_skid", "count", ["count", "skid_valid", "skid_data", "write_en", "read_en"], "FIFO_SIMULTANEOUS_RW", "Structural skid buffer stage decoupled from RAM"),
        ("v11_fifo_str_splitalways", "occupancy", ["occupancy", "wr_ptr", "rd_ptr", "full_flag", "empty_flag"], "FIFO_SIMULTANEOUS_RW", "Split always-block separating count datapath from control flags"),
        ("v11_fifo_str_decomp", "level_reg", ["level_reg", "inc_strobe", "dec_strobe", "hold_state"], "FIFO_SIMULTANEOUS_RW", "Decomposed Boolean arithmetic for increment/decrement"),
        ("v11_fifo_str_twoport", "entry_cnt", ["entry_cnt", "wr_ack", "rd_ack", "q_full", "q_empty"], "FIFO_SIMULTANEOUS_RW", "Independent dual-clock asynchronous wrapper handshake"),
        ("v11_fifo_str_syncreset", "items_cnt", ["items_cnt", "sync_rst", "wr_pulse", "rd_pulse"], "FIFO_SIMULTANEOUS_RW", "Fully synchronous active-high reset architecture"),
        ("v11_fifo_str_multiword", "word_cnt", ["word_cnt", "burst_size", "fifo_wr", "fifo_rd"], "FIFO_SIMULTANEOUS_RW", "Multi-word burst occupancy calculation")
    ],
    "axi": [
        ("v11_axi_str_skidbuffer", "valid_out", ["valid_out", "ready_out", "skid_reg", "skid_full"], "AXI_HANDSHAKE_LOCK", "Elastic skid buffer isolating upstream ready from downstream valid"),
        ("v11_axi_str_creditpipe", "rx_vld", ["rx_vld", "rx_rdy", "credit_cnt", "credit_dec"], "AXI_HANDSHAKE_LOCK", "Credit-based flow control wrapper around AXI handshake"),
        ("v11_axi_str_registerpipe", "s_axis_tvalid", ["s_axis_tvalid", "s_axis_tready", "pipe_fwd", "pipe_back"], "AXI_HANDSHAKE_LOCK", "Registered boundary pipeline stage on valid/ready pair"),
        ("v11_axi_str_interconnect", "m_vld", ["m_vld", "m_rdy", "demux_sel", "arb_ready"], "AXI_HANDSHAKE_LOCK", "1-to-2 channel demultiplexer handshake interlocking"),
        ("v11_axi_str_asyncbridge", "ch_valid", ["ch_valid", "ch_ready", "toggle_wr", "toggle_rd"], "AXI_HANDSHAKE_LOCK", "Toggle-based clock domain crossing handshake stage"),
        ("v11_axi_str_multibeat", "tx_vld", ["tx_vld", "tx_rdy", "beat_counter", "pkt_last"], "AXI_HANDSHAKE_LOCK", "Packet burst beat counter intertwined with ready stall")
    ],
    "fsm": [
        ("v11_fsm_str_onehot", "state_onehot", ["state_onehot", "next_onehot", "in_bit", "seq_out"], "FSM_STATE_TRANSITION", "One-hot state encoding (4-bit hot) with deadlock at S2"),
        ("v11_fsm_str_splittree", "curr_state", ["curr_state", "next_state", "condition_tree", "out_pulse"], "FSM_STATE_TRANSITION", "Two always-block architecture with separated output logic"),
        ("v11_fsm_str_graycode", "fsm_gray", ["fsm_gray", "fsm_nxt", "data_in", "flag_out"], "FSM_STATE_TRANSITION", "Gray-coded state sequencer with glitch-free transitions"),
        ("v11_fsm_str_hierarchical", "sub_state", ["main_state", "sub_state", "sub_next", "branch_en"], "FSM_STATE_TRANSITION", "Hierarchical nested FSM with sub-state transition stall"),
        ("v11_fsm_str_mooreout", "st_reg", ["st_reg", "st_next", "moore_dec", "detected"], "FSM_STATE_TRANSITION", "Strict Moore output decoder isolated from transition matrix"),
        ("v11_fsm_str_lookahead", "seq_state", ["seq_state", "lookahead_bit", "fast_match", "slow_match"], "FSM_STATE_TRANSITION", "Lookahead pattern matching FSM with early transition")
    ],
    "uart": [
        ("v11_uart_str_fractional", "accum", ["accum", "frac_step", "int_tick", "ser_out"], "UART_BAUD_ACCUM", "Fractional baud rate accumulator using Bresenham algorithm"),
        ("v11_uart_str_dualclock", "baud_div", ["baud_div", "ref_clk", "sample_clk", "tx_pin"], "UART_BAUD_ACCUM", "Dual-clock baud generator with domain crossing toggle"),
        ("v11_uart_str_fifoqueue", "tick_cnt", ["tick_cnt", "tx_fifo_empty", "shift_load", "tx_busy"], "UART_BAUD_ACCUM", "UART transmitter coupled to internal transmit buffer"),
        ("v11_uart_str_oversample16", "clk_div", ["clk_div", "os_16x_tick", "majority_bit", "tx_line"], "UART_BAUD_ACCUM", "16x oversampling baud rate state machine"),
        ("v11_uart_str_syncreset", "sample_cnt", ["sample_cnt", "sync_rst", "tx_strobe", "frame_ok"], "UART_BAUD_ACCUM", "Synchronous active-high reset timing structure"),
        ("v11_uart_str_autoalign", "sub_counter", ["sub_counter", "drift_corr", "tx_wire", "baud_lock"], "UART_BAUD_ACCUM", "Auto-aligning clock drift tracking accumulator")
    ],
    "pipeline": [
        ("v11_pipe_str_splitdatapath", "stg1_vld", ["stg1_vld", "stg2_vld", "alu_op", "reg_file_we"], "PIPELINE_HAZARD_STALL", "Separated datapath and hazard control unit"),
        ("v11_pipe_str_elasticring", "p1_valid", ["p1_valid", "p2_valid", "ring_token", "stall_ring"], "PIPELINE_HAZARD_STALL", "Elastic ring pipeline with backpressure tokens"),
        ("v11_pipe_str_branchpred", "fwd_vld", ["fwd_vld", "pipe_vld", "pred_taken", "flush_pipeline"], "PIPELINE_HAZARD_STALL", "Branch prediction flush bubble injection"),
        ("v11_pipe_str_3stagedeep", "s1_active", ["s1_active", "s2_active", "s3_active", "drain_valid"], "PIPELINE_HAZARD_STALL", "3-stage deep decoupled hazard forwarding pipeline"),
        ("v11_pipe_str_variablelat", "id_vld", ["id_vld", "ex_vld", "mem_vld", "stall_req"], "PIPELINE_HAZARD_STALL", "Variable-latency memory hazard stall mechanism"),
        ("v11_pipe_str_interleaving", "tok_vld1", ["tok_vld1", "tok_vld2", "thread_id", "sched_valid"], "PIPELINE_HAZARD_STALL", "Dual-thread interleaved pipeline slot allocation")
    ]
}

# ------------------------------------------------------------------------------
# Category C: Negative and Safety Stress Tests (6 per family = 30 cases)
# 3 Adversarial Negatives + 3 Incomplete Trace Negatives per family
# ------------------------------------------------------------------------------
CAT_C_TEMPLATES = {
    "fifo": [
        # Adversarial Negatives
        ("v11_fifo_neg_adv_ptrovf", "write_ptr", ["write_ptr", "count", "read_ptr", "full"], "FIFO_PTR_OVERFLOW", "ADVERSARIAL_NEGATIVE", "Pointer overflow trap: lexical overlap on count, but actual bug is write_ptr wrap"),
        ("v11_fifo_neg_adv_rstpol", "rst_n", ["rst_n", "count", "write_en", "empty"], "FIFO_RESET_POLARITY", "ADVERSARIAL_NEGATIVE", "Active-low vs active-high reset polarity glitch, count logic is correct"),
        ("v11_fifo_neg_adv_watermark", "watermark", ["watermark", "count", "high_thresh", "irq_full"], "FIFO_WATERMARK_TRAP", "ADVERSARIAL_NEGATIVE", "Interrupt watermark flag threshold off-by-one; simultaneous R/W logic is sound"),
        # Incomplete Traces
        ("v11_fifo_neg_inc_midburst", "count", ["count", "write_en", "read_en"], "FIFO_SIMULTANEOUS_RW", "INCOMPLETE_TRACE_NEGATIVE", "Trace truncated mid-burst at cycle T=15 before simultaneous R/W occurs"),
        ("v11_fifo_neg_inc_noobs", "occupancy", ["occupancy", "full_flag", "empty_flag"], "FIFO_SIMULTANEOUS_RW", "INCOMPLETE_TRACE_NEGATIVE", "Unobserved internal counter; only top-level full/empty pins visible"),
        ("v11_fifo_neg_inc_ambig", "fifo_level", ["fifo_level", "push", "pop"], "FIFO_SIMULTANEOUS_RW", "INCOMPLETE_TRACE_NEGATIVE", "Ambiguous multi-cycle clock jitter obscuring transition cycle")
    ],
    "axi": [
        # Adversarial Negatives
        ("v11_axi_neg_adv_bresp", "bresp", ["bresp", "valid_out", "ready_out", "bvalid"], "AXI_RESP_CORRUPT", "ADVERSARIAL_NEGATIVE", "Response bus error status corruption; valid/ready handshake is compliant"),
        ("v11_axi_neg_adv_strobe", "wstrb", ["wstrb", "rx_vld", "rx_rdy", "wdata"], "AXI_STROBE_MASK", "ADVERSARIAL_NEGATIVE", "Byte strobe unaligned masking drops upper bytes; handshake completes normally"),
        ("v11_axi_neg_adv_underflow", "credit_cnt", ["credit_cnt", "s_axis_tvalid", "s_axis_tready"], "AXI_CREDIT_UNDERFLOW", "ADVERSARIAL_NEGATIVE", "Credit counter underflow drops credits; channel handshake is structurally correct"),
        # Incomplete Traces
        ("v11_axi_neg_inc_prestall", "valid_out", ["valid_out", "ready_out"], "AXI_HANDSHAKE_LOCK", "INCOMPLETE_TRACE_NEGATIVE", "Simulation cut off before downstream backpressure asserts ready=0"),
        ("v11_axi_neg_inc_maskrdy", "rx_vld", ["rx_vld", "rx_data"], "AXI_HANDSHAKE_LOCK", "INCOMPLETE_TRACE_NEGATIVE", "Ready signal omitted from trace VCD header; cannot verify handshake protocol"),
        ("v11_axi_neg_inc_droppedack", "m_vld", ["m_vld", "m_rdy"], "AXI_HANDSHAKE_LOCK", "INCOMPLETE_TRACE_NEGATIVE", "Intermittent acknowledge drop with ambiguous causality")
    ],
    "fsm": [
        # Adversarial Negatives
        ("v11_fsm_neg_adv_resetglitch", "rst_glitch", ["rst_glitch", "fsm_st", "nxt_st", "clk"], "FSM_RESET_GLITCH", "ADVERSARIAL_NEGATIVE", "Asynchronous reset bounce resets machine; state transition table is correct"),
        ("v11_fsm_neg_adv_prio", "prio_sel", ["prio_sel", "curr_state", "next_state", "req"], "FSM_PRIORITY_INVERT", "ADVERSARIAL_NEGATIVE", "Arbiter priority inversion stalls service; individual states transition cleanly"),
        ("v11_fsm_neg_adv_illegal", "illegal_st", ["illegal_st", "st_reg", "st_nxt", "err"], "FSM_ILLEGAL_STATE", "ADVERSARIAL_NEGATIVE", "SEU soft error recovery trap; valid input path is correct"),
        # Incomplete Traces
        ("v11_fsm_neg_inc_earlycut", "state", ["state", "in_bit", "clk"], "FSM_STATE_TRANSITION", "INCOMPLETE_TRACE_NEGATIVE", "Trace truncated at state S1 before transition to defective state S2"),
        ("v11_fsm_neg_inc_grayhide", "fsm_gray", ["symbol_in", "out_pulse"], "FSM_STATE_TRANSITION", "INCOMPLETE_TRACE_NEGATIVE", "State vector optimized out of debug netlist; only primary I/O available"),
        ("v11_fsm_neg_inc_multitrig", "detector_state", ["detector_state", "in_bit"], "FSM_STATE_TRANSITION", "INCOMPLETE_TRACE_NEGATIVE", "Multiple overlapping input pulses create ambiguous transition timing")
    ],
    "uart": [
        # Adversarial Negatives
        ("v11_uart_neg_adv_stopbit", "stop_bit", ["stop_bit", "baud_div", "ser_out", "tx_busy"], "UART_FRAMING_ERROR", "ADVERSARIAL_NEGATIVE", "Framing generator outputs 0.5 stop bits; baud accumulator rollover is accurate"),
        ("v11_uart_neg_adv_parity", "parity_bit", ["parity_bit", "accum", "tx_pin"], "UART_PARITY_INVERT", "ADVERSARIAL_NEGATIVE", "Odd/even parity calculation inverted; baud clock frequency matches baud rate"),
        ("v11_uart_neg_adv_shiftstall", "shift_reg", ["shift_reg", "tick_cnt", "ser_out"], "UART_SHIFT_STALL", "ADVERSARIAL_NEGATIVE", "Shift register load enable blocked; baud divider ticks as expected"),
        # Incomplete Traces
        ("v11_uart_neg_inc_shortbaud", "baud_div", ["baud_div", "tx_pin"], "UART_BAUD_ACCUM", "INCOMPLETE_TRACE_NEGATIVE", "Trace ends at sample tick 3 before baud accumulator completes first rollover"),
        ("v11_uart_neg_inc_notx", "accum", ["step_tick", "active_flag"], "UART_BAUD_ACCUM", "INCOMPLETE_TRACE_NEGATIVE", "Transmit pin txd unobserved in VCD waveform header"),
        ("v11_uart_neg_inc_jitter", "tick_cnt", ["tick_cnt", "ser_out"], "UART_BAUD_ACCUM", "INCOMPLETE_TRACE_NEGATIVE", "Excessive simulated clock phase noise masks drift trajectory")
    ],
    "pipeline": [
        # Adversarial Negatives
        ("v11_pipe_neg_adv_fwddata", "fwd_data", ["fwd_data", "stg1_vld", "stg2_vld", "out_data"], "PIPELINE_DATA_HAZARD", "ADVERSARIAL_NEGATIVE", "ALU forwarding mux selects stale operand; valid/stall bubble control is correct"),
        ("v11_pipe_neg_adv_branchflush", "flush_latch", ["flush_latch", "p1_valid", "p2_valid"], "PIPELINE_BRANCH_LATCH", "ADVERSARIAL_NEGATIVE", "Branch mispredict flush latch fails to clear; pipeline stall registers are sound"),
        ("v11_pipe_neg_adv_squash", "squash_mask", ["squash_mask", "fwd_vld", "pipe_vld"], "PIPELINE_EXC_SQUASH", "ADVERSARIAL_NEGATIVE", "Exception squash mask inverts instruction retire; stall hazard logic is correct"),
        # Incomplete Traces
        ("v11_pipe_neg_inc_nostall", "stg1_vld", ["stg1_vld", "p_data"], "PIPELINE_HAZARD_STALL", "INCOMPLETE_TRACE_NEGATIVE", "Simulation stopped at cycle T=10 before hazard condition triggers"),
        ("v11_pipe_neg_inc_blackbox", "p1_valid", ["in_valid", "out_valid"], "PIPELINE_HAZARD_STALL", "INCOMPLETE_TRACE_NEGATIVE", "Internal pipeline stages synthesized as black box; internal valid signals missing"),
        ("v11_pipe_neg_inc_multihaz", "s1_active", ["s1_active", "s2_active"], "PIPELINE_HAZARD_STALL", "INCOMPLETE_TRACE_NEGATIVE", "Concurrent structural and data hazards creating ambiguous causality")
    ]
}


def build_manifest():
    cases = []
    case_idx = 1

    for fam in FAMILIES:
        # 1. Category A (8 cases)
        for cid, gt, cands, mech, desc in CAT_A_TEMPLATES[fam]:
            cases.append({
                "case_index": case_idx,
                "case_id": cid,
                "hardware_family": fam,
                "benchmark_category": "CATEGORY_A_IN_FAMILY",
                "role": "TARGET_POSITIVE",
                "case_type": "POSITIVE_REUSE_OPPORTUNITY",
                "ground_truth_signal": gt,
                "ground_truth_signals": [gt],
                "defect_mechanism": mech,
                "symptom": "Functional Assertion Failure",
                "description": desc,
                "is_reusable_positive": True,
                "is_adversarial_negative": False,
                "is_incomplete_trace": False,
                "candidate_signals": cands
            })
            case_idx += 1

        # 2. Category B (6 cases)
        for cid, gt, cands, mech, desc in CAT_B_TEMPLATES[fam]:
            cases.append({
                "case_index": case_idx,
                "case_id": cid,
                "hardware_family": fam,
                "benchmark_category": "CATEGORY_B_STRUCTURAL",
                "role": "TARGET_POSITIVE",
                "case_type": "POSITIVE_REUSE_OPPORTUNITY",
                "ground_truth_signal": gt,
                "ground_truth_signals": [gt],
                "defect_mechanism": mech,
                "symptom": "Functional Assertion Failure",
                "description": desc,
                "is_reusable_positive": True,
                "is_adversarial_negative": False,
                "is_incomplete_trace": False,
                "candidate_signals": cands
            })
            case_idx += 1

        # 3. Category C (6 cases: 3 Adv, 3 Inc)
        for cid, gt, cands, mech, ctype, desc in CAT_C_TEMPLATES[fam]:
            is_adv = (ctype == "ADVERSARIAL_NEGATIVE")
            is_inc = (ctype == "INCOMPLETE_TRACE_NEGATIVE")
            role = "TARGET_ADVERSARIAL_NEGATIVE" if is_adv else "TARGET_INCOMPLETE_EVIDENCE"
            cases.append({
                "case_index": case_idx,
                "case_id": cid,
                "hardware_family": fam,
                "benchmark_category": "CATEGORY_C_NEGATIVE_STRESS",
                "role": role,
                "case_type": ctype,
                "ground_truth_signal": gt,
                "ground_truth_signals": [gt],
                "defect_mechanism": mech,
                "symptom": "Adversarial or Incomplete Telemetry",
                "description": desc,
                "is_reusable_positive": False,
                "is_adversarial_negative": is_adv,
                "is_incomplete_trace": is_inc,
                "candidate_signals": cands
            })
            case_idx += 1

    manifest = {
        "manifest_metadata": {
            "experiment_id": "V11_BENCHMARK_EXPANSION_AND_GENERALIZATION",
            "timestamp": "2026-09-06T07:15:00Z",
            "total_cases": len(cases),
            "hardware_families": FAMILIES,
            "categories": {
                "CATEGORY_A_IN_FAMILY": sum(1 for c in cases if c["benchmark_category"] == "CATEGORY_A_IN_FAMILY"),
                "CATEGORY_B_STRUCTURAL": sum(1 for c in cases if c["benchmark_category"] == "CATEGORY_B_STRUCTURAL"),
                "CATEGORY_C_NEGATIVE_STRESS": sum(1 for c in cases if c["benchmark_category"] == "CATEGORY_C_NEGATIVE_STRESS")
            },
            "composition": {
                "positive_reuse_opportunities": sum(1 for c in cases if c["is_reusable_positive"]),
                "adversarial_negative_targets": sum(1 for c in cases if c["is_adversarial_negative"]),
                "incomplete_trace_targets": sum(1 for c in cases if c["is_incomplete_trace"])
            }
        },
        "cases": cases
    }

    out_path = os.path.join(REPORTS_DIR, "v11_benchmark_manifest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"V11 Benchmark Manifest generated: {out_path}")
    print(f"Total Cases: {len(cases)}")
    print(f"Categories: {manifest['manifest_metadata']['categories']}")
    print(f"Composition: {manifest['manifest_metadata']['composition']}")


if __name__ == "__main__":
    build_manifest()
