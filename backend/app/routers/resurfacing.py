"""
Resurfacing + Memory Jogger router - extracted from server.py (Phase 4, Plan 02).

Surfaces forgotten bookmarks at optimal times using scoring algorithm.
Includes snooze/archive management and daily featured bookmark (Memory Jogger).
"""

import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from resurfacing import (
    calculate_resurfacing_score,
    get_resurfacing_reason,
    should_resurface,
)

from app.core.database import get_database
from app.core.dependencies import get_current_user

UTC = timezone.utc

router = APIRouter(tags=["resurfacing"])


# --- Pydantic Models ---


class SnoozeRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=90, description="Number of days to snooze")


class MemoryJoggerDismissRequest(BaseModel):
    bookmark_id: str = Field(..., description="The bookmark ID to dismiss")


# --- Helper Functions ---


async def get_recent_connections(user_id: str, bookmark_embedding: list, days: int = 7, threshold: float = 0.6) -> dict:
    """
    Find bookmarks saved in last N days that are semantically related.
    Returns connection count and topics.
    """
    import numpy as np

    db = get_database()
    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    recent_bookmarks = await db.bookmarks.find(
        {
            "user_id": user_id,
            "created_at": {"$gte": cutoff_date.isoformat()},
            "embedding": {"$exists": True, "$ne": None},
        },
        {"_id": 0, "id": 1, "embedding": 1, "title": 1},
    ).to_list(100)

    if not recent_bookmarks or not bookmark_embedding:
        return {"count": 0, "topics": []}

    def cosine_similarity_score(vec1, vec2):
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    connected_titles = []
    for bm in recent_bookmarks:
        if bm.get("embedding"):
            similarity = cosine_similarity_score(bookmark_embedding, bm["embedding"])
            if similarity >= threshold:
                connected_titles.append(bm.get("title", ""))

    topics = []
    for title in connected_titles[:5]:
        words = title.split()[:3] if title else []
        if words:
            topics.append(" ".join(words))

    return {"count": len(connected_titles), "topics": topics[:3]}


def calculate_connections_batch(
    target_embedding: list,
    recent_bookmarks: list,
    threshold: float = 0.6,
) -> dict:
    """
    Calculate semantic connections entirely in-memory.
    No database queries - works on pre-loaded bookmark data.

    Args:
        target_embedding: The embedding to compare against
        recent_bookmarks: List of dicts with 'embedding' and 'title' keys
        threshold: Cosine similarity threshold (default 0.6)

    Returns:
        dict with 'count' and 'topics' keys
    """
    import numpy as np

    if not target_embedding or not recent_bookmarks:
        return {"count": 0, "topics": []}

    target = np.array(target_embedding)
    target_norm = np.linalg.norm(target)
    if target_norm == 0:
        return {"count": 0, "topics": []}

    connections = []
    for bm in recent_bookmarks:
        embedding = bm.get("embedding")
        if embedding:
            other = np.array(embedding)
            other_norm = np.linalg.norm(other)
            if other_norm > 0:
                similarity = float(np.dot(target, other) / (target_norm * other_norm))
                if similarity >= threshold:
                    connections.append(bm.get("title", ""))

    # Extract topic keywords from connected bookmark titles
    topics = [" ".join(t.split()[:3]) for t in connections[:5] if t]
    return {"count": len(connections), "topics": topics[:3]}


# --- Endpoints ---


