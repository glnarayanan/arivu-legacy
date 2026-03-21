"""
Database module for MongoDB connection management.

Provides async MongoDB client with proper connection pooling.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

# Global client and database references
client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


def init_db() -> AsyncIOMotorDatabase:
    """
    Initialize MongoDB connection.

    Creates AsyncIOMotorClient with optimized settings for production use.

    Returns:
        AsyncIOMotorDatabase: The database instance
    """
    global client, db

    client = AsyncIOMotorClient(
        settings.MONGO_URL,
        serverSelectionTimeoutMS=5000,  # 5 second timeout for server selection
        connectTimeoutMS=10000,  # 10 second timeout for initial connection
        socketTimeoutMS=30000,  # 30 second timeout for socket operations
        maxPoolSize=50,  # Limit connection pool size
        maxIdleTimeMS=45000,  # Close idle connections after 45 seconds
        waitQueueTimeoutMS=10000,  # 10 second timeout waiting for connection from pool
        retryWrites=True,  # Enable retry for write operations
        retryReads=True,  # Enable retry for read operations
    )
    db = client[settings.DB_NAME]

    return db


def close_db() -> None:
    """Close MongoDB connection."""
    global client, db

    if client is not None:
        client.close()
        client = None
        db = None


def get_database() -> AsyncIOMotorDatabase:
    """
    Get the database instance.

    Raises:
        RuntimeError: If database is not initialized

    Returns:
        AsyncIOMotorDatabase: The database instance
    """
    if db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return db
