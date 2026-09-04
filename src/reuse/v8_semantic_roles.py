import re
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple


class HardwareRole(str, Enum):
    """Normalized hardware architectural roles across diverse RTL designs."""
    OCCUPANCY_TRACKER = "OCCUPANCY_TRACKER"
    POINTER = "POINTER"
    STATE_REGISTER = "STATE_REGISTER"
    HANDSHAKE_VALID = "HANDSHAKE_VALID"
    HANDSHAKE_READY = "HANDSHAKE_READY"
    PIPELINE_TOKEN = "PIPELINE_TOKEN"
    PIPELINE_DATA_REG = "PIPELINE_DATA_REG"
    BAUD_PRESCALER = "BAUD_PRESCALER"
    TICK_STROBE = "TICK_STROBE"
    OUTPUT_STROBE = "OUTPUT_STROBE"
    CLOCK = "CLOCK"
    RESET = "RESET"
    DATA_INPUT = "DATA_INPUT"
    DATA_OUTPUT = "DATA_OUTPUT"
    GENERIC_CONTROL = "GENERIC_CONTROL"
    GENERIC_INTERNAL_REG = "GENERIC_INTERNAL_REG"
    GENERIC_PORT = "GENERIC_PORT"


class SignalDirection(str, Enum):
    """Directionality of a hardware signal."""
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    INOUT = "INOUT"
    INTERNAL_REGISTER = "INTERNAL_REGISTER"
    INTERNAL_WIRE = "INTERNAL_WIRE"
    UNKNOWN = "UNKNOWN"


class RoleClass(str, Enum):
    """High-level functional category of a hardware signal."""
    STATE = "STATE"
    CONTROL = "CONTROL"
    DATA = "DATA"
    TIMING = "TIMING"
    STATUS = "STATUS"
    CLOCK_RESET = "CLOCK_RESET"


