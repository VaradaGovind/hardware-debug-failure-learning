import re
from typing import Dict, Any, List

def tokenize_log(log_text: str) -> set:
    """Extracts alphanumeric tokens from a failure log message."""
    clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', log_text.lower())
    tokens = set(clean.split())
    return {t for t in tokens if len(t) > 1}

def jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union if union > 0 else 0.0

def levenshtein_similarity(str_a: str, str_b: str) -> float:
    """Normalized Levenshtein similarity between two strings."""
    s1, s2 = str_a.strip().lower(), str_b.strip().lower()
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
        
    len1, len2 = len(s1), len(s2)
    matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    for i in range(len1 + 1):
        matrix[i][0] = i
    for j in range(len2 + 1):
        matrix[0][j] = j
        
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost
            )
            
    dist = matrix[len1][len2]
    max_len = max(len1, len2)
    return 1.0 - (dist / max_len) if max_len > 0 else 1.0

class SimilarityBaselines:
    """
    Evaluates ordinary similarity baselines for failure matching:
    - Baseline A: Log / Symptom Similarity
    - Baseline B: RTL Structural Similarity
    - Baseline C: Semantic Keyword Similarity
    """
    def __init__(self):
        pass

    def compute_log_similarity(self, log_a: str, log_b: str) -> Dict[str, float]:
        tokens_a = tokenize_log(log_a)
        tokens_b = tokenize_log(log_b)
        
        jaccard = jaccard_similarity(tokens_a, tokens_b)
        lev = levenshtein_similarity(log_a, log_b)
        
        return {
            "token_jaccard": jaccard,
            "levenshtein": lev,
            "score": (jaccard + lev) / 2.0
        }

    def compute_structural_similarity(self, rtl_content_a: str, rtl_content_b: str) -> Dict[str, float]:
        ports_a = set(re.findall(r'(?:input|output)\s+(?:wire|reg)?\s*(?:\[.*\])?\s*(\w+)', rtl_content_a))
        ports_b = set(re.findall(r'(?:input|output)\s+(?:wire|reg)?\s*(?:\[.*\])?\s*(\w+)', rtl_content_b))
        
        internals_a = set(re.findall(r'(?:wire|reg)\s*(?:\[.*\])?\s*(\w+)\s*;', rtl_content_a))
        internals_b = set(re.findall(r'(?:wire|reg)\s*(?:\[.*\])?\s*(\w+)\s*;', rtl_content_b))
        
        all_a = ports_a.union(internals_a)
        all_b = ports_b.union(internals_b)
        
        port_overlap = jaccard_similarity(ports_a, ports_b)
        signal_overlap = jaccard_similarity(all_a, all_b)
        
        return {
            "port_overlap": port_overlap,
            "signal_overlap": signal_overlap,
            "score": (port_overlap + signal_overlap) / 2.0
        }

    def compute_semantic_similarity(self, symptom_a: str, symptom_b: str) -> Dict[str, float]:
        domains = {
            "underflow": ["underflow", "stalled", "empty", "read"],
            "capacity": ["capacity", "full", "premature", "overflow"],
            "corruption": ["overwrite", "checksum", "mismatch", "corrupt", "data"]
        }
        
        def extract_domain(symptom_str):
            s = symptom_str.lower()
            found = set()
            for dom, keywords in domains.items():
                if any(kw in s for kw in keywords):
                    found.add(dom)
            return found
            
        doms_a = extract_domain(symptom_a)
        doms_b = extract_domain(symptom_b)
        
        domain_sim = jaccard_similarity(doms_a, doms_b)
        token_sim = jaccard_similarity(tokenize_log(symptom_a), tokenize_log(symptom_b))
        
        return {
            "domain_overlap": domain_sim,
            "token_overlap": token_sim,
            "score": (domain_sim + token_sim) / 2.0
        }
