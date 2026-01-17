# Semantic Search & Knowledge Graph Quality Improvements

**Status:** ✅ Implemented  
**Created:** January 17, 2026  
**Completed:** January 17, 2026  
**Priority:** High (Quality over new features)

---

## Executive Summary

This document outlines improvements to enhance the accuracy and quality of semantic search and knowledge graph features. The current implementation has several issues that impact user experience and search relevance.

---

## Current Issues Identified

### 1. Dashboard Search is Keyword-Only
- Lines 1833-1840 in `server.py` use basic substring matching on title/description
- Does not leverage embeddings for semantic understanding
- Users expect "smart" search in an AI-native app

### 2. Entity Extraction is Primitive  
- Lines 1366-1396 use simple regex for capitalized words
- No actual NLP/NER processing
- Generates noise (e.g., "The", "This") and misses real entities

### 3. Embedding Task Type Mismatch
- Documents use `task_type="retrieval_document"` (correct)
- Queries ALSO use document type (WRONG - should use `retrieval_query`)
- This degrades semantic search quality significantly

### 4. No Hybrid Search
- Pure semantic search may miss exact keyword matches
- Pure keyword search misses conceptual meaning
- Users expect both behaviors combined

### 5. O(n) Similarity Calculation
- Loading ALL embeddings to compute similarity in Python
- Inefficient for users with many bookmarks
- Should use candidate filtering first

### 6. No Minimum Similarity Threshold
- Returns results regardless of actual relevance
- Low-quality matches pollute results

---

## Implementation Plan

### Phase 0: Correctness Fixes (Priority: Critical)

**Estimated Effort:** 1-2 hours

#### 0.1 Fix Query Embedding Task Type
```python
# For documents (at indexing time):
task_type="retrieval_document"

# For queries (at search time):
task_type="retrieval_query"
```

#### 0.2 Normalize Embeddings
- L2-normalize vectors before storage and at query time
- Makes cosine similarity a simple dot product
- Prevents score drift

#### 0.3 Add Minimum Relevance Threshold
- Implement `min_semantic_score = 0.25` (tunable)
- Filter out results below threshold
- Show "No strong matches" UX when nothing qualifies

#### 0.4 Handle Missing Embeddings Gracefully
- Bookmarks without embeddings participate in keyword search only
- Don't contaminate semantic ranking

---

### Phase 1A: Hybrid Search Engine (Priority: High)

**Estimated Effort:** 2-3 hours

#### Create Unified `/api/search` Endpoint
- Inputs: `query`, `user_id`, `limit`, filters, `use_semantic`, `use_keyword`
- Output: ranked bookmarks with debug scores

#### Two-Stage Retrieval
1. **Stage A: MongoDB Text Index Candidate Retrieval**
   - Add text index on: `title`, `description`, `text_content`, `entities`
   - Use `$text` search for top 200 candidates with `textScore`

2. **Stage B: Semantic Rerank**
   - Compute query embedding with `retrieval_query` task type
   - Calculate cosine similarity only for candidates (not all bookmarks)
   - Final score: `0.7 * semantic + 0.3 * normalized_text_score`

#### Unify Dashboard Search
- Replace substring matching (lines 1833-1840) with `/search` endpoint
- Immediate improvement without UI changes

---

### Phase 1B: Entity Extraction Upgrade (Priority: High)

**Estimated Effort:** 2-3 hours

#### Replace Regex with Gemini Structured Extraction
```python
# Prompt for entity extraction
ENTITY_EXTRACTION_PROMPT = """
Extract named entities from this content. Return JSON only:
{
  "entities": [
    {"name": "Entity Name", "type": "person|organization|technology|concept|topic", "confidence": 0.9}
  ]
}
Rules:
- Extract only explicitly mentioned entities
- Maximum 15 entities
- Confidence 0-1 scale
- Types: person, organization, technology, concept, topic
- Ignore common words, months, days
- Prefer canonical names
"""
```

#### Entity Normalization
- Lowercase, trim punctuation, collapse whitespace
- Denylist for false positives: "The", "This", "Read", etc.
- Only persist entities with confidence ≥ 0.6

---

### Phase 2: Knowledge Graph Quality (Priority: Medium)

**Estimated Effort:** 3-4 hours

#### Canonical Entity Storage
- Separate `entities` collection with:
  - `entity_id`, `canonical_name`, `type`, `usage_count`
  - Deduplication across bookmarks

#### Weighted Edges
- Co-occurrence within same bookmark creates edge
- Store: `source_entity_id`, `target_entity_id`, `weight`, `bookmark_ids_sample`
- Decay old edges, boost recent ones

