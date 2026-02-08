"""
Content router - extracted from server.py (Phase 6, Plan 03).

Provides content quality evaluation and duplicate URL checking endpoints.
"""

import logging

from fastapi import APIRouter, Depends

from app.core.database import get_database
from app.core.dependencies import get_current_user
from app.models.content import ContentEvaluateRequest, DuplicateCheckRequest
from content_intelligence import (
    calculate_credibility_score,
    check_duplicate_url,
    get_quality_badges,
    get_quality_label,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["content"])


@router.post("/content/evaluate")
async def evaluate_content(
    request_data: ContentEvaluateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Evaluate content quality before saving.
    Returns credibility score, quality label, and badges.
    """
    score, breakdown = calculate_credibility_score(
        request_data.url, request_data.content, request_data.metadata
    )

    label, severity = get_quality_label(score)
    badges = get_quality_badges(breakdown)

    return {
        "score": score,
        "label": label,
        "severity": severity,
        "badges": badges,
        "breakdown": breakdown,
    }


@router.post("/content/check-duplicate")
async def check_duplicate(
    request_data: DuplicateCheckRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Check if URL already exists for this user before saving.
    Returns duplicate status and existing bookmark if found.
    """
    db = get_database()
    result = await check_duplicate_url(request_data.url, current_user["id"], db)

    return result
