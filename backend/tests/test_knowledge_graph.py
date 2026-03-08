"""
Tests for knowledge graph router endpoints.

Covers: explore, empty state, semantic search, expand query, regenerate embeddings.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Cursor mock factory for chained MongoDB queries
def make_cursor_mock(data):
    """Create a mock that supports .limit(...).to_list(None) chaining."""
    cursor = MagicMock()
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=data)
    return cursor


@pytest.mark.anyio
async def test_explore_knowledge_graph(client, mock_db):
    """GET /api/knowledge-graph/explore returns nodes and edges for a user."""
    mock_bookmarks = [
        {
            "id": "b1",
            "title": "Python Guide",
            "description": "Learn Python",
            "url": "https://python.org",
            "domain": "python.org",
            "favicon": None,
            "thumbnail": None,
            "created_at": "2024-01-01T00:00:00Z",
            "entities": ["Python", "Programming"],
            "concepts": ["tutorial", "language"],
            "embedding": [0.1, 0.2, 0.3],
        },
        {
            "id": "b2",
            "title": "FastAPI Docs",
            "description": "FastAPI framework",
            "url": "https://fastapi.tiangolo.com",
            "domain": "fastapi.tiangolo.com",
            "favicon": None,
            "thumbnail": None,
            "created_at": "2024-01-02T00:00:00Z",
            "entities": ["FastAPI", "Python"],
            "concepts": ["framework", "api"],
            "embedding": [0.1, 0.25, 0.35],
        },
    ]
    mock_db.bookmarks.find.return_value = make_cursor_mock(mock_bookmarks)

    response = await client.get("/api/knowledge-graph/explore?limit=50")
    assert response.status_code == 200

    data = response.json()
    assert data["total_bookmarks"] == 2
    assert data["total_entities"] > 0
    assert data["total_concepts"] > 0
    assert "bookmarks" in data
    assert "entities" in data
    assert "concepts" in data
    assert "entity_importance" in data
    assert "concept_importance" in data
    assert "related_bookmarks" in data
    # Embeddings should be stripped from response
    for b in data["bookmarks"]:
        assert "embedding" not in b


@pytest.mark.anyio
async def test_explore_knowledge_graph_empty(client, mock_db):
    """GET /api/knowledge-graph/explore returns empty structure when no bookmarks."""
    mock_db.bookmarks.find.return_value = make_cursor_mock([])

    response = await client.get("/api/knowledge-graph/explore")
    assert response.status_code == 200

    data = response.json()
    assert data["total_bookmarks"] == 0
    assert data["bookmarks"] == []
    assert data["entities"] == []
    assert data["concepts"] == []


@pytest.mark.anyio
@patch("app.routers.knowledge_graph.generate_embedding")
async def test_semantic_search(mock_embed, client, mock_db):
    """GET /api/knowledge-graph/search returns semantic search results."""
    # Mock query embedding
    mock_embed.return_value = [0.1, 0.2, 0.3]

    mock_bookmarks = [
        {
            "id": "b1",
            "title": "Python Guide",
            "description": "Learn Python",
            "url": "https://python.org",
            "favicon": None,
            "domain": "python.org",
            "thumbnail": None,
            "created_at": "2024-01-01T00:00:00Z",
            "embedding": [0.1, 0.2, 0.3],
            "entities": ["Python"],
            "concepts": ["programming"],
        },
    ]
    mock_db.bookmarks.find.return_value = MagicMock(
        to_list=AsyncMock(return_value=mock_bookmarks)
    )

    response = await client.get("/api/knowledge-graph/search?query=python+programming")
    assert response.status_code == 200

    data = response.json()
    assert "results" in data
    assert "query" in data
    assert data["query"] == "python programming"


@pytest.mark.anyio
async def test_expand_query(client, mock_db):
    """GET /api/knowledge-graph/expand-query returns related entities and concepts."""
    mock_bookmarks = [
        {
            "id": "b1",
            "entities": ["Python", "Django"],
            "concepts": ["web", "framework"],
            "embedding": [0.1, 0.2],
        },
        {
            "id": "b2",
            "entities": ["Python", "Flask"],
            "concepts": ["web", "microframework"],
            "embedding": [0.3, 0.4],
        },
    ]
    mock_db.bookmarks.find.return_value = make_cursor_mock(mock_bookmarks)

    response = await client.get("/api/knowledge-graph/expand-query?query=python")
    assert response.status_code == 200

    data = response.json()
    assert data["query"] == "python"
    assert "expansions" in data
    assert "related_entities" in data
    assert "related_concepts" in data
    assert data["total_entities_searched"] > 0


@pytest.mark.anyio
async def test_regenerate_embeddings(client, mock_db):
    """POST /api/knowledge-graph/regenerate-embeddings starts background processing."""
    mock_db.bookmarks.count_documents = AsyncMock(return_value=5)

    # Background task calls get_database().bookmarks.find(...).to_list(None)
    # so we need the find() cursor to support async to_list chaining.
    mock_db.bookmarks.find.return_value = make_cursor_mock([])

    response = await client.post("/api/knowledge-graph/regenerate-embeddings")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "processing"
    assert data["queued"] == 5


@pytest.mark.anyio
async def test_explore_rejects_unauthenticated(mock_db):
    """Knowledge graph endpoints reject unauthenticated requests."""
    from fastapi import APIRouter, FastAPI
    from httpx import ASGITransport, AsyncClient
    from app.routers.knowledge_graph import router as kg_router

    # Create test app WITHOUT auth override
    test_app = FastAPI()
    api = APIRouter(prefix="/api")
    api.include_router(kg_router)
    test_app.include_router(api)

    # Override database
    import app.core.database as db_module
    _original_db = db_module.db
    db_module.db = mock_db

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/knowledge-graph/explore")
        assert response.status_code == 401

    db_module.db = _original_db
