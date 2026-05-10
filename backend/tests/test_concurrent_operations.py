"""
Integration tests for concurrent MongoDB operations.

Requires Docker daemon running (real MongoDB via testcontainers).
Run: MONGO_URL=mongodb://localhost:27017 SECRET_KEY=<key> pytest -m integration tests/test_concurrent_operations.py -v
Skip: pytest -m "not integration" tests/

Verifies:
- Exactly one update wins when N concurrent requests target the same version
- Sequential read-then-update cycles all succeed without conflict
- Concurrent updates to different bookmarks never interfere (no false conflicts)
- Mixed concurrent operations preserve data integrity (no field data loss)
"""

import asyncio
from datetime import UTC, datetime

import pytest

# Guard: skip all tests in this module if testcontainers is not installed
pytest.importorskip("testcontainers.mongodb")


def _make_bookmark(bookmark_id: str, user_id: str = "user-1", version: int = 1, **extra):
    """Create a bookmark document with required fields."""
    return {
        "id": bookmark_id,
        "user_id": user_id,
        "url": f"https://example.com/{bookmark_id}",
        "title": f"Bookmark {bookmark_id}",
        "domain": "example.com",
        "read_status": False,
        "version": version,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        **extra,
    }


@pytest.mark.integration
@pytest.mark.anyio
async def test_concurrent_updates_exactly_one_wins(real_db):
    """Fire 20 concurrent updates targeting the same version. Exactly one should succeed."""
    bookmark = _make_bookmark("bm-race")
    await real_db.bookmarks.insert_one(bookmark)

    results = []

    async def attempt_update():
        """Try to atomically update the bookmark matching version=1."""
        r = await real_db.bookmarks.find_one_and_update(
            {"id": "bm-race", "version": 1},
            {
                "$inc": {"version": 1},
                "$set": {
                    "read_status": True,
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            },
            return_document=True,
        )
        results.append(r)

    # Fire 20 concurrent update attempts
    await asyncio.gather(*[attempt_update() for _ in range(20)])

    # Exactly one should have succeeded (got a non-None result)
    successes = [r for r in results if r is not None]
    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)} " f"(total attempts: {len(results)})"

    # Final state should have version=2
    final = await real_db.bookmarks.find_one({"id": "bm-race"})
    assert final["version"] == 2
    assert final["read_status"] is True


@pytest.mark.integration
@pytest.mark.anyio
async def test_sequential_updates_all_succeed(real_db):
    """Sequential read-then-update cycles should all succeed. Final version = 1 + N."""
    bookmark = _make_bookmark("bm-sequential")
    await real_db.bookmarks.insert_one(bookmark)

    num_updates = 50

    for i in range(num_updates):
        # Read current version
        current = await real_db.bookmarks.find_one({"id": "bm-sequential"})
        current_version = current["version"]

        # Update with the current version
        result = await real_db.bookmarks.find_one_and_update(
            {"id": "bm-sequential", "version": current_version},
            {
                "$inc": {"version": 1},
                "$set": {"updated_at": datetime.now(UTC).isoformat()},
            },
            return_document=True,
        )
        assert result is not None, f"Update {i+1} failed unexpectedly at version {current_version}"

    # Final version should be 1 + num_updates
    final = await real_db.bookmarks.find_one({"id": "bm-sequential"})
    assert final["version"] == 1 + num_updates


@pytest.mark.integration
@pytest.mark.anyio
async def test_concurrent_updates_different_bookmarks_all_succeed(real_db):
    """Concurrent updates to different bookmarks should ALL succeed (no false conflicts)."""
    num_bookmarks = 20

    # Insert 20 different bookmarks
    bookmarks = []
    for i in range(num_bookmarks):
        bm = _make_bookmark(f"bm-parallel-{i}")
        bookmarks.append(bm)
    # Batch insert: need unique URLs to avoid unique index conflict
    for bm in bookmarks:
        bm["url"] = f"https://example.com/parallel-{bm['id']}"
    await real_db.bookmarks.insert_many(bookmarks)

    results = {}

    async def update_bookmark(bm_id: str):
        """Update a specific bookmark."""
        r = await real_db.bookmarks.find_one_and_update(
            {"id": bm_id, "version": 1},
            {
                "$inc": {"version": 1},
                "$set": {"read_status": True},
            },
            return_document=True,
        )
        results[bm_id] = r

    # Fire concurrent updates, each targeting a different bookmark
    await asyncio.gather(*[update_bookmark(f"bm-parallel-{i}") for i in range(num_bookmarks)])

    # ALL should have succeeded (no false conflicts between different bookmarks)
    for i in range(num_bookmarks):
        bm_id = f"bm-parallel-{i}"
        assert results[bm_id] is not None, f"Update for {bm_id} failed (false conflict!)"
        assert results[bm_id]["version"] == 2
        assert results[bm_id]["read_status"] is True


@pytest.mark.integration
@pytest.mark.anyio
async def test_concurrent_mixed_operations_no_data_loss(real_db):
    """Mixed concurrent operations on different fields preserve all data (no field loss)."""
    bookmark = _make_bookmark(
        "bm-mixed",
        tags=["original"],
        description="Original description",
        reading_time=5,
    )
    await real_db.bookmarks.insert_one(bookmark)

    # Multiple concurrent operations on different fields using $set
    # Since they all target version=1, only one will win via find_one_and_update.
    # The others should use update_one without version check for non-conflicting fields.

    async def update_read_status():
        """Simulate user marking as read (uses optimistic locking)."""
        return await real_db.bookmarks.find_one_and_update(
            {"id": "bm-mixed", "version": 1},
            {
                "$inc": {"version": 1},
                "$set": {"read_status": True},
            },
            return_document=True,
        )

    async def update_description():
        """Simulate background AI updating description (uses update_one, no version lock)."""
        return await real_db.bookmarks.update_one(
            {"id": "bm-mixed"},
            {"$set": {"description": "AI-generated description"}},
        )

    async def update_reading_time():
        """Simulate background content processing updating reading time."""
        return await real_db.bookmarks.update_one(
            {"id": "bm-mixed"},
            {"$set": {"reading_time": 10}},
        )

    # Fire all operations concurrently
    results = await asyncio.gather(
        update_read_status(),
        update_description(),
        update_reading_time(),
    )

    # The optimistic locking update should have succeeded
    assert results[0] is not None, "Optimistic locking update failed unexpectedly"

    # Verify final state has ALL fields preserved (no data loss)
    final = await real_db.bookmarks.find_one({"id": "bm-mixed"})
    assert final is not None

    # Version should be incremented
    assert final["version"] == 2

    # Read status from the locked update
    assert final["read_status"] is True

    # Fields from non-locked background updates
    assert final["description"] == "AI-generated description"
    assert final["reading_time"] == 10

    # Original fields preserved
    assert final["title"] == "Bookmark bm-mixed"
    assert final["domain"] == "example.com"
    assert final["user_id"] == "user-1"
