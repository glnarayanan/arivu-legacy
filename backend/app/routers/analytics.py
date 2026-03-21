"""
Analytics domain router - extracted from server.py (Phase 4, Plan 02).

Thin delegation layer to analytics.py business logic.
Provides reading stats, topic breakdown, patterns, insights, and summary.
"""

from analytics import (
    calculate_reading_stats,
    get_learning_insights,
    get_reading_patterns,
    get_topic_breakdown,
)
from fastapi import APIRouter, Depends

from app.core.database import get_database
from app.core.dependencies import get_current_user

router = APIRouter(tags=["analytics"])


@router.get("/analytics/reading-stats")
async def get_analytics_reading_stats(days: int = 30, current_user: dict = Depends(get_current_user)):
    """Get reading statistics for the user."""
    db = get_database()
    stats = await calculate_reading_stats(current_user["id"], days, db)
    return stats


@router.get("/analytics/topics")
async def get_analytics_topics(days: int = 30, current_user: dict = Depends(get_current_user)):
    """Get topic breakdown based on AI-suggested tags."""
    db = get_database()
    topics = await get_topic_breakdown(current_user["id"], days, db)
    return {"topics": topics}


@router.get("/analytics/patterns")
async def get_analytics_patterns(days: int = 30, current_user: dict = Depends(get_current_user)):
    """Get reading patterns (time of day, day of week)."""
    db = get_database()
    patterns = await get_reading_patterns(current_user["id"], days, db)
    return patterns


@router.get("/analytics/insights")
async def get_analytics_insights(
    current_user: dict = Depends(get_current_user),
):
    """Get behavioral insights and recommendations."""
    db = get_database()
    insights = await get_learning_insights(current_user["id"], db)
    return {"insights": insights}


@router.get("/analytics/summary")
async def get_analytics_summary(days: int = 30, current_user: dict = Depends(get_current_user)):
    """Get complete analytics summary (stats + topics + patterns + insights)."""
    db = get_database()
    stats = await calculate_reading_stats(current_user["id"], days, db)
    topics = await get_topic_breakdown(current_user["id"], days, db)
    patterns = await get_reading_patterns(current_user["id"], days, db)
    insights = await get_learning_insights(current_user["id"], db)

    return {
        "stats": stats,
        "topics": topics,
        "patterns": patterns,
        "insights": insights,
    }
