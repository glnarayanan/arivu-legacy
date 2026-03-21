"""
Tests for collections router endpoints.

Covers: create, list, add-to-collection, and validation edge cases.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.anyio
async def test_create_collection(client, mock_db):
    """POST /api/collections creates a collection and returns it."""
    response = await client.post("/api/collections", json={"name": "My Collection"})

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["user_id"] == "test-user-id"
    assert data["name"] == "My Collection"
    assert data["bookmark_ids"] == []
    assert "created_at" in data
    mock_db.collections.insert_one.assert_called_once()


@pytest.mark.anyio
async def test_create_collection_empty_name(client):
    """POST /api/collections with empty name returns 422."""
    response = await client.post("/api/collections", json={"name": ""})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_collection_whitespace_name(client):
    """POST /api/collections with whitespace-only name returns 422."""
    response = await client.post("/api/collections", json={"name": "   "})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_collection_long_name(client):
    """POST /api/collections with name over 100 chars returns 422."""
    long_name = "a" * 101
    response = await client.post("/api/collections", json={"name": long_name})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_collection_invalid_chars(client):
    """POST /api/collections with special characters returns 422."""
    response = await client.post("/api/collections", json={"name": "test@#$"})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_collections(client, mock_db):
    """GET /api/collections returns list of user collections."""
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(
        return_value=[
            {
                "id": "col-1",
                "user_id": "test-user-id",
                "name": "Reading List",
                "bookmark_ids": ["bm-1"],
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ]
    )
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_db.collections.find = MagicMock(return_value=mock_cursor)

    response = await client.get("/api/collections")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "Reading List"


@pytest.mark.anyio
async def test_get_collections_empty(client, mock_db):
    """GET /api/collections returns empty list when no collections exist."""
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_db.collections.find = MagicMock(return_value=mock_cursor)

    response = await client.get("/api/collections")

    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.anyio
async def test_add_to_collection(client, mock_db):
    """POST /api/collections/{id}/add adds bookmark to collection."""
    mock_result = MagicMock()
    mock_result.matched_count = 1
    mock_db.collections.update_one = AsyncMock(return_value=mock_result)

    response = await client.post("/api/collections/col-1/add", json={"bookmark_id": "bm-1"})

    assert response.status_code == 200
    assert response.json()["message"] == "Bookmark added to collection"
    mock_db.collections.update_one.assert_called_once()


@pytest.mark.anyio
async def test_add_to_collection_not_found(client, mock_db):
    """POST /api/collections/{id}/add returns 404 when collection not found."""
    mock_result = MagicMock()
    mock_result.matched_count = 0
    mock_db.collections.update_one = AsyncMock(return_value=mock_result)

    response = await client.post("/api/collections/nonexistent/add", json={"bookmark_id": "bm-1"})

    assert response.status_code == 404
    assert "Collection not found" in response.json()["detail"]
