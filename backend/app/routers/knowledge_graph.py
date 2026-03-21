"""
Knowledge graph router - extracted from server.py (Phase 6, Plan 03).

Provides knowledge graph exploration, semantic search within the graph,
query expansion using related concepts, and embedding regeneration.
"""

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.core.database import get_database
from app.core.dependencies import get_current_user, get_user_identifier, limiter
from app.services.ai_service import (
    extract_entities_and_concepts,
    generate_embedding,
)
from app.services.search_utils import calculate_entity_boost, tokenize_text

UTC = timezone.utc

logger = logging.getLogger(__name__)

router = APIRouter(tags=["knowledge-graph"])

# Minimum semantic similarity threshold for search results
MIN_SEMANTIC_SCORE = 0.3


@router.get("/knowledge-graph/explore")
async def explore_knowledge_graph(limit: int = 50, current_user: dict = Depends(get_current_user)):
    """
    Explore the user's knowledge graph with enhanced graph metrics.

    Features:
    - Entity/concept importance ranking (by connection count)
    - Bookmark similarity clusters
    - Co-occurrence relationships
    """
    import numpy as np

    db = get_database()

    # Get all bookmarks with embeddings
    bookmarks = (
        await db.bookmarks.find(
            {
                "user_id": current_user["id"],
                "embedding": {"$exists": True, "$ne": None},
            },
            {
                "_id": 0,
                "id": 1,
                "title": 1,
                "description": 1,
                "url": 1,
                "domain": 1,
                "favicon": 1,
                "thumbnail": 1,
                "created_at": 1,
                "entities": 1,
                "concepts": 1,
                "embedding": 1,
            },
        )
        .limit(limit)
        .to_list(None)
    )

    if not bookmarks:
        return {
            "bookmarks": [],
            "entities": [],
            "concepts": [],
            "concept_connections": {},
            "entity_connections": {},
            "entity_importance": {},
            "concept_importance": {},
            "related_bookmarks": {},
            "total_bookmarks": 0,
            "total_entities": 0,
            "total_concepts": 0,
        }

    # Extract all unique entities and concepts with counts
    entity_counts: dict[str, int] = {}
    concept_counts: dict[str, int] = {}

    for bookmark in bookmarks:
        for entity in bookmark.get("entities", []):
            entity_counts[entity] = entity_counts.get(entity, 0) + 1
        for concept in bookmark.get("concepts", []):
            concept_counts[concept] = concept_counts.get(concept, 0) + 1

    # Build concept/entity connections
    concept_connections: dict[str, list[str]] = {}
    entity_connections: dict[str, list[str]] = {}

    for bookmark in bookmarks:
        bookmark_id = bookmark["id"]

        for concept in bookmark.get("concepts", []):
            if concept not in concept_connections:
                concept_connections[concept] = []
            concept_connections[concept].append(bookmark_id)

        for entity in bookmark.get("entities", []):
            if entity not in entity_connections:
                entity_connections[entity] = []
            entity_connections[entity].append(bookmark_id)

    # Calculate entity/concept importance (IDF-weighted connection score)
    total_docs = len(bookmarks)

    def calculate_importance(count: int) -> float:
        # Higher count = more connected = more important, but with diminishing returns
        # Also penalize very common terms (like TF-IDF logic)
        if count == 0:
            return 0.0
        idf = math.log((total_docs + 1) / (count + 1)) + 1
        connection_score = math.log(count + 1)
        return round(idf * connection_score, 3)

    entity_importance = {entity: calculate_importance(count) for entity, count in entity_counts.items()}
    concept_importance = {concept: calculate_importance(count) for concept, count in concept_counts.items()}

    # Find related bookmarks using embedding similarity
    related_bookmarks: dict[str, list[tuple]] = {}
    embedding_map = {b["id"]: b.get("embedding") for b in bookmarks if b.get("embedding")}

    if len(embedding_map) > 1:

        def dot_product_similarity(vec1, vec2):
            return float(np.dot(vec1, vec2))

        # For each bookmark, find top 3 most similar
        for bookmark in bookmarks:
            if not bookmark.get("embedding"):
                continue

            similarities = []
            for other in bookmarks:
                if other["id"] == bookmark["id"] or not other.get("embedding"):
                    continue
                sim = dot_product_similarity(bookmark["embedding"], other["embedding"])
                if sim > 0.5:  # Only include reasonably similar
                    similarities.append((other["id"], round(sim, 3)))

            # Sort and take top 3
            similarities.sort(key=lambda x: x[1], reverse=True)
            if similarities:
                related_bookmarks[bookmark["id"]] = similarities[:3]

    # Remove embeddings from response to reduce payload
    for bookmark in bookmarks:
        bookmark.pop("embedding", None)

    # Sort entities/concepts by importance for response
    top_entities = sorted(entity_importance.items(), key=lambda x: x[1], reverse=True)[:50]
    top_concepts = sorted(concept_importance.items(), key=lambda x: x[1], reverse=True)[:50]

    return {
        "bookmarks": bookmarks,
        "entities": [e[0] for e in top_entities],
        "concepts": [c[0] for c in top_concepts],
        "concept_connections": concept_connections,
        "entity_connections": entity_connections,
        "entity_importance": dict(top_entities),
        "concept_importance": dict(top_concepts),
        "related_bookmarks": related_bookmarks,
        "total_bookmarks": len(bookmarks),
        "total_entities": len(entity_counts),
        "total_concepts": len(concept_counts),
    }


