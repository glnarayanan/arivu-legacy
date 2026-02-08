"""
Migration runner CLI.

Usage:
    python -m migrations.runner apply 001_add_version_field [--mongo-url mongodb://localhost:27017] [--db-name arivu]
    python -m migrations.runner rollback 001_add_version_field [--mongo-url ...]
    python -m migrations.runner verify 001_add_version_field [--mongo-url ...]

Before running migrations on production:
    1. Create a backup: mongodump --uri="mongodb://..." --db=arivu --out=/backup/$(date +%Y%m%d)
    2. Run verify first to check current state
    3. Apply the migration
    4. Run verify again to confirm
    5. If issues found, run rollback then restore from backup
"""
import asyncio
import argparse
import importlib
import logging
import sys

from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_migration(name: str):
    """Dynamically import a migration module by name."""
    try:
        module = importlib.import_module(f"migrations.{name}")
    except ImportError as e:
        logger.error(f"Migration '{name}' not found: {e}")
        sys.exit(1)
    return module


async def run_action(action: str, migration_name: str, mongo_url: str, db_name: str):
    """Run a migration action (apply, rollback, or verify)."""
    module = load_migration(migration_name)

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    try:
        if action == "apply":
            if not hasattr(module, "upgrade"):
                logger.error(f"Migration '{migration_name}' has no upgrade() function")
                sys.exit(1)
            result = await module.upgrade(db)
        elif action == "rollback":
            if not hasattr(module, "downgrade"):
                logger.error(f"Migration '{migration_name}' has no downgrade() function")
                sys.exit(1)
            result = await module.downgrade(db)
        elif action == "verify":
            if not hasattr(module, "verify"):
                logger.error(f"Migration '{migration_name}' has no verify() function")
                sys.exit(1)
            result = await module.verify(db)
        else:
            logger.error(f"Unknown action: {action}")
            sys.exit(1)

        logger.info(f"Result: {result}")
        return result
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument("action", choices=["apply", "rollback", "verify"],
                        help="Migration action to perform")
    parser.add_argument("migration", help="Migration name (e.g., 001_add_version_field)")
    parser.add_argument("--mongo-url", default="mongodb://localhost:27017",
                        help="MongoDB connection URL (default: mongodb://localhost:27017)")
    parser.add_argument("--db-name", default="arivu",
                        help="Database name (default: arivu)")
    args = parser.parse_args()

    asyncio.run(run_action(args.action, args.migration, args.mongo_url, args.db_name))


if __name__ == "__main__":
    main()
