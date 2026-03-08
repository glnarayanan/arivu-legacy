"""
Tests for analytics router endpoints.

Covers: reading-stats, topics, patterns, insights, and summary.
Business logic is mocked since it's tested separately in analytics.py.
"""

import pytest
from unittest.mock import AsyncMock, patch


MOCK_STATS = {
    "period_days": 30,
    "total_bookmarks": 42,
    "bookmarks_saved_in_period": 10,
    "bookmarks_read_in_period": 7,
    "total_reading_time_minutes": 120,
    "completion_rate": 70.0,
    "avg_reading_time_per_article": 17.1,
    "unread_count": 5,
    "most_viewed_count": 8,
}

MOCK_TOPICS = [
    {"topic": "python", "count": 5, "reading_time_minutes": 30},
    {"topic": "fastapi", "count": 3, "reading_time_minutes": 20},
]

MOCK_PATTERNS = {
    "peak_hour": 14,
    "peak_hour_label": "14:00",
    "peak_hour_count": 12,
    "weekday_percent": 80.0,
    "weekend_percent": 20.0,
    "total_sessions": 50,
    "by_hour": {14: 12, 15: 8},
    "by_day": {"Mon": 10, "Tue": 8},
    "heatmap": [],
}

MOCK_INSIGHTS = [
    {"type": "completion", "message": "Great reading habit!", "severity": "success"},
]


@pytest.mark.anyio
@patch(
    "app.routers.analytics.calculate_reading_stats",
    new_callable=AsyncMock,
    return_value=MOCK_STATS,
)
async def test_reading_stats(mock_calc, client):
    """GET /api/analytics/reading-stats returns reading statistics."""
    response = await client.get("/api/analytics/reading-stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_bookmarks"] == 42
    assert data["period_days"] == 30
    mock_calc.assert_called_once_with("test-user-id", 30, mock_calc.call_args[0][2])


@pytest.mark.anyio
@patch(
    "app.routers.analytics.calculate_reading_stats",
    new_callable=AsyncMock,
    return_value=MOCK_STATS,
)
async def test_reading_stats_custom_days(mock_calc, client):
    """GET /api/analytics/reading-stats?days=7 passes custom days parameter."""
    response = await client.get("/api/analytics/reading-stats?days=7")
    assert response.status_code == 200
    mock_calc.assert_called_once()
    assert mock_calc.call_args[0][1] == 7


@pytest.mark.anyio
@patch(
    "app.routers.analytics.get_topic_breakdown",
    new_callable=AsyncMock,
    return_value=MOCK_TOPICS,
)
async def test_topics(mock_topics, client):
    """GET /api/analytics/topics returns topic breakdown wrapped in 'topics' key."""
    response = await client.get("/api/analytics/topics")
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert len(data["topics"]) == 2
    assert data["topics"][0]["topic"] == "python"


@pytest.mark.anyio
@patch(
    "app.routers.analytics.get_reading_patterns",
    new_callable=AsyncMock,
    return_value=MOCK_PATTERNS,
)
async def test_patterns(mock_patterns, client):
    """GET /api/analytics/patterns returns reading patterns."""
    response = await client.get("/api/analytics/patterns")
    assert response.status_code == 200
    data = response.json()
    assert data["peak_hour"] == 14
    assert data["total_sessions"] == 50


@pytest.mark.anyio
@patch(
    "app.routers.analytics.get_learning_insights",
    new_callable=AsyncMock,
    return_value=MOCK_INSIGHTS,
)
async def test_insights(mock_insights, client):
    """GET /api/analytics/insights returns behavioral insights wrapped in 'insights' key."""
    response = await client.get("/api/analytics/insights")
    assert response.status_code == 200
    data = response.json()
    assert "insights" in data
    assert len(data["insights"]) == 1
    assert data["insights"][0]["type"] == "completion"


@pytest.mark.anyio
@patch(
    "app.routers.analytics.get_learning_insights",
    new_callable=AsyncMock,
    return_value=MOCK_INSIGHTS,
)
@patch(
    "app.routers.analytics.get_reading_patterns",
    new_callable=AsyncMock,
    return_value=MOCK_PATTERNS,
)
@patch(
    "app.routers.analytics.get_topic_breakdown",
    new_callable=AsyncMock,
    return_value=MOCK_TOPICS,
)
@patch(
    "app.routers.analytics.calculate_reading_stats",
    new_callable=AsyncMock,
    return_value=MOCK_STATS,
)
async def test_summary(mock_stats, mock_topics, mock_patterns, mock_insights, client):
    """GET /api/analytics/summary returns combined stats, topics, patterns, insights."""
    response = await client.get("/api/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "stats" in data
    assert "topics" in data
    assert "patterns" in data
    assert "insights" in data
    assert data["stats"]["total_bookmarks"] == 42
    assert len(data["topics"]) == 2