@router.get("/knowledge-graph/search")
@limiter.limit("30/minute")  # IP-based rate limiting
@limiter.limit("10/minute", key_func=get_user_identifier)  # User-based rate limiting (PERF-04)
async def semantic_search(
    request: Request,  # Required for slowapi rate limiting
    query: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
):
    """
    Enhanced semantic search using adaptive thresholds and entity boosting.
    Uses RRF to combine semantic similarity with entity overlap.
    """
    import numpy as np

    db = get_database()

    if not query or len(query.strip()) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")
    if len(query.encode("utf-8")) > 10240:  # PERF-01: 10KB max query
        raise HTTPException(status_code=400, detail="Query too large (max 10KB)")

    # Cap limit parameter
    limit = min(limit, 50)  # PERF-01: Cap at 50 results

    # Generate embedding for the search query
    query_embedding = await generate_embedding(query, min_length=3, task_type="retrieval_query")

    if not query_embedding:
        logger.warning(f"Failed to generate query embedding for: {query[:100]}")
        return {"results": [], "message": "Semantic search temporarily unavailable"}

    # Get all user's bookmarks with embeddings
    all_bookmarks = await db.bookmarks.find(
        {"user_id": current_user["id"], "embedding": {"$exists": True, "$ne": None}},
        {
            "_id": 0,
            "id": 1,
            "title": 1,
            "description": 1,
            "url": 1,
            "favicon": 1,
            "domain": 1,
            "thumbnail": 1,
            "created_at": 1,
            "embedding": 1,
            "entities": 1,
            "concepts": 1,
        },
    ).to_list(None)

    if not all_bookmarks:
        return {"results": [], "message": "No bookmarks with semantic data available"}

    def dot_product_similarity(vec1, vec2):
        return float(np.dot(vec1, vec2))

    # Calculate semantic scores for all bookmarks
    semantic_scores = []
    for bookmark in all_bookmarks:
        if bookmark.get("embedding"):
            sim = dot_product_similarity(query_embedding, bookmark["embedding"])
            semantic_scores.append((bookmark["id"], sim, bookmark))

    if not semantic_scores:
        return {"results": [], "message": "No bookmarks with embeddings"}

    # Calculate adaptive threshold based on score distribution
    scores_only = [s[1] for s in semantic_scores]
    if scores_only:
        mean_score = sum(scores_only) / len(scores_only)
        std_score = (sum((s - mean_score) ** 2 for s in scores_only) / len(scores_only)) ** 0.5
        # Adaptive threshold: at least 0.10, or mean - 1 std
        adaptive_threshold = max(0.10, mean_score - std_score)
    else:
        adaptive_threshold = 0.15

    # Build entity IDF for boosting
    entity_counts: dict[str, int] = {}
    for bookmark in all_bookmarks:
        for entity in bookmark.get("entities", []) + bookmark.get("concepts", []):
            entity_lower = entity.lower()
            entity_counts[entity_lower] = entity_counts.get(entity_lower, 0) + 1

    total_docs = len(all_bookmarks)
    entity_idf = {e: math.log((total_docs + 1) / (count + 1)) for e, count in entity_counts.items()}

    # Extract entities from query (simple approach: use query tokens as potential entities)
    query_tokens = tokenize_text(query)

    # Build ranked lists for RRF
    from app.services.search_utils import reciprocal_rank_fusion

    # List 1: Semantic similarity
    semantic_ranked = sorted(semantic_scores, key=lambda x: x[1], reverse=True)[:100]

    # List 2: Entity/concept overlap (using query tokens as entity proxies)
    entity_scores = []
    for bookmark in all_bookmarks:
        all_doc_entities = bookmark.get("entities", []) + bookmark.get("concepts", [])
        boost = calculate_entity_boost(query_tokens, all_doc_entities, entity_idf)
        if boost > 0:
            entity_scores.append((bookmark["id"], boost, bookmark))
    entity_ranked = sorted(entity_scores, key=lambda x: x[1], reverse=True)[:100]

    # RRF fusion
    rrf_scores = reciprocal_rank_fusion(
        [
            [(item[0], item[1]) for item in semantic_ranked],
            [(item[0], item[1]) for item in entity_ranked],
        ]
    )

    # Build result set
    bookmark_map = {b["id"]: b for b in all_bookmarks}
    semantic_map = {item[0]: item[1] for item in semantic_scores}
    entity_map = {item[0]: item[1] for item in entity_scores}

    results = []
    for doc_id, rrf_score in rrf_scores.items():
        sem_score = semantic_map.get(doc_id, 0.0)

        # Apply adaptive threshold
        if sem_score < adaptive_threshold:
            continue

        bookmark = bookmark_map[doc_id].copy()
        bookmark.pop("embedding", None)
        bookmark["similarity_score"] = round(sem_score, 4)
        bookmark["entity_score"] = round(entity_map.get(doc_id, 0.0), 4)
        bookmark["rrf_score"] = round(rrf_score, 4)
        results.append(bookmark)

    # Sort by RRF score
    results.sort(key=lambda x: x["rrf_score"], reverse=True)
    top_results = results[:limit]

    message = None
    if not top_results:
        message = "No strongly matching bookmarks found. Try different search terms."

    return {
        "results": top_results,
        "query": query,
        "adaptive_threshold": round(adaptive_threshold, 4),
        "message": message,
    }


