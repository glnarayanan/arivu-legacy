# Learning Analytics

**Status:** ✅ Implemented (Roadmap Item 12)
**Implemented:** January 2026
**Frontend:** `/analytics`
**API:** `/api/analytics/*`

---

## Overview

The Learning Analytics module provides comprehensive insights into your reading habits, content consumption patterns, and knowledge acquisition. It uses AI-powered analysis to help you understand how you learn, what topics interest you, and how to optimize your reading workflow.

---

## Key Features

### 1. **Reading Statistics**
Track your bookmark activity and reading progress:
- Total bookmarks saved
- Read vs. unread ratio
- Reading completion rate
- Average reading time per bookmark
- Daily/weekly/monthly activity trends

### 2. **Topic Analysis**
Understand your content interests:
- Topic distribution across bookmarks
- Trending topics over time
- Topic diversity score
- Emerging interests detection

### 3. **Pattern Detection**
Discover your reading habits:
- Most active days and times
- Reading streaks
- Bookmark saving patterns
- Content type preferences (articles, videos, papers, etc.)

### 4. **AI-Generated Insights**
Gemini-powered recommendations:
- Personalized reading suggestions
- Habit improvement tips
- Content gap identification
- Learning path recommendations

### 5. **Comprehensive Summary**
Unified analytics dashboard combining:
- All statistics in one view
- Visual charts and graphs
- Exportable reports
- Historical comparisons

---

## How It Works

### Backend Processing

1. **Data Collection**
   - Every bookmark interaction is logged (save, read, access)
   - Timestamps, tags, and reading times tracked
   - Content metadata extracted and analyzed

2. **Aggregation**
   - Daily batch processing of analytics data
   - Real-time updates for recent activity
   - MongoDB aggregation pipelines for efficiency

3. **AI Analysis**
   - Gemini 2.5 Flash analyzes patterns
   - Generates personalized insights
   - Identifies learning trends
   - Suggests improvements

### Frontend Visualization

The `/analytics` page displays:
- Interactive charts (reading stats over time)
- Topic distribution pie/bar charts
- Heatmap of reading patterns
- AI insights cards
- Exportable summary reports

---

## API Endpoints

### GET /api/analytics/reading-stats
Get comprehensive reading statistics.

**Response:**
```json
{
  "total_bookmarks": 156,
  "bookmarks_read": 89,
  "bookmarks_unread": 67,
  "reading_percentage": 57.1,
  "total_reading_time_minutes": 2340,
  "average_reading_time_minutes": 15,
  "bookmarks_this_week": 12,
  "bookmarks_this_month": 45,
  "bookmarks_by_day": {
    "Monday": 25,
    "Tuesday": 18,
    "Wednesday": 22,
    "Thursday": 20,
    "Friday": 15,
    "Saturday": 30,
    "Sunday": 26
  },
  "bookmarks_by_month": [
    {"month": "2025-12", "count": 45},
    {"month": "2026-01", "count": 12}
  ]
}
```

---

### GET /api/analytics/topics
Get topic distribution and trends.

**Response:**
```json
{
  "topics": [
    {
      "topic": "Artificial Intelligence",
      "count": 45,
      "percentage": 28.8,
      "trend": "increasing",
      "recent_bookmarks": 12
    },
    {
      "topic": "Web Development",
      "count": 32,
      "percentage": 20.5,
      "trend": "stable",
      "recent_bookmarks": 5
    },
    {
      "topic": "Design",
      "count": 25,
      "percentage": 16.0,
      "trend": "decreasing",
      "recent_bookmarks": 2
    }
  ],
  "total_topics": 15,
  "diversity_score": 0.75,
  "emerging_topics": ["Machine Learning", "AI Ethics"]
}
```

---

### GET /api/analytics/patterns
Get reading pattern analysis.

**Response:**
```json
{
  "most_active_day": "Saturday",
  "most_active_hour": 14,
  "average_bookmarks_per_day": 2.3,
  "reading_streak_days": 7,
  "longest_streak_days": 21,
  "preferred_content_types": [
    {"type": "article", "count": 89},
    {"type": "blog_post", "count": 45},
    {"type": "research_paper", "count": 12}
  ],
  "reading_velocity": "moderate",
  "consistency_score": 0.82
}
```

