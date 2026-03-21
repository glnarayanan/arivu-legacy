"""
Integration tests for database migrations.

Tests run against a real MongoDB instance via testcontainers.
Marked @pytest.mark.integration -- only run when explicitly requested:
    pytest tests/test_migrations.py -m integration

Requires: testcontainers[mongo], motor
    pip install testcontainers[mongo]
"""

import importlib

import pytest

# Import migration functions via importlib (module name starts with digit)
migration_001 = importlib.import_module("migrations.001_add_version_field")
upgrade = migration_001.upgrade
downgrade = migration_001.downgrade
verify = migration_001.verify

# Guard for testcontainers availability
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from testcontainers.mongodb import MongoDbContainer

    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not HAS_TESTCONTAINERS,
        reason="testcontainers not installed (pip install testcontainers[mongo])",
    ),
]


# ---------------------------------------------------------------------------
# Local real_db fixture (fallback if conftest.py not yet updated by 09-01)
# This can be removed once conftest.py has the real_db fixture.
# ---------------------------------------------------------------------------
if HAS_TESTCONTAINERS:

    @pytest.fixture(scope="module")
    def _mongo_container():
        with MongoDbContainer("mongo:7.0") as mongo:
            yield mongo

    @pytest.fixture
    async def real_db(_mongo_container):
        client = AsyncIOMotorClient(_mongo_container.get_connection_url())
        db = client["test_arivu_migrations"]
        yield db
        # Clean up all collections after each test
        for name in await db.list_collection_names():
            await db[name].drop()
        client.close()


# ---------------------------------------------------------------------------
# Helper: insert bookmarks without version field
# ---------------------------------------------------------------------------
async def _insert_bookmarks(db, count, *, with_version=False, version_value=1):
    """Insert test bookmarks. If with_version=True, include version field."""
    docs = []
    for i in range(count):
        doc = {
            "user_id": "test-user",
            "url": f"https://example.com/{i}",
            "title": f"Bookmark {i}",
        }
        if with_version:
            doc["version"] = version_value
        docs.append(doc)
    if docs:
        await db.bookmarks.insert_many(docs)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVersionFieldMigration:
    """Tests for 001_add_version_field migration."""

    async def test_version_field_migration_upgrade(self, real_db):
        """Upgrade adds version=1 to all bookmarks missing the field."""
        # Insert 100 bookmarks without version
        await _insert_bookmarks(real_db, 100)

        # Verify pre-migration state
        pre_verify = await verify(real_db)
        assert pre_verify["without_version"] == 100
        assert pre_verify["with_version"] == 0
        assert pre_verify["all_migrated"] is False

        # Run upgrade
        result = await upgrade(real_db)
        assert result["modified_count"] == 100
        assert result["action"] == "upgrade"

        # Verify post-migration state
        post_verify = await verify(real_db)
        assert post_verify["with_version"] == 100
        assert post_verify["without_version"] == 0
        assert post_verify["all_migrated"] is True
        assert post_verify["percent_migrated"] == 100.0

        # Confirm every bookmark has version=1
        async for doc in real_db.bookmarks.find({}):
            assert doc["version"] == 1

    async def test_version_field_migration_rollback(self, real_db):
        """Downgrade removes the version field from all bookmarks."""
        # Insert 50 bookmarks with version=3
        await _insert_bookmarks(real_db, 50, with_version=True, version_value=3)

        # Run downgrade
        result = await downgrade(real_db)
        assert result["modified_count"] == 50
        assert result["action"] == "downgrade"

        # Verify post-rollback state
        post_verify = await verify(real_db)
        assert post_verify["without_version"] == 50
        assert post_verify["with_version"] == 0

        # Confirm version key does not exist on any bookmark
        async for doc in real_db.bookmarks.find({}):
            assert "version" not in doc

    async def test_migration_idempotent(self, real_db):
        """Running upgrade twice does not overwrite existing version values."""
        # Insert 1 bookmark without version, 1 with version=5
        await _insert_bookmarks(real_db, 1)  # no version
        await real_db.bookmarks.insert_one(
            {
                "user_id": "test-user",
                "url": "https://example.com/existing",
                "title": "Already migrated",
                "version": 5,
            }
        )

        # First upgrade -- should only modify the one without version
        result = await upgrade(real_db)
        assert result["modified_count"] == 1

        # The bookmark with version=5 must still have version=5
        existing = await real_db.bookmarks.find_one({"url": "https://example.com/existing"})
        assert existing["version"] == 5

        # Second upgrade -- nothing to modify (idempotent)
        result2 = await upgrade(real_db)
        assert result2["modified_count"] == 0

        # Verify all migrated
        post_verify = await verify(real_db)
        assert post_verify["all_migrated"] is True
        assert post_verify["with_version"] == 2

    async def test_migration_upgrade_then_downgrade_roundtrip(self, real_db):
        """Full roundtrip: upgrade -> downgrade -> upgrade."""
        # Insert 100 bookmarks without version
        await _insert_bookmarks(real_db, 100)

        # Upgrade
        up1 = await upgrade(real_db)
        assert up1["modified_count"] == 100

        # Downgrade
        down = await downgrade(real_db)
        assert down["modified_count"] == 100

        # Verify all rolled back
        mid_verify = await verify(real_db)
        assert mid_verify["without_version"] == 100
        assert mid_verify["with_version"] == 0

        # Upgrade again
        up2 = await upgrade(real_db)
        assert up2["modified_count"] == 100

        # Verify all migrated again
        final_verify = await verify(real_db)
        assert final_verify["all_migrated"] is True

    async def test_migration_on_empty_collection(self, real_db):
        """Migration handles empty bookmarks collection gracefully."""
        # Run upgrade on empty collection
        result = await upgrade(real_db)
        assert result["modified_count"] == 0

        # Verify on empty collection
        v = await verify(real_db)
        assert v["total_bookmarks"] == 0
        assert v["all_migrated"] is True
        assert v["percent_migrated"] == 100.0