@router.get("/knowledge-graph/expand-query")
async def expand_query(
    query: str,
    max_expansions: int = 10,
    current_user: dict = Depends(get_current_user),
):
    """
    Expand a search query using the knowledge graph.

    Returns related entities and concepts that could improve search results.
    Uses:
    1. Direct entity/concept matches in user's bookmarks
    2. Co-occurring entities (appear in same bookmarks)
    3. Embedding similarity for semantic expansions
    """
    db = get_database()

    if not query or len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    if len(query.encode("utf-8")) > 10240:  # PERF-01: 10KB max query
        raise HTTPException(status_code=400, detail="Query too large (max 10KB)")

    query_tokens = set(tokenize_text(query))

    # Get user's entities and concepts with their bookmark associations
    all_bookmarks = (
        await db.bookmarks.find(
            {"user_id": current_user["id"]},
            {
                "_id": 0,
                "id": 1,
                "entities": 1,
                "concepts": 1,
                "embedding": 1,
            },
        )
        .limit(500)
        .to_list(None)
    )

    if not all_bookmarks:
        return {
            "query": query,
            "expansions": [],
            "related_entities": [],
            "related_concepts": [],
        }

    # Build entity/concept co-occurrence map
    entity_to_bookmarks: dict[str, set] = {}
    concept_to_bookmarks: dict[str, set] = {}

    for bookmark in all_bookmarks:
        bid = bookmark["id"]
        for entity in bookmark.get("entities", []):
            if entity not in entity_to_bookmarks:
                entity_to_bookmarks[entity] = set()
            entity_to_bookmarks[entity].add(bid)
        for concept in bookmark.get("concepts", []):
            if concept not in concept_to_bookmarks:
                concept_to_bookmarks[concept] = set()
            concept_to_bookmarks[concept].add(bid)

    # Find direct matches (entities/concepts containing query terms)
    direct_entity_matches = []
    direct_concept_matches = []

    for entity in entity_to_bookmarks.keys():
        entity_lower = entity.lower()
        if any(token in entity_lower for token in query_tokens):
            direct_entity_matches.append(entity)

    for concept in concept_to_bookmarks.keys():
        concept_lower = concept.lower()
        if any(token in concept_lower for token in query_tokens):
            direct_concept_matches.append(concept)

    # Find co-occurring entities/concepts (appear in same bookmarks as matched ones)
    matched_bookmark_ids = set()
    for entity in direct_entity_matches:
        matched_bookmark_ids.update(entity_to_bookmarks.get(entity, set()))
    for concept in direct_concept_matches:
        matched_bookmark_ids.update(concept_to_bookmarks.get(concept, set()))

    # Collect co-occurring terms with frequency counts
    cooccur_entities: dict[str, int] = {}
    cooccur_concepts: dict[str, int] = {}

    for bookmark in all_bookmarks:
        if bookmark["id"] in matched_bookmark_ids:
            for entity in bookmark.get("entities", []):
                if entity not in direct_entity_matches:
                    cooccur_entities[entity] = cooccur_entities.get(entity, 0) + 1
            for concept in bookmark.get("concepts", []):
                if concept not in direct_concept_matches:
                    cooccur_concepts[concept] = cooccur_concepts.get(concept, 0) + 1

    # Sort by frequency and take top items
    top_cooccur_entities = sorted(cooccur_entities.items(), key=lambda x: x[1], reverse=True)[:max_expansions]
    top_cooccur_concepts = sorted(cooccur_concepts.items(), key=lambda x: x[1], reverse=True)[:max_expansions]

    # Build expansion list (mix of direct and co-occurring)
    expansions = []

    # Add direct matches first (high relevance)
    for entity in direct_entity_matches[:5]:
        expansions.append(
            {
                "term": entity,
                "type": "entity",
                "source": "direct_match",
                "relevance": 1.0,
            }
        )
    for concept in direct_concept_matches[:5]:
        expansions.append(
            {
                "term": concept,
                "type": "concept",
                "source": "direct_match",
                "relevance": 1.0,
            }
        )

    # Add co-occurring terms (medium relevance)
    for entity, count in top_cooccur_entities[:5]:
        expansions.append(
            {
                "term": entity,
                "type": "entity",
                "source": "co_occurrence",
                "relevance": round(min(count / 5.0, 0.8), 2),
            }
        )
    for concept, count in top_cooccur_concepts[:5]:
        expansions.append(
            {
                "term": concept,
                "type": "concept",
                "source": "co_occurrence",
                "relevance": round(min(count / 5.0, 0.8), 2),
            }
        )

    # Sort by relevance and limit
    expansions.sort(key=lambda x: x["relevance"], reverse=True)

    return {
        "query": query,
        "expansions": expansions[:max_expansions],
        "related_entities": direct_entity_matches[:10] + [e[0] for e in top_cooccur_entities[:5]],
        "related_concepts": direct_concept_matches[:10] + [c[0] for c in top_cooccur_concepts[:5]],
        "total_entities_searched": len(entity_to_bookmarks),
        "total_concepts_searched": len(concept_to_bookmarks),
    }