---

### GET /api/analytics/insights
Get AI-generated insights about reading habits.

**Response:**
```json
{
  "insights": [
    "You've been reading 40% more about AI topics this month compared to last month",
    "Your reading consistency has improved by 20% - great job maintaining your streak!",
    "You tend to save bookmarks on weekends but read them on weekdays",
    "Consider revisiting your 67 unread bookmarks from the past 2 months"
  ],
  "recommendations": [
    "Check out the Knowledge Graph to discover connections between your AI and Design bookmarks",
    "Try the Resurfacing feature to review important content from 2 weeks ago",
    "Your reading velocity suggests you might enjoy longer-form content"
  ],
  "achievements": [
    "7-day reading streak 🔥",
    "100+ bookmarks saved 🎉",
    "50% read completion rate ⭐"
  ],
  "generated_at": "2026-01-12T10:00:00Z"
}
```

---

### GET /api/analytics/summary
Get comprehensive analytics summary (combines all above).

**Response:**
```json
{
  "stats": { /* reading-stats data */ },
  "topics": { /* topics data */ },
  "patterns": { /* patterns data */ },
  "insights": { /* insights data */ },
  "summary_generated_at": "2026-01-12T10:00:00Z"
}
```

---

## Use Cases

### 1. **Self-Awareness**
"I didn't realize I've been saving so many AI bookmarks lately - the topic analysis showed me a clear trend."

### 2. **Habit Building**
"The reading streak tracker motivates me to read at least one bookmark per day."

### 3. **Content Curation**
"Analytics showed I have 50+ unread design bookmarks - time to create a collection and tackle them."

### 4. **Learning Optimization**
"I discovered I read best on Tuesday mornings at 10 AM - I'll schedule important reads for then."

### 5. **Progress Tracking**
"My reading completion rate went from 30% to 57% in 3 months - visible progress!"

---

## Configuration

### Analytics Data Retention
```python
# Keep detailed logs for 90 days
ANALYTICS_LOG_RETENTION_DAYS = 90

# Keep aggregated stats forever
ANALYTICS_AGGREGATED_RETENTION = None
```

### AI Insights Generation
```python
# Regenerate insights daily
INSIGHTS_GENERATION_INTERVAL = "daily"

# Minimum bookmarks for insights
MIN_BOOKMARKS_FOR_INSIGHTS = 10
```

### Caching
```python
# Cache analytics for 1 hour
ANALYTICS_CACHE_TTL = 3600

# Invalidate cache on bookmark changes
INVALIDATE_ON_BOOKMARK_CHANGE = True
```

---

## Performance

### Database Indexes
- `user_id` + `created_at` - Fast time-based queries
- `user_id` + `tags` - Topic analysis
- `user_id` + `read_status` - Reading stats

### Aggregation Pipelines
Uses MongoDB aggregation for efficiency:
```python
# Example: Topic distribution
pipeline = [
    {"$match": {"user_id": user_id}},
    {"$unwind": "$tags"},
    {"$group": {
        "_id": "$tags",
        "count": {"$sum": 1}
    }},
    {"$sort": {"count": -1}},
    {"$limit": 20}
]
```

### Background Jobs
- Daily: Regenerate insights for all users
- Weekly: Trend analysis and pattern detection
- Monthly: Historical comparison reports

---

## Frontend Implementation

### Analytics Page Components

**Main Components:**
1. **StatCards** - Key metrics display
2. **ReadingChart** - Line chart of reading over time
3. **TopicPieChart** - Topic distribution
4. **PatternHeatmap** - Reading activity heatmap
5. **InsightsPanel** - AI-generated insights cards
6. **ExportButton** - Export analytics report

**State Management:**
```javascript
const [stats, setStats] = useState(null)
const [topics, setTopics] = useState(null)
const [patterns, setPatterns] = useState(null)
const [insights, setInsights] = useState(null)
const [loading, setLoading] = useState(true)
```

**Data Fetching:**
```javascript
useEffect(() => {
  Promise.all([
    fetch('/api/analytics/reading-stats'),
    fetch('/api/analytics/topics'),
    fetch('/api/analytics/patterns'),
    fetch('/api/analytics/insights')
  ]).then(/* update state */)
}, [])
```

