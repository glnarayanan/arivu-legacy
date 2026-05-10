"""
Bookmarks router - extracted from server.py (Phase 6, Plan 01).

Manages bookmark CRUD, read status, access tracking, duplicate detection,
and related bookmarks via embedding similarity.
"""

import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.database import get_database
from app.core.dependencies import get_current_user, get_user_identifier, limiter
from app.models.bookmark import (
    Bookmark,
    BookmarkCreate,
    BookmarkWithConnections,
    QuickConnection,
    is_safe_url,
)
from app.services.content_service import (
    calculate_reading_time,
    fetch_webpage_content,
    process_bookmark_content,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["bookmarks"])

# Minimum semantic similarity score for related bookmarks
MIN_SEMANTIC_SCORE = 0.3


class BookmarkPreviewRequest(BaseModel):
    url: str


# --- Helper Functions ---


async def find_quick_connections(
    bookmark_id: str,
    url: str,
    domain: str,
    title: str,
    user_id: str,
    limit: int = 5,
) -> list[QuickConnection]:
    """
    Find related bookmarks quickly (before embeddings are generated).

    Strategy (fast, no embedding needed):
    1. Domain match: Other bookmarks from same domain
    """
    db = get_database()
    connections = []

    if not domain:
        return connections

    domain_matches = (
        await db.bookmarks.find(
            {
                "user_id": user_id,
                "domain": domain,
                "id": {"$ne": bookmark_id},
            },
            {"_id": 0, "id": 1, "title": 1, "domain": 1, "favicon": 1},
        )
        .sort("created_at", -1)
        .limit(limit)
        .to_list(None)
    )

    for bm in domain_matches:
        connections.append(
            QuickConnection(
                id=bm["id"],
                title=bm.get("title"),
                domain=bm.get("domain"),
                favicon=bm.get("favicon"),
                connection_type="same_domain",
                connection_reason=f"Also from {domain}",
            )
        )

    return connections[:limit]


# --- Endpoints ---


@router.post("/bookmarks", response_model=BookmarkWithConnections)
@limiter.limit("20/minute")  # IP-based rate limiting
@limiter.limit("100/hour", key_func=get_user_identifier)  # User-based rate limiting
async def create_bookmark(
    request: Request,
    bookmark_data: BookmarkCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    parsed_url = urlparse(bookmark_data.url)

    bookmark = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "url": bookmark_data.url,
        "title": parsed_url.netloc or "Loading...",
        "description": None,
        "favicon": None,
        "thumbnail": None,
        "html_content": None,
        "text_content": None,
        "domain": parsed_url.netloc,
        "reading_time": None,
        "read_status": False,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "version": 1,  # Optimistic locking (REL-03)
    }

    await db.bookmarks.insert_one(bookmark)

    ai_summary = {
        "id": str(uuid.uuid4()),
        "bookmark_id": bookmark["id"],
        "processing_status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
    }
    await db.ai_summaries.insert_one(ai_summary)

    background_tasks.add_task(
        process_bookmark_content,
        bookmark["id"],
        bookmark_data.url,
        bookmark_data.collection_id,
        current_user["id"],
    )

    if bookmark_data.collection_id:
        await db.collections.update_one(
            {"id": bookmark_data.collection_id, "user_id": current_user["id"]},
            {"$addToSet": {"bookmark_ids": bookmark["id"]}},
        )

    connections = await find_quick_connections(
        bookmark_id=bookmark["id"],
        url=bookmark_data.url,
        domain=parsed_url.netloc,
        title=bookmark.get("title", ""),
        user_id=current_user["id"],
        limit=5,
    )

    return BookmarkWithConnections(
        bookmark=Bookmark(**bookmark),
        connections=connections,
        connections_count=len(connections),
    )


