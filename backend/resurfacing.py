"""
Intelligent Resurfacing Engine
Proactively surfaces forgotten bookmarks at optimal times.

This module implements the resurfacing score algorithm based on:
- Age factor (days since last access)
- Engagement history (view count)
- Content quality (AI summary presence)
- Reading time (shorter = easier commitment)
- Spaced repetition intervals (1, 3, 7, 14, 30 days)
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Spaced repetition intervals (Leitner-inspired)
SPACED_INTERVALS = [1, 3, 7, 14, 30]


def calculate_resurfacing_score(
    bookmark: dict, ai_summary: dict | None = None, current_time: datetime | None = None
) -> tuple[float, dict[str, float]]:
    """
    Calculate resurfacing priority score for a bookmark.

    Args:
        bookmark: Bookmark document with last_accessed, view_count, reading_time
        ai_summary: Optional AI summary document for the bookmark
        current_time: Optional current time (for testing), defaults to now

    Returns:
        Tuple of (total_score, breakdown_dict) where breakdown shows each factor's contribution
    """
    if current_time is None:
        current_time = datetime.now(UTC)

    breakdown = {}

    # Parse last_accessed
    last_accessed = bookmark.get("last_accessed")
    if isinstance(last_accessed, str):
        try:
            last_accessed = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            last_accessed = None

    if last_accessed is None:
        # Fallback to created_at
        created_at = bookmark.get("created_at")
        if isinstance(created_at, str):
            try:
                last_accessed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                last_accessed = current_time - timedelta(days=30)  # Default to 30 days old
        else:
            last_accessed = current_time - timedelta(days=30)

    # Ensure timezone awareness
    if last_accessed.tzinfo is None:
        last_accessed = last_accessed.replace(tzinfo=UTC)

    days_since_access = (current_time - last_accessed).days

    # --- Scoring Factors ---

    # 1. Age factor (7-90 days = higher priority)
    # Too recent (< 7 days) = don't resurface yet
    # Too old (> 90 days) = cap the boost
    age_score = 0.0
    if 7 <= days_since_access <= 90:
        age_score = min(days_since_access / 10, 10.0)
    elif days_since_access > 90:
        age_score = 10.0  # Cap at max
    breakdown["age"] = age_score

    # 2. Engagement history (previously viewed = valuable)
    view_count = bookmark.get("view_count", 0) or 0
    engagement_score = min(view_count * 2, 10.0)
    breakdown["engagement"] = engagement_score

    # 3. Content quality (has AI summary = easier to resurface)
    quality_score = 0.0
    if ai_summary:
        if ai_summary.get("one_sentence"):
            quality_score += 3.0
        if ai_summary.get("suggested_tags"):
            quality_score += 2.0
    breakdown["quality"] = quality_score

    # 4. Reading time (shorter articles = easier commitment)
    reading_time = bookmark.get("reading_time") or 0
    time_score = 0.0
    if reading_time and reading_time <= 10:
        time_score = 10.0 - reading_time
    breakdown["reading_time"] = time_score

    # 5. Spaced repetition boost (optimal review intervals)
    spaced_score = 0.0
    if days_since_access in SPACED_INTERVALS:
        spaced_score = 15.0
    # Also boost if close to an interval (within 1 day)
    elif any(abs(days_since_access - interval) <= 1 for interval in SPACED_INTERVALS):
        spaced_score = 10.0
    breakdown["spaced_repetition"] = spaced_score

    # Calculate total
    total_score = sum(breakdown.values())
    breakdown["total"] = total_score

    return total_score, breakdown


def get_resurfacing_reason(bookmark: dict, breakdown: dict[str, float], days_since_access: int) -> str:
    """
    Generate a human-readable reason for why this bookmark is being resurfaced.

    Args:
        bookmark: Bookmark document
        breakdown: Score breakdown from calculate_resurfacing_score
        days_since_access: Days since bookmark was last accessed

    Returns:
        Human-readable reason string
    """
    reasons = []

    # Primary reason based on highest scoring factor
    if breakdown.get("spaced_repetition", 0) >= 10:
        if days_since_access == 1:
            reasons.append("Review from yesterday")
        elif days_since_access == 7:
            reasons.append("Weekly review")
        elif days_since_access == 30:
            reasons.append("Monthly review")
        else:
            reasons.append(f"Optimal review timing ({days_since_access} days)")
    elif breakdown.get("age", 0) >= 5:
        if days_since_access >= 30:
            reasons.append(f"Not opened in {days_since_access} days")
        else:
            reasons.append("Time to revisit")

    # Secondary context
    view_count = bookmark.get("view_count", 0) or 0
    if view_count >= 3:
        reasons.append(f"You've found this valuable ({view_count} views)")

    reading_time = bookmark.get("reading_time")
    if reading_time and reading_time <= 5:
        reasons.append(f"Quick {reading_time} min read")

    if not reasons:
        reasons.append("Worth another look")

    return " • ".join(reasons[:2])  # Max 2 reason parts


def should_resurface(bookmark: dict) -> bool:
    """
    Check if a bookmark should be included in resurfacing candidates.

    Args:
        bookmark: Bookmark document

    Returns:
        True if bookmark can be resurfaced
    """
    # Skip if archived from resurfacing
    if bookmark.get("resurfacing_archived"):
        return False

    # Skip if snoozed
    snoozed_until = bookmark.get("resurfacing_snoozed_until")
    if snoozed_until:
        if isinstance(snoozed_until, str):
            try:
                snoozed_until = datetime.fromisoformat(snoozed_until.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                snoozed_until = None

        if snoozed_until and snoozed_until > datetime.now(UTC):
            return False

    # Skip if accessed too recently (< 1 day)
    last_accessed = bookmark.get("last_accessed")
    if last_accessed:
        if isinstance(last_accessed, str):
            try:
                last_accessed = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                last_accessed = None

        if last_accessed:
            if last_accessed.tzinfo is None:
                last_accessed = last_accessed.replace(tzinfo=UTC)
            days_since = (datetime.now(UTC) - last_accessed).days
            if days_since < 1:
                return False

    # Must have some content
    if not bookmark.get("title"):
        return False

    return True
UTC = timezone.utc
