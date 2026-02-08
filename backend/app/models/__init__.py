"""Shared Pydantic models used across multiple routers."""

from app.models.bookmark import (
    Bookmark,
    BookmarkCreate,
    BookmarkWithConnections,
    QuickConnection,
)
from app.models.ai_summary import AISummary
from app.models.import_job import ImportJob, BackupRequest
from app.models.content import ContentEvaluateRequest, DuplicateCheckRequest

__all__ = [
    "Bookmark", "BookmarkCreate", "BookmarkWithConnections", "QuickConnection",
    "AISummary", "ImportJob", "BackupRequest",
    "ContentEvaluateRequest", "DuplicateCheckRequest",
]
