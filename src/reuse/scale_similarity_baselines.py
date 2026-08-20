import os
import re
import numpy as np
from typing import Dict, Any, List
from .causal_certificate import parse_vcd_signals

def tokenize_log(log_text: str) -> set:
    clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', log_text.lower())
    return {t for t in clean.split() if len(t) > 1}

def jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return inter / union if union > 0 else 0.0

def levenshtein_similarity(s1: str, s2: str) -> float:
    s1, s2 = s1.strip().lower(), s2.strip().lower()
    if not s1 or not s2: return 0.0
    if s1 == s2: return 1.0
    len1, len2 = len(s1), len(s2)
    matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1): matrix[i][0] = i
    for j in range(len2 + 1): matrix[0][j] = j
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            matrix[i][j] = min(matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + cost)
    dist = matrix[len1][len2]
    max_len = max(len1, len2)
    return 1.0 - (dist / max_len) if max_len > 0 else 1.0

class ScaleSimilarityBaselines:
    """
    Evaluates similarity baselines for large-scale reuse comparison:
    1. Log / Symptom Similarity
    2. Semantic Keyword Similarity
    3. RTL Structural & Dependency Graph Similarity
    4. Composite Multi-Modal Similarity (Waveform + Structural + Log + Semantic)
    """
    def __init__(self):
        self.domains = {
            "timeout": ["timeout", "hung", "deadlock", "stall", "wait", "finish"],
            "underflow": ["underflow", "stalled", "empty", "read", "drain"],
            "capacity": ["capacity", "full", "premature", "overflow", "write"],
            "corruption": ["overwrite", "checksum", "mismatch", "corrupt", "data", "payload", "skew"],
            "protocol": ["handshake", "valid", "ready", "response", "ack", "framing", "baud"]
        }

    def compute_log_similarity(self, log_a: str, log_b: str) -> float:
        tokens_a = tokenize_log(log_a)
        tokens_b = tokenize_log(log_b)
        jaccard = jaccard_similarity(tokens_a, tokens_b)
        lev = levenshtein_similarity(log_a, log_b)
        return (jaccard + lev) / 2.0

    def compute_semantic_similarity(self, log_a: str, log_b: str) -> float:
        def extract_domains(text):
            t = text.lower()
            return {dom for dom, kws in self.domains.items() if any(kw in t for kw in kws)}
        doms_a = extract_domains(log_a)
        doms_b = extract_domains(log_b)
        domain_sim = jaccard_similarity(doms_a, doms_b)
        tok_sim = jaccard_similarity(tokenize_log(log_a), tokenize_log(log_b))
        return (domain_sim + tok_sim) / 2.0

    def compute_structural_similarity(self, rtl_a: str, rtl_b: str) -> float:
        ports_a = set(re.findall(r'(?:input|output)\s+(?:wire|reg)?\s*(?:\[.*\])?\s*(\w+)', rtl_a))
        ports_b = set(re.findall(r'(?:input|output)\s+(?:wire|reg)?\s*(?:\[.*\])?\s*(\w+)', rtl_b))
        internals_a = set(re.findall(r'(?:wire|reg)\s*(?:\[.*\])?\s*(\w+)\s*;', rtl_a))
        internals_b = set(re.findall(r'(?:wire|reg)\s*(?:\[.*\])?\s*(\w+)\s*;', rtl_b))
        all_a = ports_a.union(internals_a)
        all_b = ports_b.union(internals_b)
        return (jaccard_similarity(ports_a, ports_b) + jaccard_similarity(all_a, all_b)) / 2.0

    def compute_waveform_similarity(self, vcd_a: str, vcd_b: str, signals: List[str]) -> float:
        map_a = parse_vcd_signals(vcd_a, signals)
        map_b = parse_vcd_signals(vcd_b, signals)
        sig_trans_a = np.array([len(map_a.get(s, [])) for s in signals], dtype=float)
        sig_trans_b = np.array([len(map_b.get(s, [])) for s in signals], dtype=float)
        norm_a, norm_b = np.linalg.norm(sig_trans_a), np.linalg.norm(sig_trans_b)
        if norm_a == 0 or norm_b == 0: return 0.0
        return max(0.0, min(1.0, float(np.dot(sig_trans_a, sig_trans_b) / (norm_a * norm_b))))

    def compute_composite_similarity(self, vcd_a: str, vcd_b: str, rtl_a: str, rtl_b: str,
                                     log_a: str, log_b: str, signals: List[str]) -> float:
        wf_sim = self.compute_waveform_similarity(vcd_a, vcd_b, signals)
        struct_sim = self.compute_structural_similarity(rtl_a, rtl_b)
        log_sim = self.compute_log_similarity(log_a, log_b)
        sem_sim = self.compute_semantic_similarity(log_a, log_b)
        return 0.40 * wf_sim + 0.20 * struct_sim + 0.20 * log_sim + 0.20 * sem_sim