@router.post("/knowledge-graph/regenerate-embeddings")
@limiter.limit("3/hour")  # Very expensive batch operation
@limiter.limit("1/hour", key_func=get_user_identifier)  # User-based rate limiting (PERF-04)
async def regenerate_embeddings(
    request: Request,  # Required for slowapi rate limiting
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Regenerate embeddings for all bookmarks that don't have them yet.
    This is a background task that processes bookmarks asynchronously.
    """
    db = get_database()

    # Count bookmarks that need embeddings
    needs_embedding_count = await db.bookmarks.count_documents(
        {
            "user_id": current_user["id"],
            "text_content": {"$exists": True, "$ne": None},
            "$or": [{"embedding": {"$exists": False}}, {"embedding": None}],
        }
    )

    if needs_embedding_count == 0:
        return {
            "message": "All bookmarks already have embeddings",
            "processed": 0,
            "status": "completed",
        }

    # Capture user_id for background task (current_user won't be available)
    user_id = current_user["id"]

    # Start background processing
    async def process_embeddings():
        # Get own db reference inside background task
        bg_db = get_database()

        bookmarks = await bg_db.bookmarks.find(
            {
                "user_id": user_id,
                "text_content": {"$exists": True, "$ne": None},
                "$or": [{"embedding": {"$exists": False}}, {"embedding": None}],
            },
            {"_id": 0, "id": 1, "text_content": 1, "title": 1, "description": 1},
        ).to_list(None)

        processed = 0
        for bookmark in bookmarks:
            try:
                text_content = bookmark.get("text_content", "")
                if text_content and len(text_content.strip()) >= 50:
                    embedding = await generate_embedding(
                        text_content,
                        bookmark.get("title", ""),
                        bookmark.get("description", ""),
                    )

                    if embedding:
                        # Get AI summary for entity/concept extraction
                        ai_summary = await bg_db.ai_summaries.find_one({"bookmark_id": bookmark["id"]}, {"_id": 0})
                        entities, concepts = await extract_entities_and_concepts(text_content, ai_summary)

                        update_data = {
                            "embedding": embedding,
                            "embedding_model": "text-embedding-004",
                            "updated_at": datetime.now(UTC).isoformat(),
                        }

                        if entities:
                            update_data["entities"] = entities
                        if concepts:
                            update_data["concepts"] = concepts

                        await bg_db.bookmarks.update_one({"id": bookmark["id"]}, {"$set": update_data})
                        processed += 1
                        logger.info(f"Generated embedding for bookmark {bookmark['id']} ({processed}/{len(bookmarks)})")

            except Exception:
                logger.exception(f"Error generating embedding for bookmark {bookmark.get('id')}")

        logger.info(f"Completed embedding regeneration: {processed}/{len(bookmarks)} processed")

    background_tasks.add_task(process_embeddings)

    return {
        "message": f"Started regenerating embeddings for {needs_embedding_count} bookmarks",
        "queued": needs_embedding_count,
        "status": "processing",
    }
UTC = timezone.utc
