"""Small, dependency-light smoke example for adaptive evidence classification."""

import os
import sys

# Keep direct execution from ``examples/`` consistent with the experiment runners.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.reuse.adaptive_evidence import AdaptiveEvidenceClassifier
from src.reuse.adaptive_transaction_boundary import AdaptiveTransactionBoundaryDetector


def main() -> None:
    states = [
        {"rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0},
        {"rst_n": 1, "valid_in": 1, "ready_in": 0, "valid_out": 0},
        {"rst_n": 1, "valid_in": 1, "ready_in": 1, "valid_out": 1},
        {"rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0},
        {"rst_n": 1, "valid_in": 0, "ready_in": 0, "valid_out": 0},
    ]

    detector = AdaptiveTransactionBoundaryDetector(quiescence_threshold=2)
    segments = detector.detect_segments(states, ["valid_in", "ready_in", "valid_out"])
    evidence = AdaptiveEvidenceClassifier().classify_sufficiency(states, segments)

    print(f"segments: {len(segments)}")
    print(f"evidence state: {evidence.sufficiency_state}")
    print(f"recommendation: {evidence.decision_recommendation}")


if __name__ == "__main__":
    main()
