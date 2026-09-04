import pytest
import os
import sys

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.reuse.v8_semantic_roles import HardwareRole, SemanticRoleNormalizer
from src.reuse.v8_protocol_adapters import ProtocolRegistry, FifoProtocolAdapter, UartProtocolAdapter
from src.reuse.v8_certificate_store import V8CertificateStore


def test_fifo_signal_alias_generalization():
    """
    Tests whether a certificate extracted on 'count' can successfully match
    and validate a target design where the signal is named 'fifo_count' or 'occ_cnt'.
    """
    store = V8CertificateStore()
    fifo_adapter = ProtocolRegistry.get_adapter("fifo")

    # Source certificate extracted on canonical 'count'
    source_cert = fifo_adapter.extract_certificate_specs(
        source_id="source_fifo_1",
        defect_desc="FIFO concurrent RW corruption",
        symptom="Data Mismatch",
        signals=["clk", "rst_n", "write_en", "read_en", "count", "write_ptr", "read_ptr"],
        root_sig="count",
        confidence=0.95
    )
    source_cert.trust_metadata.trust_status = source_cert.trust_metadata.trust_status.TRUSTED
    store.register(source_cert)

    # 1. Target with renamed signal 'fifo_count'
    target_signals_renamed = ["clk", "rst_n", "write_en", "read_en", "fifo_count", "write_ptr", "read_ptr"]
    candidates = store.query_candidates(
        design_family="fifo",
        observed_signals=target_signals_renamed,
        symptom="Data Mismatch",
        only_trusted=True
    )
    assert len(candidates) > 0
    top_score, top_cert = candidates[0]
    assert top_score > 5.0
    assert top_cert.root_cause.normalized_role == HardwareRole.OCCUPANCY_TRACKER

    # 2. Simulate target cycle states with 'fifo_count'
    # Concurrent read/write at cycle 2 with abnormal delta
    target_states = [
        {"clk": 1, "rst_n": 0, "write_en": 0, "read_en": 0, "fifo_count": 0, "write_ptr": 0, "read_ptr": 0},
        {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "fifo_count": 0, "write_ptr": 0, "read_ptr": 0},
        {"clk": 1, "rst_n": 1, "write_en": 1, "read_en": 1, "fifo_count": 1, "write_ptr": 1, "read_ptr": 1, "empty": 0},
        {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "fifo_count": 1, "write_ptr": 1, "read_ptr": 1, "empty": 1},
        {"clk": 1, "rst_n": 1, "write_en": 0, "read_en": 0, "fifo_count": 1, "write_ptr": 1, "read_ptr": 1, "empty": 1}
    ]

    target_role_map = SemanticRoleNormalizer.map_signals_to_roles(target_signals_renamed, design_family="fifo")
    assert target_role_map["fifo_count"] == HardwareRole.OCCUPANCY_TRACKER

    val_res = fifo_adapter.validate_target(top_cert, target_states, target_role_map)
    assert val_res["decision"] == "PASS"
    assert val_res["matched_root_cause"] == "fifo_count"


def test_uart_baud_alias_generalization():
    """
    Tests whether a certificate extracted on 'cnt' can match a design with 'baud_cnt' or 'clk_div'.
    """
    store = V8CertificateStore()
    uart_adapter = ProtocolRegistry.get_adapter("uart")

    source_cert = uart_adapter.extract_certificate_specs(
        source_id="source_uart_1",
        defect_desc="UART baud timing drift",
        symptom="Framing Error",
        signals=["clk", "rst_n", "tx", "cnt"],
        root_sig="cnt",
        confidence=0.92
    )
    source_cert.trust_metadata.trust_status = source_cert.trust_metadata.trust_status.TRUSTED
    store.register(source_cert)

    # Target uses 'baud_cnt'
    target_signals = ["clk", "rst_n", "tx", "baud_cnt"]
    candidates = store.query_candidates(
        design_family="uart",
        observed_signals=target_signals,
        symptom="Framing Error",
        only_trusted=True
    )
    assert len(candidates) > 0
    top_score, top_cert = candidates[0]
    assert top_cert.root_cause.normalized_role == HardwareRole.BAUD_PRESCALER

    # Simulate baud rollover defect (counts to 5 instead of 7)
    target_states = [
        {"clk": 1, "rst_n": 0, "tx": 1, "baud_cnt": 0},
        {"clk": 1, "rst_n": 1, "tx": 0, "baud_cnt": 1},
        {"clk": 1, "rst_n": 1, "tx": 0, "baud_cnt": 3},
        {"clk": 1, "rst_n": 1, "tx": 0, "baud_cnt": 5},
        {"clk": 1, "rst_n": 1, "tx": 0, "baud_cnt": 0},  # rollover at 5!
        {"clk": 1, "rst_n": 1, "tx": 0, "baud_cnt": 2}
    ]
    target_role_map = SemanticRoleNormalizer.map_signals_to_roles(target_signals, design_family="uart")
    assert target_role_map["baud_cnt"] == HardwareRole.BAUD_PRESCALER

    val_res = uart_adapter.validate_target(top_cert, target_states, target_role_map)
    assert val_res["decision"] == "PASS"
    assert val_res["matched_root_cause"] == "baud_cnt"


def test_safety_preservation_on_incompatible_roles():
    """
    Confirms that incompatible roles (e.g. pointer vs occupancy) are NOT conflated.
    """
    target_signals = ["clk", "rst_n", "write_ptr", "read_ptr"]
    role_map = SemanticRoleNormalizer.map_signals_to_roles(target_signals, design_family="fifo")

    # Incompatible: pointer is not occupancy
    assert role_map["write_ptr"] == HardwareRole.POINTER
    assert not SemanticRoleNormalizer.are_roles_compatible(HardwareRole.OCCUPANCY_TRACKER, role_map["write_ptr"])
