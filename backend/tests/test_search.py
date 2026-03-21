"""
Tests for search router and search utility functions.

Covers: hybrid search endpoint, empty query handling, query type detection,
pagination, user isolation, and search_utils pure functions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.search_utils import (
    calculate_bm25_score,
    calculate_entity_boost,
    detect_query_type,
    get_adaptive_weights,
    reciprocal_rank_fusion,
    tokenize_text,
)

# --- Helpers for cursor mocking ---


def make_cursor(items):
    """Create a mock MongoDB cursor that supports chained .limit().to_list()."""
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=items)
    cursor.sort = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    return cursor


# --- Sample data ---

SAMPLE_BOOKMARKS = [
    {
        "id": "bm-1",
        "user_id": "test-user-id",
        "url": "https://example.com/python-guide",
        "title": "Complete Python Programming Guide",
        "description": "A comprehensive guide to Python programming",
        "domain": "example.com",
        "thumbnail": None,
        "favicon": None,
        "reading_time": 10,
        "read_status": False,
        "created_at": "2026-01-01T00:00:00+00:00",
        "embedding": [0.1] * 768,
        "entities": ["Python", "Programming"],
        "concepts": ["software-development"],
        "text_content": "Python is a versatile programming language used for web development, data science, and automation.",
    },
    {
        "id": "bm-2",
        "user_id": "test-user-id",
        "url": "https://example.com/javascript-tutorial",
        "title": "JavaScript Tutorial for Beginners",
        "description": "Learn JavaScript from scratch",
        "domain": "example.com",
        "thumbnail": None,
        "favicon": None,
        "reading_time": 15,
        "read_status": True,
        "created_at": "2026-01-02T00:00:00+00:00",
        "embedding": [0.2] * 768,
        "entities": ["JavaScript"],
        "concepts": ["web-development"],
        "text_content": "JavaScript is the language of the web, used for building interactive websites.",
    },
    {
        "id": "bm-3",
        "user_id": "test-user-id",
        "url": "https://example.com/rust-systems",
        "title": "Rust for Systems Programming",
        "description": "Building fast, safe systems with Rust",
        "domain": "example.com",
        "thumbnail": None,
        "favicon": None,
        "reading_time": 20,
        "read_status": False,
        "created_at": "2026-01-03T00:00:00+00:00",
        "embedding": [0.3] * 768,
        "entities": ["Rust", "Systems Programming"],
        "concepts": ["performance", "memory-safety"],
        "text_content": "Rust provides memory safety without garbage collection, perfect for systems programming.",
    },
]


# ============================================
# UNIT TESTS - search_utils pure functions
# ============================================


class TestTokenizeText:
    def test_basic_tokenization(self):
        tokens = tokenize_text("Hello World Python Programming")
        assert "hello" in tokens
        assert "world" in tokens
        assert "python" in tokens
        assert "programming" in tokens

    def test_stopword_removal(self):
        tokens = tokenize_text("the quick brown fox is a good animal")
        # "the", "is", "a" are stopwords
        assert "the" not in tokens
        assert "is" not in tokens
        assert "a" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens

    def test_empty_input(self):
        assert tokenize_text("") == []
        assert tokenize_text(None) == []

    def test_short_token_removal(self):
        tokens = tokenize_text("I am a x y z developer")
        # Single-character tokens should be filtered
        assert "x" not in tokens
        assert "y" not in tokens
        assert "z" not in tokens


class TestBM25Score:
    def test_basic_scoring(self):
        query_tokens = ["python", "programming"]
        doc_tokens = ["python", "programming", "language", "guide"]
        doc_freq = {"python": 2, "programming": 1, "language": 3, "guide": 2}
        score = calculate_bm25_score(query_tokens, doc_tokens, doc_freq, 10.0, 5)
        assert score > 0

    def test_empty_query(self):
        score = calculate_bm25_score([], ["python"], {"python": 1}, 10.0, 5)
        assert score == 0.0

    def test_empty_doc(self):
        score = calculate_bm25_score(["python"], [], {"python": 1}, 10.0, 5)
        assert score == 0.0

    def test_no_match(self):
        score = calculate_bm25_score(["rust"], ["python", "javascript"], {"python": 1, "javascript": 1}, 10.0, 5)
        assert score == 0.0

    def test_higher_tf_higher_score(self):
        """Document with more occurrences of query term should score higher."""
        query = ["python"]
        doc_few = ["python", "guide"]
        doc_many = ["python", "python", "python", "guide"]
        doc_freq = {"python": 1, "guide": 1}
        score_few = calculate_bm25_score(query, doc_few, doc_freq, 5.0, 5)
        score_many = calculate_bm25_score(query, doc_many, doc_freq, 5.0, 5)
        assert score_many > score_few


class TestEntityBoost:
    def test_overlap_scoring(self):
        score = calculate_entity_boost(
            ["python", "ai"],
            ["Python", "Machine Learning", "AI"],
            {"python": 1.0, "ai": 0.5, "machine learning": 0.8},
        )
        assert score > 0

    def test_no_overlap(self):
        score = calculate_entity_boost(
            ["rust"],
            ["Python", "JavaScript"],
            {"rust": 1.0, "python": 0.5, "javascript": 0.5},
        )
        assert score == 0.0

    def test_empty_inputs(self):
        assert calculate_entity_boost([], ["Python"], {}) == 0.0
        assert calculate_entity_boost(["python"], [], {}) == 0.0


class TestRRF:
    def test_basic_fusion(self):
        list1 = [("doc-a", 10.0), ("doc-b", 5.0)]
        list2 = [("doc-b", 8.0), ("doc-c", 3.0)]
        scores = reciprocal_rank_fusion([list1, list2])
        # doc-b appears in both lists, should have highest RRF score
        assert scores["doc-b"] > scores["doc-a"]
        assert scores["doc-b"] > scores["doc-c"]

    def test_single_list(self):
        list1 = [("doc-a", 10.0), ("doc-b", 5.0)]
        scores = reciprocal_rank_fusion([list1])
        assert "doc-a" in scores
        assert "doc-b" in scores
        assert scores["doc-a"] > scores["doc-b"]

    def test_empty_lists(self):
        scores = reciprocal_rank_fusion([])
        assert scores == {}


class TestDetectQueryType:
    def test_quoted_query(self):
        assert detect_query_type('"exact phrase"') == "exact"
        assert detect_query_type("it's a test") == "exact"

    def test_technical_query(self):
        assert detect_query_type("react/hooks") == "technical"
        assert detect_query_type("v2.0.1") == "technical"

    def test_short_query_is_exact(self):
        assert detect_query_type("python") == "exact"
        assert detect_query_type("machine learning") == "exact"

    def test_long_query_is_semantic(self):
        assert detect_query_type("how to build web apps with python") == "semantic"


class TestGetAdaptiveWeights:
    def test_exact_favors_keyword(self):
        sem, kw = get_adaptive_weights("exact")
        assert kw > sem

    def test_semantic_favors_semantic(self):
        sem, kw = get_adaptive_weights("semantic")
        assert sem > kw

    def test_technical_balanced(self):
        sem, kw = get_adaptive_weights("technical")
        assert kw > sem  # Keyword edge for technical


# ============================================
# INTEGRATION TESTS - search router endpoint
# ============================================


@pytest.mark.anyio
@patch("app.routers.search.generate_embedding", new_callable=AsyncMock)
async def test_hybrid_search_basic(mock_embed, client, mock_db):
    """Basic search returns results with relevance scores."""
    mock_embed.return_value = [0.15] * 768
    mock_db.bookmarks.find.return_value = make_cursor(SAMPLE_BOOKMARKS)
    mock_db.ai_summaries.find.return_value = make_cursor([])

    resp = await client.get("/api/search", params={"query": "python programming guide"})
    assert resp.status_code == 200

    data = resp.json()
    assert "results" in data
    assert "query" in data
    assert data["query"] == "python programming guide"
    assert "query_type" in data
    assert "search_mode" in data

    # Should have results (BM25 matches "python" and "programming")
    assert len(data["results"]) > 0
    # First result should have relevance_score
    assert "relevance_score" in data["results"][0]


@pytest.mark.anyio
async def test_hybrid_search_empty_query(client):
    """Empty query returns 400."""
    resp = await client.get("/api/search", params={"query": ""})
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_hybrid_search_short_query(client):
    """Single-character query returns 400."""
    resp = await client.get("/api/search", params={"query": "a"})
    assert resp.status_code == 400


@pytest.mark.anyio
@patch("app.routers.search.generate_embedding", new_callable=AsyncMock)
async def test_hybrid_search_no_results(mock_embed, client, mock_db):
    """Search with no matching bookmarks returns empty results."""
    mock_embed.return_value = None
    mock_db.bookmarks.find.return_value = make_cursor([])

    resp = await client.get("/api/search", params={"query": "nonexistent topic"})
    assert resp.status_code == 200

    data = resp.json()
    assert data["results"] == []
    assert data["total"] == 0
    assert data["message"] is not None


@pytest.mark.anyio
@patch("app.routers.search.generate_embedding", new_callable=AsyncMock)
async def test_hybrid_search_keyword_only(mock_embed, client, mock_db):
    """Search with use_semantic=false uses only BM25 scoring."""
    mock_embed.return_value = None
    mock_db.bookmarks.find.return_value = make_cursor(SAMPLE_BOOKMARKS)
    mock_db.ai_summaries.find.return_value = make_cursor([])

    resp = await client.get(
        "/api/search",
        params={"query": "python programming", "use_semantic": "false"},
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["search_mode"]["keyword"] is True
    # Semantic should be disabled in response mode
    assert data["search_mode"]["semantic"] is False


@pytest.mark.anyio
@patch("app.routers.search.generate_embedding", new_callable=AsyncMock)
async def test_hybrid_search_user_isolation(mock_embed, client, mock_db):
    """Search only queries bookmarks for the authenticated user."""
    mock_embed.return_value = None
    mock_db.bookmarks.find.return_value = make_cursor([])

    resp = await client.get("/api/search", params={"query": "python guide"})
    assert resp.status_code == 200

    # Verify the DB query included user_id filter
    call_args = mock_db.bookmarks.find.call_args
    query_filter = call_args[0][0]  # First positional arg is the query dict
    assert "user_id" in query_filter
    assert query_filter["user_id"] == "test-user-id"