---

## Data Privacy

### What's Tracked
- Bookmark metadata (titles, URLs, tags)
- Reading activity (timestamps, duration)
- User behavior patterns (aggregated only)

### What's NOT Tracked
- Personal browsing history outside bookmarks
- IP addresses or location data
- Third-party cookies
- Sensitive bookmark content

### Data Control
- Users can export all analytics data
- Analytics can be disabled in settings (planned)
- Data automatically anonymized after 90 days

---

## Metrics Definitions

### Reading Percentage
```
(bookmarks_read / total_bookmarks) * 100
```

### Reading Velocity
- **Fast:** >10 bookmarks/week
- **Moderate:** 5-10 bookmarks/week
- **Slow:** <5 bookmarks/week

### Consistency Score
```
(days_with_activity / total_days) * streak_factor
Range: 0.0 - 1.0
```

### Diversity Score
```
1 - (dominance_of_top_topic / total_topics)
Range: 0.0 (single topic) to 1.0 (highly diverse)
```

---

## Limitations

Current limitations:
- Analytics require minimum 10 bookmarks
- Insights generated daily (not real-time)
- Limited to past 12 months of data
- English content only for topic analysis

**Planned Improvements (Q2 2026):**
- Real-time analytics updates
- Custom date range selection
- Comparative analytics (vs. other users, anonymized)
- Goal setting and tracking
- Advanced filters and segmentation

---

## Troubleshooting

### No analytics showing
- Check that you have at least 10 bookmarks
- Verify bookmarks have been processed (status: "completed")
- Clear browser cache and reload

### Insights not updating
- Insights regenerate daily at midnight UTC
- Check backend logs for AI processing errors
- Verify Gemini API key is configured

### Incorrect statistics
- Statistics update every hour
- Force refresh: Clear cache and reload page
- Report discrepancies via GitHub issues

---

## Technical Implementation

### Libraries Used
- **Backend:** `pandas` (data analysis), `numpy` (calculations)
- **AI:** `google-generativeai` (Gemini insights)
- **Database:** `pymongo` (aggregation pipelines)
- **Frontend:** `recharts` (data visualization)

### Database Schema

**Analytics Events Collection:**
```json
{
  "user_id": "user_id",
  "event_type": "bookmark_saved|bookmark_read|bookmark_accessed",
  "bookmark_id": "bookmark_id",
  "timestamp": "2026-01-12T10:00:00Z",
  "metadata": {
    "reading_time_seconds": 450,
    "source": "dashboard|extension|import"
  }
}
```

**Aggregated Stats Collection:**
```json
{
  "user_id": "user_id",
  "date": "2026-01-12",
  "stats": {
    "bookmarks_saved": 3,
    "bookmarks_read": 2,
    "total_reading_time_minutes": 45
  },
  "topics": {"AI": 2, "Design": 1},
  "generated_at": "2026-01-12T23:59:59Z"
}
```

---

## Export Formats

### JSON Export
```json
{
  "user_id": "user_id",
  "export_date": "2026-01-12T10:00:00Z",
  "analytics": {
    "stats": { /* ... */ },
    "topics": { /* ... */ },
    "patterns": { /* ... */ },
    "insights": { /* ... */ }
  }
}
```

### CSV Export
```csv
Metric,Value
Total Bookmarks,156
Bookmarks Read,89
Reading Percentage,57.1%
Top Topic,Artificial Intelligence (45)
Most Active Day,Saturday
Reading Streak,7 days
```

---

## Related Features

- **[Knowledge Graph](knowledge-graph.md)** - Topic analysis uses knowledge graph entities
- **[Resurfacing](resurfacing-engine.md)** - Patterns inform resurfacing suggestions
- **Dashboard** - Summary stats shown on main dashboard

---

## References

- **Roadmap:** [documentation/roadmap/2026-roadmap/12-personal-learning-analytics-insight-engine.md](../roadmap/2026-roadmap/12-personal-learning-analytics-insight-engine.md)
- **API Docs:** [documentation/api/README.md](../api/README.md#analytics-endpoints)

---

**Last Updated:** January 12, 2026
**Status:** Fully Implemented
**Next Enhancements:** Q2 2026 (Real-time updates, Goal tracking, Custom date ranges)
