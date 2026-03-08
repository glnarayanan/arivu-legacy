"""Search domain router -- hybrid BM25 + semantic + entity search."""

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.database import get_database
from app.core.dependencies import get_current_user, get_user_identifier, limiter
from app.services.ai_service import generate_embedding
from app.services.search_utils import (
    tokenize_text,
    calculate_bm25_score,
    calculate_entity_boost,
    reciprocal_rank_fusion,
    detect_query_type,
    get_adaptive_weights,
)

router = APIRouter(tags=["search"])


@router.get("/search")
@limiter.limit("30/minute")  # IP-based rate limiting
@limiter.limit("10/minute", key_func=get_user_identifier)  # User-based rate limiting (PERF-04)
async def hybrid_search(
    request: Request,  # Required for slowapi rate limiting
    query: str,
    limit: int = 20,
    use_semantic: bool = True,
    use_keyword: bool = True,
    domain: Optional[str] = None,
    collection_id: Optional[str] = None,
    read_status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Enhanced hybrid search using BM25 + Semantic + Entity boosting with RRF fusion.

    Improvements over basic hybrid:
    1. BM25 for proper lexical ranking (not just substring matching)
    2. Reciprocal Rank Fusion for robust score combination
    3. Adaptive weighting based on query type
    4. Entity/concept graph boosting
    5. Adaptive semantic thresholds
    """
    import numpy as np

    db = get_database()

    if not query or len(query.strip()) < 2:
        raise HTTPException(
            status_code=400, detail="Query must be at least 2 characters"
        )
    if len(query.encode("utf-8")) > 10240:  # PERF-01: 10KB max query
        raise HTTPException(
            status_code=400, detail="Query too large (max 10KB)"
        )

    # Cap limit parameter
    limit = min(limit, 100)  # PERF-01: Cap at 100 results

    query_lower = query.lower().strip()
    query_tokens = tokenize_text(query)
    user_id = current_user["id"]

    # Detect query type for adaptive weighting
    query_type = detect_query_type(query)
    semantic_weight, keyword_weight = get_adaptive_weights(query_type)

    # Build base query with filters
    base_query = {"user_id": user_id}

    if domain:
        base_query["domain"] = domain

    if read_status == "read":
        base_query["read_status"] = True
    elif read_status == "unread":
        base_query["read_status"] = False

    if collection_id:
        collection = await db.collections.find_one(
            {"id": collection_id}, {"_id": 0, "bookmark_ids": 1}
        )
        if collection:
            base_query["id"] = {"$in": collection.get("bookmark_ids", [])}

    # Projection for candidates
    projection = {
        "_id": 0,
        "id": 1,
        "url": 1,
        "title": 1,
        "description": 1,
        "domain": 1,
        "thumbnail": 1,
        "favicon": 1,
        "reading_time": 1,
        "read_status": 1,
        "created_at": 1,
        "embedding": 1,
        "entities": 1,
        "concepts": 1,
        "text_content": 1,  # For BM25 scoring
    }

    # Fetch candidates (increased limit for better reranking)
    candidate_limit = min(500, limit * 25)
    all_candidates = await db.bookmarks.find(
        base_query, projection
    ).limit(candidate_limit).to_list(None)

    if not all_candidates:
        return {
            "results": [],
            "query": query,
            "total": 0,
            "search_mode": {"semantic": use_semantic, "keyword": use_keyword},
            "message": "No bookmarks found matching filters.",
        }

    # ========== BM25 SCORING ==========
    # Build document corpus for BM25
    doc_tokens_map = {}
    all_doc_lengths = []
    doc_freq = {}  # Term -> number of documents containing it

    for bookmark in all_candidates:
        # Combine searchable text fields (weighted by importance)
        title = bookmark.get("title") or ""
        description = bookmark.get("description") or ""
        text_content = (bookmark.get("text_content") or "")[:2000]  # Limit content
        entities = " ".join(bookmark.get("entities", []))
        concepts = " ".join(bookmark.get("concepts", []))

        # Weight title more by repeating it
        combined = f"{title} {title} {title} {description} {entities} {concepts} {text_content}"
        tokens = tokenize_text(combined)

        doc_tokens_map[bookmark["id"]] = tokens
        all_doc_lengths.append(len(tokens))

        # Count document frequency for each unique term
        for term in set(tokens):
            doc_freq[term] = doc_freq.get(term, 0) + 1

    avg_doc_len = sum(all_doc_lengths) / len(all_doc_lengths) if all_doc_lengths else 1.0
    total_docs = len(all_candidates)

    # Calculate BM25 scores
    bm25_scores = []
    for bookmark in all_candidates:
        doc_tokens = doc_tokens_map.get(bookmark["id"], [])
        score = calculate_bm25_score(
            query_tokens, doc_tokens, doc_freq, avg_doc_len, total_docs
        )
        if score > 0:
            bm25_scores.append((bookmark["id"], score))

    # Sort for ranking
    bm25_ranked = sorted(bm25_scores, key=lambda x: x[1], reverse=True)

    # ========== SEMANTIC SCORING ==========
    semantic_scores = []
    query_embedding = None

    if use_semantic and len(query.strip()) >= 3:
        query_embedding = await generate_embedding(
            query, min_length=3, task_type="retrieval_query"
        )
        if not query_embedding:
            logger.warning(
                f"Semantic embedding failed for query, falling back to keyword-only"
            )
            use_semantic = False  # Graceful degradation (REL-03)

    if query_embedding:
        def dot_product_similarity(vec1, vec2):
            return float(np.dot(vec1, vec2))

        for bookmark in all_candidates:
            if bookmark.get("embedding"):
                sim = dot_product_similarity(query_embedding, bookmark["embedding"])
                semantic_scores.append((bookmark["id"], sim))

    semantic_ranked = sorted(semantic_scores, key=lambda x: x[1], reverse=True)

    # Calculate adaptive semantic threshold
    if semantic_scores:
        scores_only = [s[1] for s in semantic_scores]
        mean_score = sum(scores_only) / len(scores_only)
        std_score = (sum((s - mean_score) ** 2 for s in scores_only) / len(scores_only)) ** 0.5
        adaptive_threshold = max(0.10, mean_score - std_score)
    else:
        adaptive_threshold = 0.15

    # ========== ENTITY BOOSTING ==========
    # Build entity IDF
    entity_counts = {}
    for bookmark in all_candidates:
        for entity in bookmark.get("entities", []) + bookmark.get("concepts", []):
            entity_lower = entity.lower()
            entity_counts[entity_lower] = entity_counts.get(entity_lower, 0) + 1

    entity_idf = {
        e: math.log((total_docs + 1) / (count + 1))
        for e, count in entity_counts.items()
    }

    entity_scores = []
    for bookmark in all_candidates:
        all_doc_entities = bookmark.get("entities", []) + bookmark.get("concepts", [])
        boost = calculate_entity_boost(query_tokens, all_doc_entities, entity_idf)
        if boost > 0:
            entity_scores.append((bookmark["id"], boost))

    entity_ranked = sorted(entity_scores, key=lambda x: x[1], reverse=True)

    # ========== RRF FUSION ==========
    ranked_lists = []
    if use_keyword and bm25_ranked:
        ranked_lists.append(bm25_ranked[:100])
    if use_semantic and semantic_ranked:
        ranked_lists.append(semantic_ranked[:100])
    if entity_ranked:
        ranked_lists.append(entity_ranked[:100])

    if not ranked_lists:
        return {
            "results": [],
            "query": query,
            "total": 0,
            "search_mode": {"semantic": use_semantic, "keyword": use_keyword},
            "message": "No matching bookmarks found.",
        }

    rrf_scores = reciprocal_rank_fusion(ranked_lists)

    # Build lookup maps
    bookmark_map = {b["id"]: b for b in all_candidates}
    bm25_map = {item[0]: item[1] for item in bm25_scores}
    semantic_map = {item[0]: item[1] for item in semantic_scores}
    entity_map = {item[0]: item[1] for item in entity_scores}

    # ========== FINAL RANKING ==========
    results = []
    for doc_id, rrf_score in rrf_scores.items():
        sem_score = semantic_map.get(doc_id, 0.0)
        bm25_score_val = bm25_map.get(doc_id, 0.0)
        entity_score_val = entity_map.get(doc_id, 0.0)

        # Apply semantic threshold for semantic-only mode
        if use_semantic and not use_keyword and sem_score < adaptive_threshold:
            continue

        # Skip if no meaningful scores
        if rrf_score <= 0:
            continue

        bookmark = bookmark_map[doc_id].copy()
        bookmark.pop("embedding", None)
        bookmark.pop("text_content", None)

        # Normalize BM25 for display (0-1 scale based on max)
        max_bm25 = max((s[1] for s in bm25_scores), default=1.0)
        normalized_bm25 = bm25_score_val / max_bm25 if max_bm25 > 0 else 0.0

        bookmark["relevance_score"] = round(rrf_score, 4)
        bookmark["keyword_score"] = round(normalized_bm25, 4)
        bookmark["semantic_score"] = round(sem_score, 4) if sem_score else None
        bookmark["entity_score"] = round(entity_score_val, 4) if entity_score_val else None

        results.append(bookmark)

    # Sort by RRF score
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    top_results = results[:limit]

    # Fetch AI summaries for results
    if top_results:
        bookmark_ids = [b["id"] for b in top_results]
        summaries = await db.ai_summaries.find(
            {"bookmark_id": {"$in": bookmark_ids}}, {"_id": 0}
        ).to_list(None)
        summary_map = {s["bookmark_id"]: s for s in summaries}

        for bookmark in top_results:
            summary = summary_map.get(bookmark["id"])
            if summary:
                bookmark["ai_summary"] = summary

    message = None
    if not top_results:
        message = "No matching bookmarks found. Try different search terms."

    return {
        "results": top_results,
        "query": query,
        "total": len(top_results),
        "query_type": query_type,
        "adaptive_threshold": round(adaptive_threshold, 4),
        "search_mode": {
            "semantic": use_semantic,
            "keyword": use_keyword,
            "semantic_weight": semantic_weight,
            "keyword_weight": keyword_weight,
        },
        "message": message,
    }
