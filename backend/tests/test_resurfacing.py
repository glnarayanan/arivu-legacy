"""
Tests for resurfacing + memory-jogger router endpoints.

Covers: resurfacing suggestions, snooze, archive, unarchive,
memory-jogger get, and memory-jogger dismiss.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# --- Helpers for cursor mocking ---


def make_cursor(items):
    """Create a mock MongoDB cursor that supports .to_list(), .limit() chaining."""
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=items)
    cursor.limit = MagicMock(return_value=cursor)
    return cursor


# --- Sample data ---

THIRTY_DAYS_AGO = (datetime.now(UTC) - timedelta(days=30)).isoformat()

SAMPLE_BOOKMARK = {
    "id": "bm-1",
    "title": "Test Bookmark",
    "url": "https://example.com",
    "domain": "example.com",
    "thumbnail": None,
    "favicon": None,
    "description": "A test bookmark",
    "reading_time": 5,
    "created_at": THIRTY_DAYS_AGO,
    "last_accessed": THIRTY_DAYS_AGO,
    "view_count": 3,
    "resurfacing_snoozed_until": None,
    "resurfacing_archived": False,
}


# ============================================
# Resurfacing Suggestions Tests
# ============================================


@pytest.mark.anyio
@patch("app.routers.resurfacing.should_resurface", return_value=True)
@patch(
    "app.routers.resurfacing.calculate_resurfacing_score",
    return_value=(
        25.0,
        {
            "age": 10,
            "engagement": 6,
            "quality": 3,
            "reading_time": 5,
            "spaced_repetition": 0,
            "total": 25.0,
        },
    ),
)
@patch(
    "app.routers.resurfacing.get_resurfacing_reason",
    return_value="Not opened in 30 days",
)
async def test_get_resurfacing_suggestions(mock_reason, mock_score, mock_should, client, mock_db):
    """GET /api/resurfacing returns scored suggestions."""
    # Mock bookmarks cursor
    mock_db.bookmarks.find.return_value = make_cursor([SAMPLE_BOOKMARK])
    # Mock AI summaries cursor
    mock_db.ai_summaries.find.return_value = make_cursor([{"bookmark_id": "bm-1", "one_sentence": "A test summary"}])

    response = await client.get("/api/resurfacing")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert "total_candidates" in data
    assert data["total_candidates"] == 1
    assert len(data["suggestions"]) == 1
    assert data["suggestions"][0]["resurfacing_reason"] == "Not opened in 30 days"


@pytest.mark.anyio
async def test_get_resurfacing_suggestions_empty(client, mock_db):
    """GET /api/resurfacing with no bookmarks returns empty suggestions."""
    mock_db.bookmarks.find.return_value = make_cursor([])
    mock_db.ai_summaries.find.return_value = make_cursor([])

    response = await client.get("/api/resurfacing")
    assert response.status_code == 200
    data = response.json()
    assert data["suggestions"] == []
    assert data["total_candidates"] == 0


# ============================================
# Snooze Tests
# ============================================


@pytest.mark.anyio
async def test_snooze_resurfacing(client, mock_db):
    """POST /api/resurfacing/{id}/snooze snoozes bookmark for N days."""
    mock_db.bookmarks.find_one.return_value = {"id": "bm-1", "user_id": "test-user-id"}

    response = await client.post(
        "/api/resurfacing/bm-1/snooze",
        json={"days": 14},
    )
    assert response.status_code == 200
    data = response.json()
    assert "snoozed_until" in data
    assert "14 days" in data["message"]
    mock_db.bookmarks.update_one.assert_called_once()


@pytest.mark.anyio
async def test_snooze_resurfacing_not_found(client, mock_db):
    """POST /api/resurfacing/{id}/snooze returns 404 for missing bookmark."""
    mock_db.bookmarks.find_one.return_value = None

    response = await client.post(
        "/api/resurfacing/nonexistent/snooze",
        json={"days": 7},
    )
    assert response.status_code == 404


# ============================================
# Archive Tests
# ============================================


@pytest.mark.anyio
async def test_archive_from_resurfacing(client, mock_db):
    """POST /api/resurfacing/{id}/archive archives bookmark."""
    mock_db.bookmarks.find_one.return_value = {"id": "bm-1", "user_id": "test-user-id"}

    response = await client.post("/api/resurfacing/bm-1/archive")
    assert response.status_code == 200
    assert "archived" in response.json()["message"].lower()
    mock_db.bookmarks.update_one.assert_called_once()


@pytest.mark.anyio
async def test_archive_not_found(client, mock_db):
    """POST /api/resurfacing/{id}/archive returns 404 for missing bookmark."""
    mock_db.bookmarks.find_one.return_value = None

    response = await client.post("/api/resurfacing/nonexistent/archive")
    assert response.status_code == 404


# ============================================
# Unarchive Tests
# ============================================


@pytest.mark.anyio
async def test_unarchive_from_resurfacing(client, mock_db):
    """POST /api/resurfacing/{id}/unarchive restores bookmark to resurfacing."""
    mock_db.bookmarks.find_one.return_value = {"id": "bm-1", "user_id": "test-user-id"}

    response = await client.post("/api/resurfacing/bm-1/unarchive")
    assert response.status_code == 200
    assert "unarchived" in response.json()["message"].lower()
    mock_db.bookmarks.update_one.assert_called_once()


# ============================================
# Memory Jogger Tests
# ============================================


@pytest.mark.anyio
async def test_get_memory_jogger(client, mock_db):
    """GET /api/memory-jogger returns featured bookmark with context."""
    bookmark_with_embedding = {
        **SAMPLE_BOOKMARK,
        "embedding": [0.1] * 768,
    }

    # First call: main bookmarks query
    # Second call: recent bookmarks with embeddings
    # The mock_db.bookmarks.find is a MagicMock — each call returns same cursor
    # We need to differentiate calls. Use side_effect.
    call_count = 0

    def bookmarks_find_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Main bookmarks query
            return make_cursor([bookmark_with_embedding])
        elif call_count == 2:
            # Recent with embeddings
            return make_cursor([])
        else:
            return make_cursor([])

    mock_db.bookmarks.find.side_effect = bookmarks_find_side_effect

    # AI summaries find (completed summaries)
    mock_db.ai_summaries.find.return_value = make_cursor([])

    # AI summary find_one for selected bookmark
    mock_db.ai_summaries.find_one.return_value = {
        "bookmark_id": "bm-1",
        "one_sentence": "A test summary",
    }

    response = await client.get("/api/memory-jogger")
    assert response.status_code == 200
    data = response.json()
    assert data["has_memory"] is True
    assert "bookmark" in data
    assert "context" in data
    assert data["bookmark"]["id"] == "bm-1"
    assert "reason" in data["context"]


@pytest.mark.anyio
async def test_get_memory_jogger_empty(client, mock_db):
    """GET /api/memory-jogger with no eligible bookmarks returns has_memory=False."""
    mock_db.bookmarks.find.return_value = make_cursor([])

    response = await client.get("/api/memory-jogger")
    assert response.status_code == 200
    data = response.json()
    assert data["has_memory"] is False
    assert data["bookmark"] is None


# ============================================
# Memory Jogger Dismiss Tests
# ============================================


@pytest.mark.anyio
async def test_dismiss_memory_jogger(client, mock_db):
    """POST /api/memory-jogger/dismiss records dismissal."""
    mock_db.bookmarks.find_one.return_value = {"id": "bm-1", "user_id": "test-user-id"}

    response = await client.post(
        "/api/memory-jogger/dismiss",
        json={"bookmark_id": "bm-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["bookmark_id"] == "bm-1"
    mock_db.bookmarks.update_one.assert_called_once()


@pytest.mark.anyio
async def test_dismiss_memory_jogger_not_found(client, mock_db):
    """POST /api/memory-jogger/dismiss returns 404 for missing bookmark."""
    mock_db.bookmarks.find_one.return_value = None

    response = await client.post(
        "/api/memory-jogger/dismiss",
        json={"bookmark_id": "nonexistent"},
    )
    assert response.status_code == 404
