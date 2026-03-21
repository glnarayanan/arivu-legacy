"""
Content evaluation models - extracted from server.py (Phase 6, Plan 01).

Pydantic models for content quality evaluation and duplicate checking.
"""

from pydantic import BaseModel


class ContentEvaluateRequest(BaseModel):
    url: str
    content: str | None = None
    metadata: dict | None = None


class DuplicateCheckRequest(BaseModel):
    url: str
