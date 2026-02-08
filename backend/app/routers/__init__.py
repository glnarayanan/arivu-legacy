"""Router modules for extracted API domains."""

from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.collections import router as collections_router
from app.routers.resurfacing import router as resurfacing_router

__all__ = ["analytics_router", "auth_router", "collections_router", "resurfacing_router"]
