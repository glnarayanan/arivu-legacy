# Knowledge Graph

**Status:** ✅ Phase 1 Implemented (Roadmap Item 1)
**Implemented:** January 2026
**Frontend:** `/knowledge-graph`
**API:** `/api/knowledge-graph/*`

---

## Overview

The Knowledge Graph is a semantic AI-powered feature that automatically extracts entities and relationships from your bookmarks, creating an interconnected web of knowledge. It helps you discover hidden connections between seemingly unrelated content.

---

## Key Features

### 1. **Entity Extraction**
Automatically identifies and extracts:
- **People** - Authors, researchers, thought leaders
- **Organizations** - Companies, institutions, projects
- **Concepts** - Technical terms, theories, methodologies
- **Technologies** - Tools, frameworks, languages
- **Topics** - Themes, subjects, domains

### 2. **Relationship Mapping**
Discovers connections between entities:
- Related concepts
- People associated with organizations
- Technologies used by projects
- Similar topics across different bookmarks

### 3. **Semantic Embeddings**
Uses vector embeddings for:
- Content similarity detection
- Semantic search
- Related bookmark recommendations
- Cluster detection

---

## How It Works

### Backend Processing

1. **Content Analysis**
   - When a bookmark is saved, content is analyzed by Gemini 2.5 Flash
   - Entities are extracted using NLP techniques
   - Relationships are identified based on context

2. **Embedding Generation**
   - Text is converted to vector embeddings using scikit-learn
   - Embeddings enable semantic similarity calculations
   - Stored in MongoDB for fast retrieval

3. **Graph Construction**
   - Entities become nodes in the graph
   - Relationships become edges
   - Weights calculated based on co-occurrence and context

### Frontend Visualization

The `/knowledge-graph` page displays:
- Interactive node-link diagram
- Filterable by entity type
- Zoomable and pannable
- Click nodes to see related bookmarks

---

## API Endpoints

### GET /api/knowledge-graph/explore
Retrieve the knowledge graph structure.

**Query Parameters:**
- `entity` (optional) - Focus on specific entity
- `depth` (optional) - Graph depth (default: 2, max: 5)

**Response:**
```json
{
  "nodes": [
    {
      "id": "entity_1",
      "label": "Machine Learning",
      "type": "concept",
      "bookmark_count": 15
    }
  ],
  "edges": [
    {
      "source": "entity_1",
      "target": "entity_2",
      "relationship": "related_to",
      "strength": 0.85
    }
  ]
}
```

### GET /api/knowledge-graph/search
Search for entities in the graph.

**Query Parameters:**
- `query` - Search string
- `limit` (optional) - Max results (default: 10)

### POST /api/knowledge-graph/regenerate-embeddings
Regenerate embeddings for all bookmarks (admin operation).

---

## Use Cases

### 1. **Discovery**
Find connections you didn't know existed:
- "I've been reading about React and MongoDB separately - the graph shows they're often used together"

### 2. **Research**
Track recurring themes in your research:
- "My bookmarks about AI consistently mention ethics and bias"

### 3. **Learning Paths**
Identify knowledge gaps:
- "I have many bookmarks about frontend but few about backend - the graph shows isolated clusters"

### 4. **Content Curation**
Create thematic collections:
- "The graph shows a cluster of bookmarks about sustainability - I should create a collection"

---

## Configuration

### Entity Types
Configurable in `backend/server.py`:
```python
ENTITY_TYPES = [
    "person",
    "organization",
    "concept",
    "technology",
    "topic"
]
```

### Similarity Threshold
Minimum similarity score for edge creation (default: 0.7):
```python
SIMILARITY_THRESHOLD = 0.7
```

---

## Performance

### Database Indexes
Knowledge graph uses these MongoDB indexes:
- `user_id` + `entity_type` - Fast entity filtering
- `user_id` + `entity_label` - Quick entity lookups
- `embedding_vector` - Vector similarity search

### Caching
- Graph structure cached for 5 minutes
- Embeddings cached indefinitely until content changes

---

## Limitations (Phase 1)

- English language only
- Maximum 5000 entities per user
- Graph depth limited to 5 levels
- No manual entity editing

Not currently implemented:
- Multi-language support
- Custom entity types
- Manual relationship editing
- Graph export (GraphML, Cypher)
- Time-based graph evolution view

---

## Technical Implementation

### Libraries Used
- `scikit-learn` - Vector embeddings and similarity
- `google-generativeai` - Entity extraction with Gemini
- `numpy` - Vector operations
- `pymongo` - Graph storage in MongoDB

### Database Schema

**Entities Collection:**
```json
{
  "id": "entity_unique_id",
  "user_id": "user_id",
  "label": "Machine Learning",
  "type": "concept",
  "bookmark_ids": ["bm1", "bm2"],
  "embedding_vector": [0.1, 0.2, ...],
  "created_at": "2026-01-12T00:00:00Z"
}
```

**Relationships Collection:**
```json
{
  "id": "rel_unique_id",
  "user_id": "user_id",
  "source_entity_id": "entity_1",
  "target_entity_id": "entity_2",
  "relationship_type": "related_to",
  "strength": 0.85,
  "created_at": "2026-01-12T00:00:00Z"
}
```

---

## Troubleshooting

### Graph not showing entities
- Check that bookmarks have been processed (status: "completed")
- Verify Gemini API key is configured
- Check browser console for errors

### Slow graph loading
- Reduce graph depth parameter
- Clear browser cache
- Check backend logs for performance issues

### Missing connections
- Lower similarity threshold (adjust in backend)
- Regenerate embeddings: `POST /api/knowledge-graph/regenerate-embeddings`

---

## Related Features

- **[Analytics](analytics.md)** - Topic distribution uses knowledge graph data
- **[Resurfacing](resurfacing-engine.md)** - Uses entity similarity for suggestions
- **Related Bookmarks** - Powered by knowledge graph embeddings

---

## References

- **API Docs:** [documentation/api/README.md](../api/README.md#knowledge-graph-endpoints)
- **Architecture:** [documentation/architecture.md](../architecture.md)

---

**Last Updated:** May 10, 2026
**Status:** Implemented for graph exploration, semantic search, query expansion, and embedding regeneration