@router.get("/resurfacing")
async def get_resurfacing_suggestions(limit: int = 5, current_user: dict = Depends(get_current_user)):
    """
    Get top resurfacing suggestions for the user.
    Returns bookmarks scored by age, engagement, content quality, and spaced repetition.
    """
    db = get_database()

    # Get all user bookmarks with necessary fields
    projection = {
        "_id": 0,
        "id": 1,
        "title": 1,
        "url": 1,
        "domain": 1,
        "thumbnail": 1,
        "favicon": 1,
        "description": 1,
        "reading_time": 1,
        "created_at": 1,
        "last_accessed": 1,
        "view_count": 1,
        "resurfacing_snoozed_until": 1,
        "resurfacing_archived": 1,
    }

    bookmarks = await db.bookmarks.find({"user_id": current_user["id"]}, projection).to_list(
        500
    )  # Cap at 500 for performance

    # Get AI summaries for all bookmarks
    bookmark_ids = [b["id"] for b in bookmarks]
    summaries = await db.ai_summaries.find({"bookmark_id": {"$in": bookmark_ids}}, {"_id": 0}).to_list(None)
    summary_map = {s["bookmark_id"]: s for s in summaries}

    # Score each bookmark
    scored_bookmarks = []
    current_time = datetime.now(UTC)

    for bookmark in bookmarks:
        if not should_resurface(bookmark):
            continue

        ai_summary = summary_map.get(bookmark["id"])
        score, breakdown = calculate_resurfacing_score(bookmark, ai_summary, current_time)

        # Calculate days since access for reason generation
        last_accessed = bookmark.get("last_accessed")
        if isinstance(last_accessed, str):
            try:
                last_accessed = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                last_accessed = None

        if last_accessed:
            if last_accessed.tzinfo is None:
                last_accessed = last_accessed.replace(tzinfo=UTC)
            days_since = (current_time - last_accessed).days
        else:
            days_since = 30  # Default

        reason = get_resurfacing_reason(bookmark, breakdown, days_since)

        # Build response object
        scored_bookmarks.append(
            {
                **bookmark,
                "resurfacing_score": score,
                "resurfacing_reason": reason,
                "days_since_access": days_since,
                "ai_summary": ai_summary,
            }
        )

    # Sort by score descending and take top N
    scored_bookmarks.sort(key=lambda x: x["resurfacing_score"], reverse=True)
    top_suggestions = scored_bookmarks[:limit]

    # Remove internal fields before returning
    for bm in top_suggestions:
        bm.pop("resurfacing_snoozed_until", None)
        bm.pop("resurfacing_archived", None)

    return {"suggestions": top_suggestions, "total_candidates": len(scored_bookmarks)}


