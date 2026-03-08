"""
Migration 001: Add version field to all bookmarks.

Introduced by Phase 7 (REL-04: Optimistic locking).
The version field enables concurrent update detection via find_one_and_update
with version matching.

Apply: Sets version=1 on all bookmarks that lack the version field.
Rollback: Removes the version field from all bookmarks.
Verify: Reports counts of bookmarks with and without version field.

Usage via runner:
    python -m migrations.runner apply 001_add_version_field
    python -m migrations.runner rollback 001_add_version_field
    python -m migrations.runner verify 001_add_version_field
"""
import logging

logger = logging.getLogger(__name__)


async def upgrade(db):
    """Add version=1 to all bookmarks missing the version field."""
    result = await db.bookmarks.update_many(
        {"version": {"$exists": False}},
        {"$set": {"version": 1}},
    )
    logger.info(f"Migration 001 upgrade: modified {result.modified_count} bookmarks")
    return {
        "migration": "001_add_version_field",
        "action": "upgrade",
        "modified_count": result.modified_count,
    }


async def downgrade(db):
    """Remove version field from all bookmarks."""
    result = await db.bookmarks.update_many(
        {},
        {"$unset": {"version": ""}},
    )
    logger.info(f"Migration 001 downgrade: modified {result.modified_count} bookmarks")
    return {
        "migration": "001_add_version_field",
        "action": "downgrade",
        "modified_count": result.modified_count,
    }


async def verify(db):
    """Check migration status: how many bookmarks have/lack the version field."""
    without_version = await db.bookmarks.count_documents(
        {"version": {"$exists": False}}
    )
    with_version = await db.bookmarks.count_documents(
        {"version": {"$exists": True}}
    )
    total = without_version + with_version
    return {
        "migration": "001_add_version_field",
        "total_bookmarks": total,
        "with_version": with_version,
        "without_version": without_version,
        "all_migrated": without_version == 0,
        "percent_migrated": round(with_version / total * 100, 1) if total > 0 else 100.0,
    }
