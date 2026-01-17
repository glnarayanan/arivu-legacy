# Knowledge Graph

> **One-liner:** Your bookmarks aren't isolated — they're interconnected nodes in a web of knowledge.

## What Is It?

The Knowledge Graph is a visual and data-driven way to see how all your saved content relates to each other. Instead of a flat list of bookmarks, you get a network that shows:

- Which bookmarks share common topics
- What entities (people, companies, technologies) connect your reading
- Clusters of related content you've been exploring

## Why It Matters

**Without Knowledge Graph:** You save 100 bookmarks about "machine learning" but they're scattered across folders. You forget how they connect.

**With Knowledge Graph:** You instantly see that your TensorFlow article connects to your GPU optimization guide, which connects to your cloud computing bookmarks.

## How It Works (Step by Step)

### Step 1: Content Understanding

When you save a bookmark, Arivu fetches the page content and sends it to Gemini AI with this question:

> "Read this article and extract the key entities (people, organizations, technologies, concepts) mentioned."

For example, an article about "OpenAI's GPT-4" might extract:
- **Person:** Sam Altman
- **Organization:** OpenAI, Microsoft
- **Technology:** GPT-4, Transformer, RLHF
- **Concept:** Large Language Models, AI Safety

### Step 2: Meaning Encoding (Embeddings)

The entire content gets converted into a **768-dimensional embedding** — think of it as a "fingerprint" of what the article means.

```
Article: "How to deploy machine learning models on Kubernetes"
         ↓
Embedding: [0.234, -0.891, 0.127, ... 768 numbers]
```

Two articles about similar topics will have similar embeddings, even if they use different words.

### Step 3: Building Connections

The Knowledge Graph builds connections in two ways:

**Entity-Based Connections:**
- Article A mentions "React"
- Article B mentions "React"
- → A and B are connected through "React"

**Semantic Connections:**
- Article A's embedding is similar to Article B's embedding
- → A and B are conceptually related

### Step 4: Visualization

The frontend renders this as an interactive graph where:
- **Nodes** = Your bookmarks
- **Edges** = Connections between related content
- **Clusters** = Groups of highly related bookmarks

## Key Functions Explained

### `explore_knowledge_graph()`
Returns all your bookmarks with their entities and concepts, plus a map showing which bookmarks share which entities.

**What it returns:**
```json
{
  "bookmarks": [...],
  "entities": ["React", "OpenAI", "Sam Altman"],
  "concepts": ["machine-learning", "web-development"],
  "entity_connections": {
    "React": ["bookmark-1", "bookmark-3", "bookmark-7"]
  }
}
```

### `get_related_bookmarks(bookmark_id)`
Given one bookmark, finds others that are semantically similar using embedding comparison.

**The math:** It calculates the dot product of normalized embedding vectors. A score of 1.0 = identical meaning, 0.0 = completely unrelated.

Only returns bookmarks with similarity ≥ 0.25 (25% related or higher).

## Real-World Example

**You're researching "startup fundraising"**

Over time, you save:
- "How to pitch to VCs" → Entities: Y Combinator, Series A
- "Cap table management" → Entities: Carta, Equity
- "Investor update template" → Entities: Newsletter, Metrics
- "Sam Altman on startups" → Entities: Sam Altman, Y Combinator

The Knowledge Graph shows:
- Articles 1 & 4 are connected through "Y Combinator"
- All four are semantically clustered around "startup funding"
- You discover you have a growing knowledge base about fundraising

## Technical Details

| Component | Technology | Purpose |
|-----------|------------|---------|
| Entity Extraction | Gemini 2.5 Flash | Identifies named entities with confidence scores |
| Embeddings | Google text-embedding-004 | Creates 768-dimensional meaning vectors |
| Similarity | Dot Product (cosine) | Measures how related two embeddings are |
| Storage | MongoDB | Stores embeddings as arrays for fast retrieval |

## Confidence Threshold

Entity extraction only keeps entities with **confidence ≥ 0.6** (60%). This prevents false positives like extracting "The" or "Monday" as entities.

A denylist of 50+ common words is also filtered out (months, days, navigation words like "click here").