class SemanticRoleNormalizer:
    """
    Deterministic Architectural Role Normalizer.
    
    Maps heterogeneous, variant signal identifiers across differing IP implementations
    into standardized HardwareRoles without ungrounded synonym hallucination.
    """

    # Family-specific and general regex pattern mappings
    _ROLE_PATTERNS = [
        # Clocks & Resets
        (re.compile(r"^(clk|clock|clk_i|sys_clk)$", re.IGNORECASE), HardwareRole.CLOCK, RoleClass.CLOCK_RESET),
        (re.compile(r"^(rst|rst_n|reset|reset_n|rst_b|arst_n)$", re.IGNORECASE), HardwareRole.RESET, RoleClass.CLOCK_RESET),
        
        # FIFO
        (re.compile(r"^(count|fifo_count|occ_cnt|occupancy|fill_level|items_count|count_r)$", re.IGNORECASE), HardwareRole.OCCUPANCY_TRACKER, RoleClass.STATUS),
        (re.compile(r"^(write_ptr|read_ptr|wr_ptr|rd_ptr|w_ptr|r_ptr|wr_p|rd_p|head_ptr|tail_ptr)$", re.IGNORECASE), HardwareRole.POINTER, RoleClass.STATE),
        
        # AXI & Handshakes
        (re.compile(r"^(valid_out|vld_out|m_valid|tx_valid|data_valid|out_valid|valid_o)$", re.IGNORECASE), HardwareRole.HANDSHAKE_VALID, RoleClass.CONTROL),
        (re.compile(r"^(valid_in|vld_in|s_valid|rx_valid|in_valid|valid_i)$", re.IGNORECASE), HardwareRole.HANDSHAKE_VALID, RoleClass.CONTROL),
        (re.compile(r"^(ready_in|rdy_in|m_ready|rx_ready|data_ready|ready_i)$", re.IGNORECASE), HardwareRole.HANDSHAKE_READY, RoleClass.CONTROL),
        (re.compile(r"^(ready_out|rdy_out|s_ready|tx_ready|out_ready|ready_o)$", re.IGNORECASE), HardwareRole.HANDSHAKE_READY, RoleClass.CONTROL),
        
        # FSM
        (re.compile(r"^(state|current_state|fsm_state|cur_state|cs|state_reg)$", re.IGNORECASE), HardwareRole.STATE_REGISTER, RoleClass.STATE),
        (re.compile(r"^(next_state|nxt_state|ns|state_next)$", re.IGNORECASE), HardwareRole.STATE_REGISTER, RoleClass.STATE),
        
        # Pipeline
        (re.compile(r"^(v1|v2|v3|stage1_valid|stage2_valid|val_s1|val_s2|stg1_vld|valid_q1|valid_q2)$", re.IGNORECASE), HardwareRole.PIPELINE_TOKEN, RoleClass.CONTROL),
        (re.compile(r"^(d1|d2|d3|stage1_data|stage2_data|dat_s1|dat_s2|stg1_dat|data_q1|data_q2)$", re.IGNORECASE), HardwareRole.PIPELINE_DATA_REG, RoleClass.DATA),
        
        # UART / Comm Prescaler
        (re.compile(r"^(cnt|baud_cnt|clk_div|prescaler|baud_divider|clk_counter|div_cnt|baud_reg)$", re.IGNORECASE), HardwareRole.BAUD_PRESCALER, RoleClass.TIMING),
        (re.compile(r"^(tick|baud_tick|sample_pulse|baud_pulse|sample_tick)$", re.IGNORECASE), HardwareRole.TICK_STROBE, RoleClass.TIMING),
        (re.compile(r"^(tx|uart_tx|txd|serial_out|tx_out)$", re.IGNORECASE), HardwareRole.OUTPUT_STROBE, RoleClass.DATA),
        (re.compile(r"^(rx|uart_rx|rxd|serial_in|rx_in)$", re.IGNORECASE), HardwareRole.DATA_INPUT, RoleClass.DATA),
        (re.compile(r"^(done|finished|complete|txn_done|tx_done)$", re.IGNORECASE), HardwareRole.OUTPUT_STROBE, RoleClass.CONTROL),
    ]

    @classmethod
    def normalize_signal(cls, signal_name: str,
                         design_family: Optional[str] = None,
                         direction: SignalDirection = SignalDirection.UNKNOWN,
                         decl_type: Optional[str] = None) -> Tuple[HardwareRole, RoleClass]:
        """
        Infers canonical HardwareRole and RoleClass from signal identifier,
        design family context, and RTL declaration attributes.
        """
        clean_sig = signal_name.strip()

        # 1. Family-Specific Priors
        if design_family:
            fam_lower = design_family.lower()
            if fam_lower == "fifo":
                if clean_sig in ["count", "fifo_count", "occ_cnt", "occupancy"]:
                    return HardwareRole.OCCUPANCY_TRACKER, RoleClass.STATUS
                if "ptr" in clean_sig.lower():
                    return HardwareRole.POINTER, RoleClass.STATE
            elif fam_lower == "uart":
                if clean_sig in ["cnt", "baud_cnt", "clk_div", "prescaler"]:
                    return HardwareRole.BAUD_PRESCALER, RoleClass.TIMING
            elif fam_lower == "pipeline":
                if clean_sig in ["v1", "v2", "v3"] or re.match(r"^v\d+$", clean_sig):
                    return HardwareRole.PIPELINE_TOKEN, RoleClass.CONTROL
                if clean_sig in ["d1", "d2", "d3"] or re.match(r"^d\d+$", clean_sig):
                    return HardwareRole.PIPELINE_DATA_REG, RoleClass.DATA
            elif fam_lower == "axi":
                if "valid" in clean_sig.lower():
                    return HardwareRole.HANDSHAKE_VALID, RoleClass.CONTROL
                if "ready" in clean_sig.lower():
                    return HardwareRole.HANDSHAKE_READY, RoleClass.CONTROL
            elif fam_lower == "fsm":
                if "state" in clean_sig.lower():
                    return HardwareRole.STATE_REGISTER, RoleClass.STATE

        # 2. General Pattern Matching
        for pattern, role, r_class in cls._ROLE_PATTERNS:
            if pattern.match(clean_sig):
                return role, r_class

        # 3. Fallback based on Direction / Declaration
        if direction == SignalDirection.INPUT:
            return HardwareRole.GENERIC_CONTROL, RoleClass.CONTROL
        elif direction == SignalDirection.OUTPUT:
            return HardwareRole.OUTPUT_STROBE, RoleClass.STATUS
        elif direction == SignalDirection.INTERNAL_REGISTER:
            return HardwareRole.GENERIC_INTERNAL_REG, RoleClass.STATE

        return HardwareRole.GENERIC_PORT, RoleClass.CONTROL

    @classmethod
    def are_roles_compatible(cls, source_role: HardwareRole, target_role: HardwareRole) -> bool:
        """
        Determines whether two hardware roles are semantically equivalent for reuse.
        Strict: Only identical roles or directly interchangeable sub-roles match.
        """
        if source_role == target_role:
            return True

        # Equivalent control groupings
        valid_group = {HardwareRole.HANDSHAKE_VALID}
        if source_role in valid_group and target_role in valid_group:
            return True

        ready_group = {HardwareRole.HANDSHAKE_READY}
        if source_role in ready_group and target_role in ready_group:
            return True

        prescaler_group = {HardwareRole.BAUD_PRESCALER}
        if source_role in prescaler_group and target_role in prescaler_group:
            return True

        occupancy_group = {HardwareRole.OCCUPANCY_TRACKER}
        if source_role in occupancy_group and target_role in occupancy_group:
            return True

        return False

    @classmethod
    def map_signals_to_roles(cls, signal_names: List[str],
                             design_family: Optional[str] = None,
                             rtl_declarations: Optional[Dict[str, Any]] = None) -> Dict[str, HardwareRole]:
        """Maps a collection of signal names to their normalized HardwareRoles."""
        mapping = {}
        for sig in signal_names:
            direction = SignalDirection.UNKNOWN
            if rtl_declarations and sig in rtl_declarations:
                d_str = rtl_declarations[sig].get("direction", "").upper()
                if "IN" in d_str and "OUT" not in d_str:
                    direction = SignalDirection.INPUT
                elif "OUT" in d_str:
                    direction = SignalDirection.OUTPUT
                elif "REG" in d_str:
                    direction = SignalDirection.INTERNAL_REGISTER

            role, _ = cls.normalize_signal(sig, design_family=design_family, direction=direction)
            mapping[sig] = role
        return mapping
