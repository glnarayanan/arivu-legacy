"""
Content evaluation models - extracted from server.py (Phase 6, Plan 01).

Pydantic models for content quality evaluation and duplicate checking.
"""

from typing import Dict, Optional

from pydantic import BaseModel


class ContentEvaluateRequest(BaseModel):
    url: str
    content: Optional[str] = None
    metadata: Optional[Dict] = None


class DuplicateCheckRequest(BaseModel):
    url: str
