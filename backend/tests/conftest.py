"""
Shared test fixtures for Arivu backend tests.

Provides mock auth, mock database, test app, and async HTTP client.
Reusable across all router test modules (collections, analytics, resurfacing).
"""

import os
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-chars")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest
import pytest_asyncio
from app.core.dependencies import get_current_user
from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.bookmarks import router as bookmarks_router
from app.routers.collections import router as collections_router
from app.routers.content import router as content_router
from app.routers.import_export import router as import_export_router
from app.routers.knowledge_graph import router as knowledge_graph_router
from app.routers.resurfacing import router as resurfacing_router
from app.routers.search import router as search_router
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter storage between tests to prevent leaking state."""
    from app.core.dependencies import limiter

    limiter.reset()
    yield
    limiter.reset()


MOCK_USER = {
    "id": "test-user-id",
    "email": "test@example.com",
    "name": "Test User",
}


@pytest.fixture
def mock_user():
    return MOCK_USER.copy()


@pytest.fixture
def mock_db():
    """Create a mock MongoDB database with async collection methods."""
    db = MagicMock()

    # Collections
    db.collections = MagicMock()
    db.collections.insert_one = AsyncMock()
    db.collections.find = MagicMock()  # .find() returns cursor, needs chaining
    db.collections.find_one = AsyncMock()
    db.collections.update_one = AsyncMock()
    db.collections.update_many = AsyncMock()

    # Bookmarks (for bookmarks router + resurfacing tests)
    db.bookmarks = MagicMock()
    db.bookmarks.find = MagicMock()
    db.bookmarks.find_one = AsyncMock()
    db.bookmarks.insert_one = AsyncMock()
    db.bookmarks.update_one = AsyncMock()
    db.bookmarks.update_many = AsyncMock()
    db.bookmarks.delete_one = AsyncMock()
    db.bookmarks.delete_many = AsyncMock()

    # AI summaries (for bookmarks router + resurfacing tests)
    db.ai_summaries = MagicMock()
    db.ai_summaries.find = MagicMock()
    db.ai_summaries.find_one = AsyncMock()
    db.ai_summaries.insert_one = AsyncMock()
    db.ai_summaries.delete_one = AsyncMock()
    db.ai_summaries.delete_many = AsyncMock()

    # Users (for auth tests in Phase 5)
    db.users = MagicMock()
    db.users.find_one = AsyncMock()
    db.users.insert_one = AsyncMock()
    db.users.update_one = AsyncMock()

    # Password reset tokens (for auth tests in Phase 5)
    db.password_reset_tokens = MagicMock()
    db.password_reset_tokens.find_one = AsyncMock()
    db.password_reset_tokens.insert_one = AsyncMock()
    db.password_reset_tokens.delete_one = AsyncMock()
    db.password_reset_tokens.delete_many = AsyncMock()

    # Import jobs (for import/export router)
    db.import_jobs = MagicMock()
    db.import_jobs.find = MagicMock()
    db.import_jobs.find_one = AsyncMock()
    db.import_jobs.insert_one = AsyncMock()
    db.import_jobs.update_one = AsyncMock()
    db.import_jobs.count_documents = AsyncMock(return_value=0)

    # Notes (for backup endpoint)
    db.notes = MagicMock()
    db.notes.find = MagicMock()

    return db


@pytest.fixture
def app(mock_db):
    """Create test FastAPI app with collections router and mock dependencies."""
    test_app = FastAPI()
    api_router = APIRouter(prefix="/api")
    # import_export_router MUST be before bookmarks_router because
    # /bookmarks/import, /bookmarks/export, /bookmarks/backup must match
    # before the bookmarks router's /bookmarks/{bookmark_id} catch-all.
    api_router.include_router(import_export_router)
    api_router.include_router(content_router)
    api_router.include_router(bookmarks_router)
    api_router.include_router(collections_router)
    api_router.include_router(analytics_router)
    api_router.include_router(knowledge_graph_router)
    api_router.include_router(resurfacing_router)
    api_router.include_router(auth_router)
    api_router.include_router(search_router)
    test_app.include_router(api_router)

    # Set up rate limiter (required for auth router's slowapi decorators)
    from app.core.dependencies import limiter

    test_app.state.limiter = limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Override auth dependency
    test_app.dependency_overrides[get_current_user] = lambda: MOCK_USER

    # Override database: set module-level db variable so get_database() returns our mock
    import app.core.database as db_module

    _original_db = db_module.db
    db_module.db = mock_db

    yield test_app

    # Restore
    db_module.db = _original_db
    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP client for testing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_app(mock_db):
    """Test app for auth tests WITHOUT auth override (tests login/signup flow)."""
    test_app = FastAPI()
    api_router_local = APIRouter(prefix="/api")
    api_router_local.include_router(auth_router)
    test_app.include_router(api_router_local)

    # Set up rate limiter
    from app.core.dependencies import limiter

    test_app.state.limiter = limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Override database
    import app.core.database as db_module

    _original_db = db_module.db
    db_module.db = mock_db

    yield test_app

    db_module.db = _original_db


@pytest_asyncio.fixture
async def auth_client(auth_app):
    """Async HTTP client for auth testing (no auth override)."""
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Integration test fixtures (real MongoDB via testcontainers)
# Requires Docker daemon running. Skipped automatically if unavailable.
# Usage: pytest -m integration tests/
# Skip:  pytest -m "not integration" tests/
# ---------------------------------------------------------------------------
try:
    from motor.motor_asyncio import AsyncIOMotorClient as _RealMotorClient
    from testcontainers.mongodb import MongoDbContainer

    _TESTCONTAINERS_AVAILABLE = True
except ImportError:
    _TESTCONTAINERS_AVAILABLE = False

if _TESTCONTAINERS_AVAILABLE:

    @pytest.fixture(scope="session")
    def mongo_container():
        """Spin up MongoDB 7.0 container for the entire test session."""
        with MongoDbContainer("mongo:7.0") as mongo:
            yield mongo

    @pytest_asyncio.fixture
    async def real_db(mongo_container):
        """Per-test async database connected to real MongoDB.

        Creates production-matching indexes and drops all collections after each test.
        """
        client = _RealMotorClient(mongo_container.get_connection_url())
        db = client["test_arivu"]

        # Create indexes matching production (Phase 2 ESR pattern)
        await db.bookmarks.create_index(
            [("user_id", 1), ("created_at", -1)],
            name="idx_user_created",
            background=True,
        )
        await db.bookmarks.create_index(
            [("user_id", 1), ("url", 1)],
            unique=True,
            name="idx_user_url_unique",
            background=True,
        )

        yield db

        # Cleanup: drop all collections after each test
        for name in await db.list_collection_names():
            await db[name].drop()
        client.close()
