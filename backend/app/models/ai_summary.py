"""
AI Summary model - extracted from server.py (Phase 6, Plan 01).

Pydantic model for AI-generated bookmark summaries.
"""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class AISummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bookmark_id: str
    one_sentence: str | None = None
    bullet_points: list[str] = []
    long_form: str | None = None
    highlights: list[str] = []
    suggested_tags: list[str] = []
    processing_status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
