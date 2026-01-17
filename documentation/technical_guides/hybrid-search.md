# Hybrid Search

> **One-liner:** Find bookmarks by what they mean, not just the exact words they contain.

## What Is It?

Hybrid Search combines two search approaches:

1. **Keyword Search** — Traditional text matching ("python" finds articles with "python")
2. **Semantic Search** — Meaning-based matching ("python" also finds articles about "programming languages")

The result: You find what you're actually looking for, even if you can't remember the exact words.

## Why It Matters

**Traditional Search Problem:**
- You search "machine learning deployment"
- You miss an article titled "Putting AI Models into Production" (same concept, different words)

**Hybrid Search Solution:**
- Searches for keyword matches AND similar meanings
- Finds both the exact phrase AND conceptually related content

## How It Works (Two-Stage Retrieval)

### Stage 1: Keyword Candidate Retrieval (Fast)

First, we quickly find bookmarks that contain your search words:

```
Search: "react hooks"
         ↓
Checks: title, description, URL, domain, entities, concepts
         ↓
Found: 50 candidates that mention "react" or "hooks"
```

**Keyword Scoring Rules:**
| Match Location | Points |
|----------------|--------|
| Exact title match | 3 points |
| Title contains query | 2 points |
| Description contains query | 1 point |
| URL contains query | 0.5 points |
| Entity/concept contains query | 0.5 points each |

### Stage 2: Semantic Reranking (Smart)

Next, we use AI to understand the meaning:

1. Convert your search query into an embedding
2. Compare it to each candidate's embedding
3. Score by semantic similarity

```
Query Embedding: [0.123, -0.456, 0.789, ...]
                     ↓
Compare to each candidate's embedding
                     ↓
Semantic Score: 0.0 to 1.0 (how similar in meaning)
```

### Stage 3: Combined Scoring

The final score blends both approaches:

```
Final Score = (0.7 × Semantic Score) + (0.3 × Keyword Score)
```

**Why 70/30?** Semantic search captures meaning better, but keyword matches are still important for exact phrases.

## Key Functions Explained

### `hybrid_search(query)`
The main search endpoint that orchestrates everything.

**Parameters:**
- `query` — What you're searching for
- `limit` — How many results (default: 20)
- `use_semantic` — Enable AI meaning matching (default: true)
- `use_keyword` — Enable text matching (default: true)
- `domain` — Filter by website (optional)
- `collection_id` — Search within a collection (optional)

### `generate_embedding(text, task_type)`
Converts text into a meaning vector.

**Important:** Uses different modes for different purposes:
- `task_type="retrieval_query"` — For search queries (what you type)
- `task_type="retrieval_document"` — For bookmarks (what gets indexed)

This distinction helps the AI understand that queries are questions and documents are answers.

### `dot_product_similarity(vec1, vec2)`
Measures how similar two embeddings are.

**How it works:**
1. Both vectors are L2-normalized (made the same length)
2. Dot product is calculated (multiply and sum)
3. Result: -1 to 1 (1 = identical meaning)

## Real-World Examples

### Example 1: Finding Related Content

**Search:** "kubernetes deployment strategies"

**Keyword matches:**
- "Kubernetes Rolling Updates Explained" (contains "kubernetes")
- "Deploy to K8s with Helm Charts" (contains "deploy")

**Semantic matches:**
- "Container Orchestration Best Practices" (conceptually related)
- "Managing Microservices at Scale" (similar topic)

**Final results:** All four appear, ranked by combined relevance.

### Example 2: Conceptual Discovery

**Search:** "startup funding"

**You didn't use these words, but semantic search finds:**
- "How to Raise a Seed Round" (same meaning)
- "Series A Pitching Guide" (related concept)
- "Term Sheet Negotiation" (related topic)

## Minimum Similarity Threshold

Results must score at least **0.25 (25%)** semantic similarity to appear.

This prevents irrelevant content from showing up just because it has a vague connection.

## Technical Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────┐
│  Stage 1: Keyword Candidate Retrieval   │
│  - Text index search across fields      │
│  - Up to 200 candidates                 │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Stage 2: Query Embedding Generation    │
│  - Google text-embedding-004            │
│  - task_type="retrieval_query"          │
│  - L2-normalized vector                 │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Stage 3: Semantic Scoring              │
│  - Dot product with each candidate      │
│  - Filter by MIN_SEMANTIC_SCORE (0.25)  │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Stage 4: Score Combination             │
│  - 70% semantic + 30% keyword           │
│  - Sort by final score                  │
│  - Return top N results                 │
└─────────────────────────────────────────┘
```

## Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| `SEMANTIC_WEIGHT` | 0.7 | Weight given to meaning similarity |
| `KEYWORD_WEIGHT` | 0.3 | Weight given to text matching |
| `MIN_SEMANTIC_SCORE` | 0.25 | Minimum similarity threshold |
| `candidate_limit` | 200 | Max bookmarks to consider |
