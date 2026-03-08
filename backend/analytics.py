"""
Learning Analytics Module
Provides reading statistics, topic analysis, and behavioral insights.

Part of Personal Learning Analytics & Insight Engine (Roadmap Item 12)
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from collections import Counter, defaultdict
import logging

logger = logging.getLogger(__name__)


async def calculate_reading_stats(user_id: str, days: int, db) -> Dict:
    """
    Calculate reading statistics for a user over a time period.
    
    Args:
        user_id: User ID to analyze
        days: Number of days to look back
        db: Database instance
    
    Returns:
        Dict with reading statistics
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff_date.isoformat()
    
    # Get all bookmarks for the user
    bookmarks = await db.bookmarks.find(
        {"user_id": user_id},
        {
            "_id": 0,
            "id": 1,
            "created_at": 1,
            "last_accessed": 1,
            "view_count": 1,
            "reading_time": 1,
            "read_status": 1,
            "access_history": 1
        }
    ).to_list(None)
    
    # Initialize stats
    stats = {
        "period_days": days,
        "total_bookmarks": len(bookmarks),
        "bookmarks_saved_in_period": 0,
        "bookmarks_read_in_period": 0,
        "total_reading_time_minutes": 0,
        "completion_rate": 0.0,
        "avg_reading_time_per_article": 0,
        "unread_count": 0,
        "most_viewed_count": 0
    }
    
    bookmarks_saved_in_period = 0
    bookmarks_saved_and_read_in_period = 0  # Only count bookmarks that were BOTH saved AND read in period
    bookmarks_accessed_in_period = 0  # Any bookmark accessed in period (for reading time)
    total_reading_time = 0
    unread_count = 0
    max_views = 0
    
    for bookmark in bookmarks:
        created_at = bookmark.get("created_at", "")
        last_accessed = bookmark.get("last_accessed")
        view_count = bookmark.get("view_count", 0) or 0
        reading_time = bookmark.get("reading_time", 0) or 0
        read_status = bookmark.get("read_status", False)
        
        saved_in_period = created_at and created_at >= cutoff_str
        accessed_in_period = last_accessed and last_accessed >= cutoff_str
        
        # Count bookmarks saved in period
        if saved_in_period:
            bookmarks_saved_in_period += 1
            
            # Only count as "completed" if this bookmark was ALSO read (saved AND accessed in period)
            if accessed_in_period:
                bookmarks_saved_and_read_in_period += 1
        
        # Count bookmarks read/accessed in period (for reading time calculation)
        if accessed_in_period:
            bookmarks_accessed_in_period += 1
            if reading_time:
                total_reading_time += reading_time
        
        # Count unread (never marked as read)
        if not read_status:
            unread_count += 1
        
        # Track max views
        if view_count > max_views:
            max_views = view_count
    
    stats["bookmarks_saved_in_period"] = bookmarks_saved_in_period
    stats["bookmarks_read_in_period"] = bookmarks_accessed_in_period  # Total accessed for display
    stats["total_reading_time_minutes"] = total_reading_time
    stats["unread_count"] = unread_count
    stats["most_viewed_count"] = max_views
    
    # Calculate completion rate (bookmarks saved in period that were subsequently read)
    # This ensures completion rate can never exceed 100%
    if bookmarks_saved_in_period > 0:
        rate = (bookmarks_saved_and_read_in_period / bookmarks_saved_in_period) * 100
        stats["completion_rate"] = min(round(rate, 1), 100.0)  # Cap at 100%
    
    # Average reading time per article
    if bookmarks_accessed_in_period > 0:
        stats["avg_reading_time_per_article"] = round(
            total_reading_time / bookmarks_accessed_in_period, 1
        )
    
    return stats


