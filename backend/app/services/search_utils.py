"""
Search utility functions for hybrid BM25 + semantic + entity search.

Pure scoring and ranking functions with no database or service dependencies.
Used by search router and knowledge graph router.
"""

import math
import re
from typing import Dict, List, Set, Tuple

# BM25 parameters (tuned for bookmark search)
BM25_K1 = 1.2  # Term frequency saturation
BM25_B = 0.75  # Length normalization factor

# RRF fusion constant (typically 20-60, higher = more weight to lower ranks)
RRF_K = 60

# Stopwords for tokenization
SEARCH_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "this",
    "that", "these", "those", "it", "its", "i", "you", "he", "she", "we",
    "they", "what", "which", "who", "whom", "when", "where", "why", "how",
}


def tokenize_text(text: str) -> List[str]:
    """Tokenize text for BM25 scoring."""
    if not text:
        return []
    # Lowercase, split on non-alphanumeric, filter stopwords and short tokens
    tokens = re.findall(r'\b[a-z0-9]+\b', text.lower())
    return [t for t in tokens if t not in SEARCH_STOPWORDS and len(t) > 1]


def calculate_bm25_score(
    query_tokens: List[str],
    doc_tokens: List[str],
    doc_freq: Dict[str, int],
    avg_doc_len: float,
    total_docs: int,
) -> float:
    """
    Calculate BM25 score for a document given a query.

    BM25(d, q) = Sigma IDF(t) * (tf(t,d) * (k1+1)) / (tf(t,d) + k1 * (1 - b + b * |d|/avgdl))
    """
    if not query_tokens or not doc_tokens:
        return 0.0

    doc_len = len(doc_tokens)
    if doc_len == 0 or avg_doc_len == 0:
        return 0.0

    # Count term frequencies in document
    doc_tf = {}
    for token in doc_tokens:
        doc_tf[token] = doc_tf.get(token, 0) + 1

    score = 0.0
    for term in query_tokens:
        if term not in doc_tf:
            continue

        tf = doc_tf[term]
        df = doc_freq.get(term, 1)  # Document frequency of term

        # IDF with smoothing: log((N - df + 0.5) / (df + 0.5))
        idf = max(0.0, math.log((total_docs - df + 0.5) / (df + 0.5)))

        # BM25 term score
        numerator = tf * (BM25_K1 + 1)
        denominator = tf + BM25_K1 * (1 - BM25_B + BM25_B * (doc_len / avg_doc_len))

        score += idf * (numerator / denominator)

    return score


def calculate_entity_boost(
    query_entities: List[str],
    doc_entities: List[str],
    entity_idf: Dict[str, float],
) -> float:
    """
    Calculate IDF-weighted entity overlap score.
    Boosts bookmarks that share entities/concepts with the query.
    """
    if not query_entities or not doc_entities:
        return 0.0

    query_set = {e.lower() for e in query_entities}
    doc_set = {e.lower() for e in doc_entities}

    overlap = query_set & doc_set
    if not overlap:
        return 0.0

    # Sum IDF weights for matching entities
    score = sum(entity_idf.get(e, 1.0) for e in overlap)
    return score


def reciprocal_rank_fusion(
    ranked_lists: List[List[tuple]],
    k: int = RRF_K,
) -> Dict[str, float]:
    """
    Combine multiple ranked lists using Reciprocal Rank Fusion.

    RRF(d) = Sigma 1 / (k + rank_l(d)) for each list l

    Args:
        ranked_lists: List of [(doc_id, score), ...] sorted by score descending
        k: Fusion constant (default 60)

    Returns:
        Dict of doc_id -> RRF score
    """
    rrf_scores = {}

    for ranked_list in ranked_lists:
        for rank, (doc_id, _score) in enumerate(ranked_list, start=1):
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
            rrf_scores[doc_id] += 1.0 / (k + rank)

    return rrf_scores


def detect_query_type(query: str) -> str:
    """
    Detect query type to adapt search weighting.

    Returns: 'exact', 'technical', or 'semantic'
    """
    # Quoted phrases indicate exact match desire
    if '"' in query or "'" in query:
        return 'exact'

    # Technical patterns: URLs, code-like syntax, file paths
    if re.search(r'[/\\._:@#]+', query) or re.search(r'\b\d+\.\d+\b', query):
        return 'technical'

    # Short queries (1-2 words) tend to be keyword-focused
    word_count = len(query.split())
    if word_count <= 2:
        return 'exact'

    # Longer natural language queries benefit from semantic
    return 'semantic'


def get_adaptive_weights(query_type: str) -> tuple:
    """
    Get adaptive semantic/keyword weights based on query type.

    Returns: (semantic_weight, keyword_weight)
    """
    if query_type == 'exact':
        return (0.3, 0.7)  # Favor keyword matching
    elif query_type == 'technical':
        return (0.4, 0.6)  # Balanced with keyword edge
    else:  # semantic
        return (0.75, 0.25)  # Favor semantic understanding