#### De-noising
- Ignore "stop entities" that appear in >X% of bookmarks
- These aren't useful for graph structure

---

## Technical Implementation

### MongoDB Text Index (Phase 1A)
```python
# Create compound text index
await db.bookmarks.create_index([
    ("title", "text"),
    ("description", "text"),
    ("text_content", "text"),
    ("entities", "text"),
    ("concepts", "text")
], name="bookmark_text_search")
```

### Hybrid Search Algorithm (Phase 1A)
```python
async def hybrid_search(query: str, user_id: str, limit: int = 20):
    # Stage A: Keyword candidates
    keyword_results = await db.bookmarks.find(
        {"user_id": user_id, "$text": {"$search": query}},
        {"score": {"$meta": "textScore"}, ...}
    ).sort([("score", {"$meta": "textScore"})]).limit(200).to_list(None)
    
    # Stage B: Semantic rerank
    query_embedding = await generate_embedding(query, task_type="retrieval_query")
    
    for bookmark in keyword_results:
        if bookmark.get("embedding"):
            semantic_score = cosine_similarity(query_embedding, bookmark["embedding"])
            text_score = bookmark.get("score", 0) / max_text_score  # normalize
            bookmark["final_score"] = 0.7 * semantic_score + 0.3 * text_score
        else:
            bookmark["final_score"] = 0.3 * text_score  # keyword only
    
    # Filter by threshold and sort
    results = [b for b in keyword_results if b["final_score"] >= MIN_SCORE]
    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results[:limit]
```

---

## Success Metrics

1. **Search Relevance**: Top-5 results should be relevant 90%+ of the time
2. **Entity Quality**: Extracted entities should be meaningful (not common words)
3. **Performance**: Search should complete in <500ms for users with 1000+ bookmarks
4. **User Satisfaction**: Reduced "no results" frustration

---

## Rollout Plan

1. **Phase 0**: Deploy fixes silently (no breaking changes)
2. **Phase 1A**: Add `/api/search` alongside existing endpoints, then migrate
3. **Phase 1B**: Run entity re-extraction in background for existing bookmarks
4. **Phase 2**: Launch improved Knowledge Graph UI

---

## Implementation Summary

The following improvements were implemented on January 17, 2026:

### ✅ Phase 0: Correctness Fixes
1. **Fixed query embedding task type** - Now uses `retrieval_query` for search queries (was incorrectly using `retrieval_document`)
2. **L2 normalization** - All embeddings are now normalized, enabling efficient dot product similarity
3. **Minimum similarity threshold** - Added `MIN_SEMANTIC_SCORE = 0.25` to filter low-quality matches
4. **Better error messages** - Returns helpful messages when no strong matches found

### ✅ Phase 1A: Hybrid Search Engine
1. **New `/api/search` endpoint** - Unified hybrid search combining keyword + semantic
2. **Two-stage retrieval** - Keyword candidate filtering → semantic reranking
3. **Configurable weights** - `SEMANTIC_WEIGHT = 0.7`, `KEYWORD_WEIGHT = 0.3`
4. **Improved dashboard search** - Now searches across title, description, URL, and domain

### ✅ Phase 1B: Entity Extraction Upgrade
1. **Gemini-powered extraction** - Replaced regex with structured AI extraction
2. **Entity confidence scoring** - Only entities with confidence ≥ 0.6 are stored
3. **Comprehensive denylist** - Filters common words, months, days, navigation terms
4. **Entity normalization** - Consistent lowercase, trimmed, collapsed whitespace

---

## New API: Hybrid Search

### GET /api/search

Unified search endpoint combining keyword matching and semantic similarity.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | string | required | Search query (min 2 chars) |
| limit | int | 20 | Max results to return |
| use_semantic | bool | true | Enable semantic similarity |
| use_keyword | bool | true | Enable keyword matching |
| domain | string | null | Filter by domain |
| collection_id | string | null | Filter by collection |
| read_status | string | null | "read" or "unread" |

**Response:**
```json
{
  "results": [
    {
      "id": "bookmark_id",
      "title": "Example Title",
      "url": "https://example.com",
      "relevance_score": 0.85,
      "keyword_score": 0.6,
      "semantic_score": 0.95,
      "ai_summary": {...}
    }
  ],
  "query": "machine learning",
  "total": 15,
  "search_mode": {
    "semantic": true,
    "keyword": true
  },
  "message": null
}
```

---

## References

- [Knowledge Graph Documentation](knowledge-graph.md)
- [Backend Server](../../backend/server.py)
- [Google Embedding Documentation](https://ai.google.dev/gemini-api/docs/embeddings)

---

**Last Updated:** January 17, 2026
