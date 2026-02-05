"""
Database Migration Script: Add Tracking Fields to Bookmarks

This script initializes tracking fields for all existing bookmarks in the database.
It also creates necessary indexes for optimal query performance.

Fields added:
- last_accessed: Set to created_at for existing bookmarks
- view_count: Initialized to 0
- access_history: Initialized to empty array

Run this script once before deploying the Phase 1 tracking features.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'arivu_db')


async def migrate_tracking_fields():
    """
    Migrate existing bookmarks to include tracking fields.
    This is an idempotent operation - safe to run multiple times.
    """
    print(f"Connecting to MongoDB: {MONGO_URL}")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    try:
        # Count total bookmarks
        total_bookmarks = await db.bookmarks.count_documents({})
        print(f"\nFound {total_bookmarks} bookmarks in database")

        if total_bookmarks == 0:
            print("No bookmarks to migrate. Exiting.")
            return

        # Count bookmarks missing tracking fields
        missing_last_accessed = await db.bookmarks.count_documents({
            "last_accessed": {"$exists": False}
        })
        missing_view_count = await db.bookmarks.count_documents({
            "view_count": {"$exists": False}
        })
        missing_access_history = await db.bookmarks.count_documents({
            "access_history": {"$exists": False}
        })

        print(f"\nBookmarks missing tracking fields:")
        print(f"  - last_accessed: {missing_last_accessed}")
        print(f"  - view_count: {missing_view_count}")
        print(f"  - access_history: {missing_access_history}")

        # Migration 1: Set last_accessed = created_at for bookmarks without it
        print("\n[1/3] Setting last_accessed = created_at for existing bookmarks...")

        # Use aggregation pipeline to copy created_at to last_accessed
        # Note: MongoDB update with aggregation pipeline (MongoDB 4.2+)
        result1 = await db.bookmarks.update_many(
            {"last_accessed": {"$exists": False}},
            [{"$set": {"last_accessed": "$created_at"}}]
        )
        print(f"  ✓ Updated {result1.modified_count} bookmarks")

        # Migration 2: Initialize view_count to 0
        print("\n[2/3] Initializing view_count to 0...")
        result2 = await db.bookmarks.update_many(
            {"view_count": {"$exists": False}},
            {"$set": {"view_count": 0}}
        )
        print(f"  ✓ Updated {result2.modified_count} bookmarks")

        # Migration 3: Initialize empty access_history array
        print("\n[3/3] Initializing empty access_history arrays...")
        result3 = await db.bookmarks.update_many(
            {"access_history": {"$exists": False}},
            {"$set": {"access_history": []}}
        )
        print(f"  ✓ Updated {result3.modified_count} bookmarks")

        # Verify migration
        print("\n--- Verification ---")
        bookmarks_with_tracking = await db.bookmarks.count_documents({
            "last_accessed": {"$exists": True},
            "view_count": {"$exists": True},
            "access_history": {"$exists": True}
        })
        print(f"Bookmarks with all tracking fields: {bookmarks_with_tracking}/{total_bookmarks}")

        if bookmarks_with_tracking == total_bookmarks:
            print("✓ Migration completed successfully!")
        else:
            print(f"⚠ Warning: {total_bookmarks - bookmarks_with_tracking} bookmarks still missing fields")

        # Sample a few bookmarks to show before/after
        print("\n--- Sample Bookmarks ---")
        sample_bookmarks = await db.bookmarks.find(
            {},
            {
                "_id": 0,
                "id": 1,
                "title": 1,
                "created_at": 1,
                "last_accessed": 1,
                "view_count": 1,
                "access_history": 1
            }
        ).limit(3).to_list(None)

        for i, bookmark in enumerate(sample_bookmarks, 1):
            print(f"\nBookmark {i}:")
            print(f"  ID: {bookmark.get('id', 'N/A')}")
            print(f"  Title: {bookmark.get('title', 'N/A')[:50]}...")
            print(f"  Created: {bookmark.get('created_at', 'N/A')}")
            print(f"  Last Accessed: {bookmark.get('last_accessed', 'N/A')}")
            print(f"  View Count: {bookmark.get('view_count', 'N/A')}")
            print(f"  Access History: {len(bookmark.get('access_history', []))} entries")

    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()


async def create_indexes():
    """
    Create database indexes for optimal query performance.
    """
    print("\n\n=== Creating Indexes ===")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    try:
        # Index 1: For aged bookmarks queries (user_id + last_accessed)
        print("\n[1/2] Creating index on (user_id, last_accessed)...")
        await db.bookmarks.create_index(
            [("user_id", 1), ("last_accessed", 1)],
            name="user_last_accessed_idx"
        )
        print("  ✓ Index created: user_last_accessed_idx")

        # Index 2: For sorting by view_count (user_id + view_count)
        print("\n[2/2] Creating index on (user_id, view_count)...")
        await db.bookmarks.create_index(
            [("user_id", 1), ("view_count", -1)],
            name="user_view_count_idx"
        )
        print("  ✓ Index created: user_view_count_idx")

        # List all indexes on bookmarks collection
        print("\n--- All Indexes on Bookmarks Collection ---")
        indexes = await db.bookmarks.index_information()
        for index_name, index_info in indexes.items():
            print(f"  - {index_name}: {index_info.get('key', [])}")

        print("\n✓ Index creation completed!")

    except Exception as e:
        print(f"\n❌ Error creating indexes: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


async def create_phase2_indexes():
    """
    Create Phase 2 database indexes following ESR (Equality-Sort-Range) pattern.
    These indexes optimize common query patterns for scale.

    Indexes created:
    - bookmarks.user_created_idx: User's bookmarks sorted by date (most common query)
    - bookmarks.user_read_status_created_idx: Unread bookmarks by date
    - bookmarks.user_url_unique_idx: Prevent duplicate URLs per user (UNIQUE)
    - ai_summaries.bookmark_id_idx: Primary lookup pattern for AI summaries

    This is an idempotent operation - safe to run multiple times.
    """
    print("\n" + "=" * 60)
    print("Phase 2 Index Creation: ESR-Optimized Compound Indexes")
    print("=" * 60)

    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    try:
        # Index 1: User's bookmarks sorted by date (ESR: Equality on user_id, Sort on created_at)
        print("\n[1/4] Creating index on bookmarks (user_id, created_at desc)...")
        try:
            await db.bookmarks.create_index(
                [("user_id", 1), ("created_at", -1)],
                name="user_created_idx",
                background=True
            )
            print("  ✓ Index created: user_created_idx")
        except Exception as e:
            print(f"  ⚠ Index user_created_idx: {e}")

        # Index 2: Unread bookmarks by date (ESR: Equality on user_id+read_status, Sort on created_at)
        print("\n[2/4] Creating index on bookmarks (user_id, read_status, created_at desc)...")
        try:
            await db.bookmarks.create_index(
                [("user_id", 1), ("read_status", 1), ("created_at", -1)],
                name="user_read_status_created_idx",
                background=True
            )
            print("  ✓ Index created: user_read_status_created_idx")
        except Exception as e:
            print(f"  ⚠ Index user_read_status_created_idx: {e}")

        # Index 3: Unique URL per user (prevents duplicates)
        print("\n[3/4] Creating unique index on bookmarks (user_id, url)...")
        try:
            await db.bookmarks.create_index(
                [("user_id", 1), ("url", 1)],
                name="user_url_unique_idx",
                unique=True,
                background=True
            )
            print("  ✓ Index created: user_url_unique_idx (UNIQUE)")
        except Exception as e:
            print(f"  ⚠ Index user_url_unique_idx: {e}")

        # Index 4: AI summaries lookup by bookmark_id
        print("\n[4/4] Creating index on ai_summaries (bookmark_id)...")
        try:
            await db.ai_summaries.create_index(
                [("bookmark_id", 1)],
                name="bookmark_id_idx",
                background=True
            )
            print("  ✓ Index created: bookmark_id_idx")
        except Exception as e:
            print(f"  ⚠ Index bookmark_id_idx: {e}")

        # List all indexes on bookmarks collection
        print("\n--- All Indexes on Bookmarks Collection ---")
        indexes = await db.bookmarks.index_information()
        for index_name, index_info in indexes.items():
            unique_marker = " (UNIQUE)" if index_info.get('unique', False) else ""
            print(f"  - {index_name}: {index_info.get('key', [])}{unique_marker}")

        # List all indexes on ai_summaries collection
        print("\n--- All Indexes on AI Summaries Collection ---")
        indexes = await db.ai_summaries.index_information()
        for index_name, index_info in indexes.items():
            print(f"  - {index_name}: {index_info.get('key', [])}")

        print("\n" + "=" * 60)
        print("✓ Phase 2 Index Creation Complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during Phase 2 index creation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


async def main():
    """
    Main migration function.
    """
    print("=" * 60)
    print("Phase 1 Migration: Bookmark Tracking Fields")
    print("=" * 60)

    # Run migrations
    await migrate_tracking_fields()

    # Create indexes
    await create_indexes()

    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Deploy updated backend code with new endpoints")
    print("2. Deploy updated frontend code with aging indicators")
    print("3. Monitor for any issues in production logs")
    print("\n")


if __name__ == "__main__":
    if "--phase2-indexes" in sys.argv:
        # Run only Phase 2 index creation
        asyncio.run(create_phase2_indexes())
    elif "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python migrate_tracking_fields.py [OPTIONS]")
        print("")
        print("Options:")
        print("  (no args)         Run Phase 1 data migration + indexes")
        print("  --phase2-indexes  Run Phase 2 index creation only")
        print("  --help, -h        Show this help message")
    else:
        # Default: Run Phase 1 migration
        asyncio.run(main())
