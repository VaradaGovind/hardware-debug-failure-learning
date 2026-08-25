import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple, Set

@dataclass
class TransactionEvent:
    cycle: int
    event_type: str  # "RISING_EDGE", "FALLING_EDGE", "HANDSHAKE_ACCEPT", "HANDSHAKE_STALL", "STATE_TRANSITION", "DATA_TRANSFER", "ASSERTION_ACTIVE", "QUIESCENCE", "COMPLETION"
    signals: List[str]
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class TransactionSegment:
    start_cycle: int
    end_cycle: int
    event_sequence: List[Dict[str, Any]]
    confidence: float
    evidence_reasons: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return max(1, self.end_cycle - self.start_cycle + 1)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class AdaptiveTransactionBoundaryDetector:
    """Detects transaction boundaries from observable waveform signal events and protocol handshakes."""
    def __init__(self, quiescence_threshold: int = 2, max_window_cycles: int = 50):
        self.quiescence_threshold = quiescence_threshold
        self.max_window_cycles = max_window_cycles
    
    def detect_edges(self, cycle_states: List[Dict[str, Any]], signal: str) -> List[Tuple[int, str]]:
        """Detects rising (0->1) and falling (1->0) transitions for a given signal."""
        edges = []
        for i in range(1, len(cycle_states)):
            prev_val = cycle_states[i - 1].get(signal, None)
            curr_val = cycle_states[i].get(signal, None)
            if prev_val is None or curr_val is None:
                continue
            if prev_val == 0 and curr_val != 0:
                edges.append((i, "RISING_EDGE"))
            elif prev_val != 0 and curr_val == 0:
                edges.append((i, "FALLING_EDGE"))
        return edges

    def detect_signal_activity(self, cycle_states: List[Dict[str, Any]], sigs: List[str]) -> List[int]:
        """Returns cycles where at least one observed signal transitioned or an active enable/handshake was asserted."""
        active_cycles = []
        for i in range(len(cycle_states)):
            curr_s = cycle_states[i]
            if curr_s.get("rst_n", 1) == 0:
                continue
            prev_s = cycle_states[i - 1] if i > 0 else {}
            prev_in_reset = (prev_s.get("rst_n", 1) == 0)
            
            has_activity = False
            for s in sigs:
                v_curr = curr_s.get(s, None)
                v_prev = prev_s.get(s, None)
                
                if any(kw in s for kw in ["start", "en", "valid", "req", "read_", "write_"]):
                    if v_curr == 1:
                        has_activity = True
                        break
                        
                if not prev_in_reset and v_prev is not None and v_curr is not None and v_curr != v_prev:
                    has_activity = True
                    break
                    
            if has_activity:
                active_cycles.append(i)
        return active_cycles

    def detect_handshake_events(self, cycle_states: List[Dict[str, Any]], 
                                req_sig: str, ack_sig: str) -> List[TransactionEvent]:
        """Generic handshake operator: detects request, stall, and accept transitions."""
        events = []
        for i in range(1, len(cycle_states)):
            s = cycle_states[i]
            if s.get("rst_n", 1) == 0:
                continue
            v_req = s.get(req_sig, 0)
            v_ack = s.get(ack_sig, 0)
            
            if v_req == 1 and v_ack == 1:
                events.append(TransactionEvent(
                    cycle=i,
                    event_type="HANDSHAKE_ACCEPT",
                    signals=[req_sig, ack_sig],
                    details={"req": v_req, "ack": v_ack}
                ))
            elif v_req == 1 and v_ack == 0:
                events.append(TransactionEvent(
                    cycle=i,
                    event_type="HANDSHAKE_STALL",
                    signals=[req_sig, ack_sig],
                    details={"req": v_req, "ack": v_ack}
                ))
        return events

    def detect_state_transitions(self, cycle_states: List[Dict[str, Any]], 
                                 state_sig: str) -> List[TransactionEvent]:
        """Generic FSM/state progression operator."""
        events = []
        for i in range(1, len(cycle_states)):
            prev_st = cycle_states[i - 1].get(state_sig, None)
            curr_st = cycle_states[i].get(state_sig, None)
            if prev_st is not None and curr_st is not None and prev_st != curr_st:
                events.append(TransactionEvent(
                    cycle=i,
                    event_type="STATE_TRANSITION",
                    signals=[state_sig],
                    details={"from": prev_st, "to": curr_st}
                ))
        return events

    def detect_data_movement(self, cycle_states: List[Dict[str, Any]], 
                             data_sigs: List[str]) -> List[TransactionEvent]:
        """Generic data-flow / register update operator."""
        events = []
        for i in range(1, len(cycle_states)):
            for sig in data_sigs:
                prev_d = cycle_states[i - 1].get(sig, None)
                curr_d = cycle_states[i].get(sig, None)
                if prev_d is not None and curr_d is not None and prev_d != curr_d:
                    events.append(TransactionEvent(
                        cycle=i,
                        event_type="DATA_TRANSFER",
                        signals=[sig],
                        details={"prev_val": prev_d, "curr_val": curr_d}
                    ))
        return events

    def detect_segments(self, cycle_states: List[Dict[str, Any]], 
                        observed_signals: Optional[List[str]] = None) -> List[TransactionSegment]:
        """
        Recovers variable-length transaction segments from waveform cycle states.
        Clusters contiguous active execution periods and bounds them by initiation
        and completion/quiescence.
        """
        if not cycle_states or len(cycle_states) < 3:
            return []

        if observed_signals is None:
            all_keys = set()
            for s in cycle_states:
                all_keys.update(s.keys())
            observed_signals = [k for k in all_keys if k not in ["clk", "rst_n", "_time", "time"]]

        active_cycles = self.detect_signal_activity(cycle_states, observed_signals)
        if not active_cycles:
            return []

        clusters: List[List[int]] = []
        curr_cluster = [active_cycles[0]]

        for c in active_cycles[1:]:
            if c - curr_cluster[-1] <= self.quiescence_threshold:
                curr_cluster.append(c)
            else:
                clusters.append(curr_cluster)
                curr_cluster = [c]
        if curr_cluster:
            clusters.append(curr_cluster)

        segments: List[TransactionSegment] = []

        for cluster in clusters:
            start_raw = cluster[0]
            end_raw = cluster[-1]

            start_c = max(1, start_raw)
            for s in observed_signals:
                if cycle_states[start_raw].get(s, 0) != 0 and cycle_states[start_raw - 1].get(s, 0) == 0:
                    start_c = min(start_c, start_raw)

            end_c = min(len(cycle_states) - 1, end_raw + 2)

            event_seq: List[TransactionEvent] = []
            evidence_reasons: List[str] = []

            for s in observed_signals:
                edges = self.detect_edges(cycle_states[start_c:end_c + 1], s)
                for rel_c, edge_type in edges:
                    abs_c = start_c + rel_c
                    event_seq.append(TransactionEvent(
                        cycle=abs_c,
                        event_type=edge_type,
                        signals=[s],
                        details={"signal": s}
                    ))
                    if edge_type == "RISING_EDGE" and abs_c <= start_c + 1:
                        evidence_reasons.append(f"Initiation rising edge on '{s}' at cycle {abs_c}")

            for s in observed_signals:
                st_events = self.detect_state_transitions(cycle_states[start_c:end_c + 1], s)
                for ev in st_events:
                    ev.cycle += start_c
                    event_seq.append(ev)
                    evidence_reasons.append(f"State transition on '{s}' ({ev.details['from']} -> {ev.details['to']}) at cycle {ev.cycle}")

            dm_events = self.detect_data_movement(cycle_states[start_c:end_c + 1], observed_signals)
            for ev in dm_events:
                ev.cycle += start_c
                event_seq.append(ev)

            event_seq.sort(key=lambda e: e.cycle)

            conf = 0.4  
            if any(e.event_type == "RISING_EDGE" for e in event_seq):
                conf += 0.2
            if any(e.event_type in ["STATE_TRANSITION", "DATA_TRANSFER", "HANDSHAKE_ACCEPT"] for e in event_seq):
                conf += 0.2
            if end_c < len(cycle_states) - 1:
                conf += 0.2  
                evidence_reasons.append(f"Transaction completed cleanly with post-activity quiescence at cycle {end_c}")
            else:
                evidence_reasons.append(f"Transaction active through end of recorded trace at cycle {end_c}")

            segments.append(TransactionSegment(
                start_cycle=start_c,
                end_cycle=end_c,
                event_sequence=[e.to_dict() for e in event_seq],
                confidence=min(1.0, conf),
                evidence_reasons=evidence_reasons,
                metadata={
                    "cluster_span": [start_raw, end_raw],
                    "raw_length": end_raw - start_raw + 1,
                    "adaptive_window_length": end_c - start_c + 1,
                    "event_count": len(event_seq)
                }
            ))

        return segments

    def detect_primary_segment(self, cycle_states: List[Dict[str, Any]], 
                               observed_signals: Optional[List[str]] = None) -> Optional[TransactionSegment]:
        """Returns the primary (highest confidence / longest valid) transaction segment."""
        segments = self.detect_segments(cycle_states, observed_signals)
        if not segments:
            return None
        segments.sort(key=lambda s: (s.confidence, s.length), reverse=True)
        return segments[0]
