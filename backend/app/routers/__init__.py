"""Router modules for extracted API domains."""

from app.routers.collections import router as collections_router
from app.routers.analytics import router as analytics_router
from app.routers.resurfacing import router as resurfacing_router

__all__ = ["collections_router", "analytics_router", "resurfacing_router"]