async def get_topic_breakdown(user_id: str, days: int, db) -> List[Dict]:
    """
    Get topic breakdown based on AI-suggested tags.
    
    Args:
        user_id: User ID to analyze
        days: Number of days to look back
        db: Database instance
    
    Returns:
        List of topic dicts with count and reading time
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff_date.isoformat()
    
    # Get bookmarks accessed in period
    bookmarks = await db.bookmarks.find(
        {
            "user_id": user_id,
            "$or": [
                {"last_accessed": {"$gte": cutoff_str}},
                {"created_at": {"$gte": cutoff_str}}
            ]
        },
        {"_id": 0, "id": 1, "reading_time": 1}
    ).to_list(None)
    
    if not bookmarks:
        return []
    
    bookmark_ids = [b["id"] for b in bookmarks]
    reading_times = {b["id"]: b.get("reading_time", 0) or 0 for b in bookmarks}
    
    # Get AI summaries with tags
    summaries = await db.ai_summaries.find(
        {"bookmark_id": {"$in": bookmark_ids}},
        {"_id": 0, "bookmark_id": 1, "suggested_tags": 1}
    ).to_list(None)
    
    # Aggregate by topic
    topic_stats = defaultdict(lambda: {"count": 0, "reading_time": 0})
    
    for summary in summaries:
        tags = summary.get("suggested_tags", [])
        bookmark_id = summary.get("bookmark_id")
        rt = reading_times.get(bookmark_id, 0)
        
        for tag in tags[:5]:  # Limit to first 5 tags per bookmark
            topic_stats[tag]["count"] += 1
            topic_stats[tag]["reading_time"] += rt
    
    # Convert to sorted list
    topics = [
        {
            "topic": topic,
            "count": stats["count"],
            "reading_time_minutes": stats["reading_time"]
        }
        for topic, stats in topic_stats.items()
    ]
    
    # Sort by count descending
    topics.sort(key=lambda x: x["count"], reverse=True)
    
    return topics[:15]  # Return top 15 topics


async def get_reading_patterns(user_id: str, days: int, db) -> Dict:
    """
    Analyze reading patterns by time of day and day of week.
    
    Args:
        user_id: User ID to analyze
        days: Number of days to look back
        db: Database instance
    
    Returns:
        Dict with pattern data for heatmap visualization
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff_date.isoformat()
    
    # Get bookmarks with access history
    bookmarks = await db.bookmarks.find(
        {"user_id": user_id},
        {"_id": 0, "access_history": 1, "last_accessed": 1}
    ).to_list(None)
    
    # Initialize counters
    hour_counts = Counter()  # 0-23
    day_counts = Counter()   # 0-6 (Monday-Sunday)
    hour_day_matrix = defaultdict(Counter)  # hour -> day -> count
    
    for bookmark in bookmarks:
        access_history = bookmark.get("access_history", [])
        
        for access in access_history:
            timestamp = access.get("timestamp")
            if not timestamp:
                continue
            
            # Parse timestamp
            if isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    continue
            else:
                dt = timestamp
            
            # Only count accesses in the period
            if dt < cutoff_date:
                continue
            
            hour = dt.hour
            day = dt.weekday()  # 0=Monday, 6=Sunday
            
            hour_counts[hour] += 1
            day_counts[day] += 1
            hour_day_matrix[hour][day] += 1
        
        # Also count last_accessed if no history
        if not access_history:
            last_accessed = bookmark.get("last_accessed")
            if last_accessed and last_accessed >= cutoff_str:
                try:
                    dt = datetime.fromisoformat(last_accessed.replace('Z', '+00:00'))
                    hour_counts[dt.hour] += 1
                    day_counts[dt.weekday()] += 1
                    hour_day_matrix[dt.hour][dt.weekday()] += 1
                except (ValueError, TypeError):
                    pass
    
    # Find peak hour
    peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 0
    peak_hour_count = hour_counts.get(peak_hour, 0)
    
    # Calculate weekday vs weekend
    weekday_total = sum(day_counts[d] for d in range(5))
    weekend_total = sum(day_counts[d] for d in range(5, 7))
    total_accesses = weekday_total + weekend_total
    
    weekday_percent = round(weekday_total / total_accesses * 100, 1) if total_accesses > 0 else 0
    
    # Build heatmap data (hour x day matrix)
    heatmap_data = []
    for hour in range(24):
        for day in range(7):
            count = hour_day_matrix[hour][day]
            heatmap_data.append({
                "hour": hour,
                "day": day,
                "count": count
            })
    
    # Day labels
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    return {
        "peak_hour": peak_hour,
        "peak_hour_label": f"{peak_hour:02d}:00",
        "peak_hour_count": peak_hour_count,
        "weekday_percent": weekday_percent,
        "weekend_percent": round(100 - weekday_percent, 1),
        "total_sessions": total_accesses,
        "by_hour": dict(hour_counts),
        "by_day": {day_labels[d]: c for d, c in day_counts.items()},
        "heatmap": heatmap_data
    }


async def get_learning_insights(user_id: str, db) -> List[Dict]:
    """
    Generate behavioral insights based on reading patterns.
    
    Args:
        user_id: User ID to analyze
        db: Database instance
    
    Returns:
        List of insight dicts with 'type', 'message', 'severity'
    """
    insights = []
    
    # Get 30-day stats
    stats = await calculate_reading_stats(user_id, 30, db)
    
    # Insight 1: Low completion rate
    if stats["completion_rate"] < 40 and stats["bookmarks_saved_in_period"] >= 5:
        insights.append({
            "type": "completion",
            "message": f"You save more than you read: only {stats['completion_rate']}% of bookmarks get read. Consider being more selective.",
            "severity": "warning"
        })
    elif stats["completion_rate"] >= 70:
        insights.append({
            "type": "completion",
            "message": f"Great reading habit! You read {stats['completion_rate']}% of what you save.",
            "severity": "success"
        })
    
    # Insight 2: High unread count
    if stats["unread_count"] > 50:
        insights.append({
            "type": "backlog",
            "message": f"You have {stats['unread_count']} unread bookmarks. Consider reviewing your backlog.",
            "severity": "warning"
        })
    
    # Insight 3: Reading time analysis
    if stats["total_reading_time_minutes"] >= 600:  # 10+ hours
        hours = stats["total_reading_time_minutes"] / 60
        insights.append({
            "type": "reading_time",
            "message": f"Impressive! You've spent {hours:.1f} hours reading this month.",
            "severity": "success"
        })
    elif stats["total_reading_time_minutes"] < 60 and stats["bookmarks_saved_in_period"] >= 10:
        insights.append({
            "type": "reading_time",
            "message": "You save bookmarks but spend little time reading. Try scheduling reading time.",
            "severity": "info"
        })
    
    # Insight 4: Get patterns for time-based insights
    patterns = await get_reading_patterns(user_id, 30, db)
    if patterns["total_sessions"] >= 10:
        peak_label = patterns["peak_hour_label"]
        insights.append({
            "type": "peak_time",
            "message": f"Your peak reading time is around {peak_label}. Schedule deep reading then.",
            "severity": "info"
        })
    
    return insights