@router.post("/bookmarks/preview")
@limiter.limit("20/minute")
async def preview_bookmark(
    request: Request,
    preview_data: BookmarkPreviewRequest,
    current_user: dict = Depends(get_current_user),
):
    """Fetch safe metadata for a URL before saving it."""
    safe, error_msg = is_safe_url(preview_data.url, resolve_host=True)
    if not safe:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        content = await fetch_webpage_content(preview_data.url, raise_on_error=True)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    return {
        "url": content.get("url") or preview_data.url,
        "title": content.get("title") or urlparse(preview_data.url).netloc,
        "description": content.get("description") or "",
        "domain": content.get("domain") or urlparse(preview_data.url).netloc,
        "favicon": content.get("favicon"),
        "thumbnail": content.get("thumbnail"),
        "reading_time": calculate_reading_time(content.get("text_content", "")),
    }


@router.get("/bookmarks", response_model=list[dict])
async def get_bookmarks(
    search: str | None = None,
    tag: str | None = None,
    domain: str | None = None,
    collection_id: str | None = None,
    read_status: str | None = None,
    source: str | None = None,
    sort_by: str | None = "created_at",
    limit: int | None = 100,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    query = {"user_id": current_user["id"]}

    if domain:
        query["domain"] = domain

    if source == "web":
        query["$or"] = [{"source": "web"}, {"source": {"$exists": False}}]
    elif source == "x":
        query["source"] = "x"

    if read_status == "read":
        query["read_status"] = True
    elif read_status == "unread":
        query["read_status"] = False

    if collection_id:
        collection = await db.collections.find_one({"id": collection_id}, {"_id": 0, "bookmark_ids": 1})
        if collection:
            query["id"] = {"$in": collection.get("bookmark_ids", [])}

    sort_field = "created_at"
    sort_order = -1
    if sort_by == "reading_time":
        sort_field = "reading_time"
        sort_order = 1
    elif sort_by == "title":
        sort_field = "title"
        sort_order = 1

    projection = {
        "_id": 0,
        "id": 1,
        "url": 1,
        "title": 1,
        "description": 1,
        "domain": 1,
        "thumbnail": 1,
        "favicon": 1,
        "reading_time": 1,
        "read_status": 1,
        "created_at": 1,
        "updated_at": 1,
        "last_accessed": 1,  # Phase 1: For aging indicators
        "view_count": 1,  # Phase 1: For usage tracking
        "source": 1,
        "x_tweet_id": 1,
        "x_author_username": 1,
        "x_author_name": 1,
        "x_tweet_url": 1,
        "x_metrics": 1,
        "version": 1,  # Optimistic locking (REL-03)
    }

    bookmarks = (
        await db.bookmarks.find(query, projection).sort(sort_field, sort_order).limit(min(limit, 1000)).to_list(None)
    )

    # Improved search: use keyword matching across multiple fields
    # For full hybrid search with semantic, use the /api/search endpoint
    if search:
        search_lower = search.lower()

        def matches_search(b: dict) -> bool:
            """Check if bookmark matches search query."""
            title = (b.get("title") or "").lower()
            description = (b.get("description") or "").lower()
            url = (b.get("url") or "").lower()
            domain_val = (b.get("domain") or "").lower()
            return (
                search_lower in title
                or search_lower in description
                or search_lower in url
                or search_lower in domain_val
            )

        bookmarks = [b for b in bookmarks if matches_search(b)]

    bookmark_ids = [b["id"] for b in bookmarks]
    summaries = await db.ai_summaries.find({"bookmark_id": {"$in": bookmark_ids}}, {"_id": 0}).to_list(None)

    summary_map = {s["bookmark_id"]: s for s in summaries}

    result = []
    for bookmark in bookmarks:
        summary = summary_map.get(bookmark["id"])

        if tag and summary:
            if tag.lower() not in [t.lower() for t in summary.get("suggested_tags", [])]:
                continue

        bookmark_with_summary = {**bookmark}
        # Graceful degradation for AI summary (REL-03)
        if summary and summary.get("processing_status") == "failed":
            bookmark_with_summary["ai_summary"] = {
                "processing_status": "failed",
                "one_sentence": summary.get("one_sentence", "AI summary temporarily unavailable"),
                "suggested_tags": summary.get("suggested_tags", []),
            }
        elif summary:
            bookmark_with_summary["ai_summary"] = summary
        result.append(bookmark_with_summary)

    return result


# Phase 1: Aged Bookmarks Endpoint (MUST be before /{bookmark_id} to avoid route collision)
@router.get("/bookmarks/aged")
async def get_aged_bookmarks(
    min_days: int = 30,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
):
    """
    Get count and list of bookmarks not accessed in min_days.
    Used for aged bookmarks banner.
    """
    db = get_database()
    cutoff_date = datetime.now(UTC) - timedelta(days=min_days)

    query = {
        "user_id": current_user["id"],
        "$or": [
            {"last_accessed": {"$lt": cutoff_date.isoformat()}},
            {"last_accessed": {"$exists": False}},  # Unmigrated bookmarks
        ],
    }

    projection = {
        "_id": 0,
        "id": 1,
        "title": 1,
        "url": 1,
        "domain": 1,
        "thumbnail": 1,
        "created_at": 1,
        "last_accessed": 1,
        "view_count": 1,
    }

    bookmarks = await db.bookmarks.find(query, projection).sort("last_accessed", 1).limit(limit).to_list(None)

    return {"count": len(bookmarks), "bookmarks": bookmarks}


@router.get("/bookmarks/duplicates/detect")
async def detect_duplicates(current_user: dict = Depends(get_current_user)):
    """Detect duplicate bookmarks using URL matching and embedding similarity (PERF-03)."""
    import numpy as np

    db = get_database()
    projection = {
        "_id": 0,
        "id": 1,
        "url": 1,
        "title": 1,
        "domain": 1,
        "created_at": 1,
        "thumbnail": 1,
        "favicon": 1,
        "embedding": 1,  # Fetch embeddings instead of text_content
    }
    bookmarks = await db.bookmarks.find({"user_id": current_user["id"]}, projection).limit(500).to_list(None)

    # URL-based exact duplicates (preserve existing logic)
    url_groups = {}
    for bookmark in bookmarks:
        normalized_url = re.sub(r"(\?|#).*$", "", bookmark["url"]).lower().strip("/")
        if normalized_url not in url_groups:
            url_groups[normalized_url] = []
        url_groups[normalized_url].append(bookmark)

    duplicates = []
    for group in url_groups.values():
        if len(group) > 1:
            # Strip embeddings from response (large arrays, not needed in output)
            clean_group = [{k: v for k, v in b.items() if k != "embedding"} for b in group]
            duplicates.append({"type": "exact_url", "bookmarks": clean_group})

    # Embedding-based similarity detection (replaces TF-IDF) (PERF-03)
    embeddings = []
    indexed_bookmarks = []
    for b in bookmarks:
        if b.get("embedding"):
            embeddings.append(b["embedding"])
            indexed_bookmarks.append(b)

    if len(embeddings) > 1:
        try:
            matrix = np.array(embeddings)
            # Dot product = cosine similarity (embeddings are L2-normalized)
            similarity_matrix = np.dot(matrix, matrix.T)

            for i in range(len(indexed_bookmarks)):
                for j in range(i + 1, len(indexed_bookmarks)):
                    if similarity_matrix[i][j] > 0.85:
                        # Strip embeddings from response
                        b_i = {k: v for k, v in indexed_bookmarks[i].items() if k != "embedding"}
                        b_j = {k: v for k, v in indexed_bookmarks[j].items() if k != "embedding"}
                        duplicates.append(
                            {
                                "type": "similar_content",
                                "similarity": float(similarity_matrix[i][j]),
                                "bookmarks": [b_i, b_j],
                            }
                        )
        except Exception:
            logger.exception("Error in embedding-based duplicate detection")

    return {"duplicates": duplicates}


@router.get("/bookmarks/{bookmark_id}")
async def get_bookmark(bookmark_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    bookmark = await db.bookmarks.find_one({"id": bookmark_id, "user_id": current_user["id"]}, {"_id": 0})
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    summary = await db.ai_summaries.find_one({"bookmark_id": bookmark_id}, {"_id": 0})

    result = {**bookmark}
    # Graceful degradation for AI summary (REL-03)
    if not summary:
        result["ai_summary"] = {
            "processing_status": "pending",
            "one_sentence": "Processing...",
            "suggested_tags": [],
        }
    elif summary.get("processing_status") == "failed":
        result["ai_summary"] = {
            "processing_status": "failed",
            "one_sentence": summary.get("one_sentence", "AI summary temporarily unavailable"),
            "exec_summary": summary.get("exec_summary", ""),
            "highlights": summary.get("highlights", []),
            "suggested_tags": summary.get("suggested_tags", []),
        }
    else:
        result["ai_summary"] = summary

    # Phase 1: Auto-track detail page view
    await track_bookmark_access(bookmark_id, "detail", current_user)

    return result


@router.get("/bookmarks/{bookmark_id}/related")
async def get_related_bookmarks(
    bookmark_id: str,
    limit: int = 5,
    current_user: dict = Depends(get_current_user),
):
    """
    Get semantically related bookmarks using embedding similarity
    Part of Semantic Knowledge Graph feature (Phase 1)
    """
    db = get_database()
    # Get the source bookmark with its embedding
    source_bookmark = await db.bookmarks.find_one(
        {"id": bookmark_id, "user_id": current_user["id"]},
        {"_id": 0, "embedding": 1, "title": 1},
    )

    if not source_bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    if not source_bookmark.get("embedding"):
        # No embedding available yet - return empty result
        return {
            "related": [],
            "message": "Semantic analysis not yet available for this bookmark",
        }

    source_embedding = source_bookmark["embedding"]

    # Get all user's bookmarks that have embeddings (excluding the source bookmark)
    all_bookmarks = await db.bookmarks.find(
        {
            "user_id": current_user["id"],
            "id": {"$ne": bookmark_id},
            "embedding": {"$exists": True, "$ne": None},
        },
        {
            "_id": 0,
            "id": 1,
            "title": 1,
            "description": 1,
            "url": 1,
            "favicon": 1,
            "domain": 1,
            "thumbnail": 1,
            "created_at": 1,
            "embedding": 1,
            "entities": 1,
            "concepts": 1,
        },
    ).to_list(None)

    if not all_bookmarks:
        return {
            "related": [],
            "message": "No other bookmarks with semantic data available",
        }

    # Calculate similarity using dot product (vectors are L2-normalized)
    import numpy as np

    def dot_product_similarity(vec1, vec2):
        """Dot product of L2-normalized vectors equals cosine similarity."""
        return float(np.dot(vec1, vec2))

    # Calculate similarity scores and filter by threshold
    similarities = []
    for bookmark in all_bookmarks:
        if bookmark.get("embedding"):
            similarity = dot_product_similarity(source_embedding, bookmark["embedding"])
            # Only include results above minimum threshold
            if similarity >= MIN_SEMANTIC_SCORE:
                bookmark.pop("embedding", None)
                bookmark["similarity_score"] = similarity
                similarities.append(bookmark)

    # Sort by similarity score and take top N
    similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
    top_related = similarities[:limit]

    return {"related": top_related}


@router.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    result = await db.bookmarks.delete_one({"id": bookmark_id, "user_id": current_user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.ai_summaries.delete_one({"bookmark_id": bookmark_id})
    await db.collections.update_many({"user_id": current_user["id"]}, {"$pull": {"bookmark_ids": bookmark_id}})

    return {"message": "Bookmark deleted"}


@router.post("/bookmarks/bulk-delete")
@limiter.limit("10/minute")  # IP-based rate limiting
@limiter.limit("50/hour", key_func=get_user_identifier)  # User-based rate limiting
async def bulk_delete_bookmarks(
    request: Request,
    bookmark_ids: list[str],
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    result = await db.bookmarks.delete_many({"id": {"$in": bookmark_ids}, "user_id": current_user["id"]})
    await db.ai_summaries.delete_many({"bookmark_id": {"$in": bookmark_ids}})
    await db.collections.update_many(
        {"user_id": current_user["id"]},
        {"$pull": {"bookmark_ids": {"$in": bookmark_ids}}},
    )
    return {
        "message": f"Deleted {result.deleted_count} bookmarks",
        "count": result.deleted_count,
    }


@router.patch("/bookmarks/{bookmark_id}/read-status")
async def update_read_status(
    bookmark_id: str,
    read_status: bool,
    version: int | None = None,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    query = {"id": bookmark_id, "user_id": current_user["id"]}

    # If client sends version, enforce optimistic locking
    if version is not None:
        query["$or"] = [
            {"version": version},
            {"version": {"$exists": False}},  # Backward compat for pre-migration docs
        ]

    result = await db.bookmarks.find_one_and_update(
        query,
        {
            "$set": {
                "read_status": read_status,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            "$inc": {"version": 1},
        },
        return_document=True,
    )

    if result is None:
        # Check if bookmark exists at all
        exists = await db.bookmarks.find_one(
            {"id": bookmark_id, "user_id": current_user["id"]},
            {"_id": 0, "id": 1},
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Bookmark not found")
        raise HTTPException(
            status_code=409,
            detail="Bookmark was modified by another request. Please refresh and retry.",
        )
    return {"message": "Read status updated", "version": result.get("version", 1)}


@router.post("/bookmarks/bulk-mark-read")
@limiter.limit("10/minute")  # IP-based rate limiting
@limiter.limit("50/hour", key_func=get_user_identifier)  # User-based rate limiting
async def bulk_mark_read(
    request: Request,
    bookmark_ids: list[str],
    read_status: bool,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    result = await db.bookmarks.update_many(
        {"id": {"$in": bookmark_ids}, "user_id": current_user["id"]},
        {
            "$set": {
                "read_status": read_status,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            "$inc": {"version": 1},
        },
    )
    return {
        "message": f"Updated {result.modified_count} bookmarks",
        "count": result.modified_count,
    }


# Phase 1: Access Tracking & Aging Endpoints


@router.post("/bookmarks/{bookmark_id}/accessed")
async def track_bookmark_access(
    bookmark_id: str,
    source: str = "detail",  # "detail" or "external"
    current_user: dict = Depends(get_current_user),
):
    """
    Track when a bookmark is meaningfully accessed.
    Called when user views detail page or opens external URL.
    """
    db = get_database()
    # Validate ownership
    bookmark = await db.bookmarks.find_one({"id": bookmark_id, "user_id": current_user["id"]})
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    now = datetime.now(UTC).isoformat()

    # Atomic update with tracking
    await db.bookmarks.update_one(
        {"id": bookmark_id},
        {
            "$set": {"last_accessed": now},
            "$inc": {"view_count": 1, "version": 1},
            "$push": {
                "access_history": {
                    "$each": [{"timestamp": now, "source": source}],
                    "$slice": -20,  # Keep only last 20
                }
            },
        },
    )

    return {"status": "tracked", "timestamp": now}


@router.post("/bookmarks/merge")
async def merge_bookmarks(bookmark_ids: list[str], current_user: dict = Depends(get_current_user)):
    db = get_database()
    if len(bookmark_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 bookmarks to merge")

    bookmarks = await db.bookmarks.find(
        {"id": {"$in": bookmark_ids}, "user_id": current_user["id"]}, {"_id": 0}
    ).to_list(100)
    if len(bookmarks) < 2:
        raise HTTPException(status_code=404, detail="Bookmarks not found")

    keep_bookmark = bookmarks[0]
    delete_ids = [b["id"] for b in bookmarks[1:]]

    await db.bookmarks.delete_many({"id": {"$in": delete_ids}})
    await db.ai_summaries.delete_many({"bookmark_id": {"$in": delete_ids}})

    return {"message": "Bookmarks merged", "kept_bookmark": keep_bookmark}