@router.post("/resurfacing/{bookmark_id}/snooze")
async def snooze_resurfacing(
    bookmark_id: str,
    snooze_data: SnoozeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Snooze a bookmark from resurfacing suggestions for N days."""
    db = get_database()

    # Verify ownership
    bookmark = await db.bookmarks.find_one({"id": bookmark_id, "user_id": current_user["id"]})
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    snooze_until = datetime.now(UTC) + timedelta(days=snooze_data.days)

    await db.bookmarks.update_one(
        {"id": bookmark_id},
        {
            "$set": {
                "resurfacing_snoozed_until": snooze_until.isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
        },
    )

    return {
        "message": f"Bookmark snoozed for {snooze_data.days} days",
        "snoozed_until": snooze_until.isoformat(),
    }


@router.post("/resurfacing/{bookmark_id}/archive")
async def archive_from_resurfacing(bookmark_id: str, current_user: dict = Depends(get_current_user)):
    """Archive a bookmark from resurfacing suggestions (never show again)."""
    db = get_database()

    # Verify ownership
    bookmark = await db.bookmarks.find_one({"id": bookmark_id, "user_id": current_user["id"]})
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.bookmarks.update_one(
        {"id": bookmark_id},
        {
            "$set": {
                "resurfacing_archived": True,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        },
    )

    return {"message": "Bookmark archived from resurfacing"}


@router.post("/resurfacing/{bookmark_id}/unarchive")
async def unarchive_from_resurfacing(bookmark_id: str, current_user: dict = Depends(get_current_user)):
    """Unarchive a bookmark to allow it back in resurfacing suggestions."""
    db = get_database()

    # Verify ownership
    bookmark = await db.bookmarks.find_one({"id": bookmark_id, "user_id": current_user["id"]})
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.bookmarks.update_one(
        {"id": bookmark_id},
        {
            "$set": {
                "resurfacing_archived": False,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        },
    )

    return {"message": "Bookmark unarchived from resurfacing"}


@router.get("/memory-jogger")
async def get_memory_jogger(current_user: dict = Depends(get_current_user)):
    """
    Get a single featured bookmark for today's memory jogger.
    Uses scoring algorithm to surface forgotten but relevant bookmarks.
    """
    db = get_database()
    current_time = datetime.now(UTC)
    seven_days_ago = current_time - timedelta(days=7)

    query = {
        "user_id": current_user["id"],
        "$or": [
            {"last_accessed": {"$lt": seven_days_ago.isoformat()}},
            {"last_accessed": {"$exists": False}},
        ],
        "$and": [
            {
                "$or": [
                    {"resurfacing_snoozed_until": {"$exists": False}},
                    {"resurfacing_snoozed_until": None},
                    {"resurfacing_snoozed_until": {"$lt": current_time.isoformat()}},
                ]
            },
            {
                "$or": [
                    {"resurfacing_archived": {"$exists": False}},
                    {"resurfacing_archived": False},
                ]
            },
        ],
    }

    projection = {
        "_id": 0,
        "id": 1,
        "title": 1,
        "url": 1,
        "domain": 1,
        "favicon": 1,
        "thumbnail": 1,
        "description": 1,
        "created_at": 1,
        "last_accessed": 1,
        "embedding": 1,
    }

    bookmarks = await db.bookmarks.find(query, projection).limit(200).to_list(None)

    if not bookmarks:
        return {
            "bookmark": None,
            "context": None,
            "has_memory": False,
            "message": "Save more bookmarks to unlock daily memories",
        }

    bookmark_ids = [b["id"] for b in bookmarks]
    summaries = await db.ai_summaries.find(
        {"bookmark_id": {"$in": bookmark_ids}, "processing_status": "completed"},
        {"_id": 0, "bookmark_id": 1},
    ).to_list(None)
    summary_set = {s["bookmark_id"] for s in summaries}

    # Load recent bookmarks with embeddings for connection scoring (single query)
    recent_with_embeddings = await db.bookmarks.find(
        {
            "user_id": current_user["id"],
            "created_at": {"$gte": seven_days_ago.isoformat()},
            "embedding": {"$exists": True, "$ne": None},
        },
        {"_id": 0, "id": 1, "embedding": 1, "title": 1},
    ).to_list(None)

    # Calculate connections in-memory (no database queries in loop)
    related_counts = {}
    for bm in bookmarks:
        if bm.get("embedding"):
            conn_data = calculate_connections_batch(
                bm["embedding"],
                recent_with_embeddings,
                threshold=0.6,
            )
            related_counts[bm["id"]] = conn_data

    scored_bookmarks = []
    for bm in bookmarks:
        score = 0

        conn_data = related_counts.get(bm["id"], {"count": 0, "topics": []})
        if conn_data["count"] > 0:
            score += 30

        last_accessed = bm.get("last_accessed")
        days_since_accessed = 30
        if last_accessed:
            try:
                if isinstance(last_accessed, str):
                    last_accessed_dt = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
                else:
                    last_accessed_dt = last_accessed
                if last_accessed_dt.tzinfo is None:
                    last_accessed_dt = last_accessed_dt.replace(tzinfo=UTC)
                days_since_accessed = (current_time - last_accessed_dt).days
            except (ValueError, TypeError):
                days_since_accessed = 30

        if days_since_accessed >= 30:
            score += 20

        if bm["id"] in summary_set:
            score += 10

        # Use pre-loaded recent_with_embeddings count (no per-bookmark query)
        if len(recent_with_embeddings) >= 3:
            score += 5

        score += random.randint(0, 15)

        scored_bookmarks.append(
            {
                "bookmark": bm,
                "score": score,
                "days_since_accessed": days_since_accessed,
                "conn_data": conn_data,
            }
        )

    scored_bookmarks.sort(key=lambda x: x["score"], reverse=True)
    top = scored_bookmarks[0]
    selected_bookmark = top["bookmark"]

    created_at = selected_bookmark.get("created_at")
    days_since_saved = 0
    if created_at:
        try:
            if isinstance(created_at, str):
                created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                created_at_dt = created_at
            if created_at_dt.tzinfo is None:
                created_at_dt = created_at_dt.replace(tzinfo=UTC)
            days_since_saved = (current_time - created_at_dt).days
        except (ValueError, TypeError):
            days_since_saved = 0

    conn_data = top["conn_data"]
    connection_count = conn_data["count"]
    connected_topics = conn_data["topics"]

    if connection_count > 0:
        reason = f"Connects to {connection_count} bookmark{'s' if connection_count > 1 else ''} you saved this week"
        if connected_topics:
            reason += f" about {', '.join(connected_topics[:2])}"
    elif top["days_since_accessed"] >= 30:
        reason = f"You haven't visited this in {top['days_since_accessed']} days"
    else:
        reason = "A forgotten gem from your collection"

    ai_summary = await db.ai_summaries.find_one({"bookmark_id": selected_bookmark["id"]}, {"_id": 0})

    selected_bookmark.pop("embedding", None)

    return {
        "bookmark": {
            **selected_bookmark,
            "ai_summary": ai_summary,
        },
        "context": {
            "days_since_saved": days_since_saved,
            "days_since_accessed": top["days_since_accessed"],
            "connection_count": connection_count,
            "connected_topics": connected_topics,
            "reason": reason,
        },
        "has_memory": True,
    }


@router.post("/memory-jogger/dismiss")
async def dismiss_memory_jogger(
    request: MemoryJoggerDismissRequest,
    current_user: dict = Depends(get_current_user),
):
    """Dismiss today's memory jogger. Records dismissal for analytics."""
    db = get_database()

    bookmark = await db.bookmarks.find_one({"id": request.bookmark_id, "user_id": current_user["id"]})
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.bookmarks.update_one(
        {"id": request.bookmark_id},
        {
            "$set": {
                "memory_jogger_dismissed_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
        },
    )

    return {"message": "Memory jogger dismissed", "bookmark_id": request.bookmark_id}
UTC = timezone.utc
