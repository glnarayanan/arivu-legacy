"""
Import job and backup models - extracted from server.py (Phase 6, Plan 01).

Pydantic models for bookmark import/export operations.
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

UTC = timezone.utc


class BackupRequest(BaseModel):
    format: str = "html"  # "html" | "json" | "csv"
    include_notes: bool = True
    include_ai_summaries: bool = True
    date_from: datetime | None = None
    date_to: datetime | None = None


class ImportJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    total_bookmarks: int
    content_fetched: int = 0
    ai_processed: int = 0
    failed: int = 0
    status: str = "processing"  # processing, completed, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    estimated_completion_time: datetime | None = None
