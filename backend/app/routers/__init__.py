"""Router modules for extracted API domains."""

from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.bookmarks import router as bookmarks_router
from app.routers.collections import router as collections_router
from app.routers.content import router as content_router
from app.routers.import_export import router as import_export_router
from app.routers.knowledge_graph import router as knowledge_graph_router
from app.routers.resurfacing import router as resurfacing_router
from app.routers.search import router as search_router

__all__ = [
    "analytics_router",
    "auth_router",
    "bookmarks_router",
    "collections_router",
    "content_router",
    "import_export_router",
    "knowledge_graph_router",
    "resurfacing_router",
    "search_router",
]
