# Intelligent Resurfacing Engine

**Status:** ✅ Fully Implemented (Roadmap Item 2)
**Implemented:** January 2026
**Frontend:** Integrated in Dashboard
**API:** `/api/resurfacing/*`, `/api/bookmarks/aged`

---

## Overview

The Intelligent Resurfacing Engine uses spaced repetition algorithms to help you rediscover valuable content at optimal intervals. Based on memory science and reading patterns, it suggests bookmarks you should revisit to maximize retention and insight.

---

## Key Features

### 1. **Spaced Repetition Algorithm**
- Calculates optimal review intervals based on previous access
- Adapts to your reading patterns
- Increases intervals with each successful review
- Prioritizes high-value content

### 2. **Context-Aware Suggestions**
- Considers current reading patterns
- Surfaces related content when you're exploring a topic
- Factors in bookmark importance (tags, highlights, notes)

### 3. **Smart Snoozing**
- Postpone bookmarks temporarily (1, 3, 7, 14, or 30 days)
- Snoozed items reappear after the specified period
- Track snooze history for pattern analysis

### 4. **Archiving**
- Remove bookmarks from resurfacing rotation
- Still accessible via search and filters
- Can be unarchived anytime

### 5. **Memory Jogger (Daily Rediscovery)**
- Surfaces a single "Forgotten Gem" every day
- Prominent placement on the dashboard
- Contextual reasons for rediscovery (similarity to recent saves, time since saved)
- High-impact micro-intervention for knowledge retention

---

## How It Works

### Resurfacing Score Calculation

The resurfacing score (0-1) is calculated based on:

1. **Time Since Last Access** (40% weight)
   - Optimal interval: 1, 3, 7, 14, 30, 90, 180 days
   - Score increases as actual time approaches optimal interval

2. **Access Frequency** (20% weight)
   - Bookmarks accessed 2-5 times score higher
   - Too many accesses = less need to resurface
   - Never accessed = needs initial review

3. **Content Quality** (20% weight)
   - Presence of highlights (indicates value)
   - Number of tags (indicates categorization)
   - Reading time (longer content scores higher)

4. **Relevance to Current Interests** (20% weight)
   - Similarity to recently accessed bookmarks
   - Overlapping tags with current reading
   - Knowledge graph entity overlap

**Formula:**
```python
resurfacing_score = (
    time_factor * 0.4 +
    frequency_factor * 0.2 +
    quality_factor * 0.2 +
    relevance_factor * 0.2
)
```

---

## API Endpoints

### GET /api/resurfacing
Get bookmarks recommended for resurfacing.

**Query Parameters:**
- `limit` (optional) - Number of suggestions (default: 10, max: 50)

**Response:**
```json
[
  {
    "id": "bookmark_xyz",
    "title": "The Science of Spaced Repetition",
    "url": "https://example.com/article",
    "resurfacing_score": 0.85,
    "resurfacing_reason": "Optimal review interval reached (14 days)",
    "days_since_last_access": 14,
    "previous_access_count": 2,
    "last_accessed_at": "2025-12-29T00:00:00Z"
  }
]
```

### GET /api/bookmarks/aged
Get bookmarks that haven't been accessed recently.

**Query Parameters:**
- `days` (optional) - Minimum days since last access (default: 30)
- `limit` (optional) - Max results (default: 20)

### POST /api/resurfacing/{bookmark_id}/snooze
Snooze a bookmark for a specified period.

**Request Body:**
```json
{
  "days": 7
}
```

**Response:**
```json
{
  "message": "Bookmark snoozed for 7 days",
  "snooze_until": "2026-01-19T00:00:00Z"
}
```

### POST /api/resurfacing/{bookmark_id}/archive
Archive a bookmark (remove from resurfacing).

### POST /api/resurfacing/{bookmark_id}/unarchive
Unarchive a bookmark.

---

## Frontend Integration

### Dashboard View

The dashboard shows resurfacing suggestions in a dedicated section:
- Top 5 bookmarks for immediate review
- "Resurface" button to view all suggestions
- One-click snooze/archive actions

### Notification System

Email or push notifications are not currently implemented. Possible future notification surfaces include:
- Daily digest of resurfacing suggestions
- Weekly summary of unreviewed bookmarks
- Monthly "rediscovery" highlights

---

## Use Cases

### 1. **Learning & Retention**
"I saved an article about React hooks 2 weeks ago. The resurfacing engine reminds me to review it now, reinforcing my understanding."

### 2. **Research Continuity**
"I was researching AI ethics last month but got sidetracked. Resurfacing brings those bookmarks back when I return to the topic."

### 3. **Content Discovery**
"I forgot I saved this amazing talk about design patterns. Resurfacing reminded me at the perfect time."

### 4. **Knowledge Management**
"By reviewing bookmarks at optimal intervals, I retain more information and build deeper connections."

---

## Configuration

### Intervals
Default spaced repetition intervals (in days):
```python
RESURFACING_INTERVALS = [1, 3, 7, 14, 30, 90, 180]
```

### Score Thresholds
Minimum score for resurfacing suggestions:
```python
MIN_RESURFACING_SCORE = 0.6
```

### Maximum Suggestions
Default number of suggestions per request:
```python
DEFAULT_RESURFACING_LIMIT = 10
MAX_RESURFACING_LIMIT = 50
```

---

## Performance

### Database Indexes
- `user_id` + `last_accessed_at` - Fast aging queries
- `user_id` + `archived` - Filter archived bookmarks
- `user_id` + `snoozed_until` - Handle snoozed items

### Caching
- Resurfacing scores cached for 1 hour
- Aged bookmarks cached for 6 hours
- Cache invalidated on bookmark access

### Background Jobs
- Daily recalculation of resurfacing scores
- Weekly cleanup of expired snoozes
- Monthly archival suggestions for never-accessed bookmarks

---

## Algorithm Details

### Spaced Repetition Model

Based on the **SM-2 algorithm** (SuperMemo 2):
1. First review: 1 day after saving
2. Second review: 3 days after first review
3. Subsequent reviews: Multiply interval by factor (1.5-2.5)
4. Maximum interval: 180 days

### Adaptive Intervals

The algorithm adapts based on:
- **Quick re-access** (< 24h) → Interval reduced by 20%
- **Access at optimal time** → Interval increased by 50%
- **Missed optimal window** → Interval reset to previous level

---

## Resurfacing Reasons

The engine provides human-readable reasons:
- "Optimal review interval reached (N days)"
- "You haven't visited this in N days"
- "Related to your recent reading about [topic]"
- "High-value content (has highlights)"
- "Part of your [tag] collection"
- "Connected to N other bookmarks in your graph"

---

## Limitations

Current limitations:
- English content only (NLP-based relevance)
- Maximum 50 suggestions per request
- No cross-device notification delivery
- No manual interval adjustment

---

## Not Currently Implemented

- Email/push notifications based on user preferences
- User-adjustable resurfacing intervals
- Reading goals
- Habit tracking
- Manual priority boosting
- Team resurfacing

---

## Technical Implementation

### Libraries Used
- `datetime` - Date/time calculations
- `numpy` - Score calculations
- `pymongo` - Database queries
- `scikit-learn` - Relevance scoring (cosine similarity)

### Database Schema

**Bookmark Access Log:**
```json
{
  "bookmark_id": "bookmark_xyz",
  "user_id": "user_id",
  "accessed_at": "2026-01-12T10:00:00Z",
  "source": "resurfacing_suggestion"
}
```

**Snooze Data (embedded in bookmark):**
```json
{
  "snoozed": true,
  "snoozed_until": "2026-01-19T00:00:00Z",
  "snooze_count": 2,
  "last_snoozed_at": "2026-01-12T10:00:00Z"
}
```

**Archive Status (embedded in bookmark):**
```json
{
  "archived": true,
  "archived_at": "2026-01-12T10:00:00Z"
}
```

---

## Troubleshooting

### No resurfacing suggestions
- Check that you have bookmarks older than 1 day
- Verify bookmarks aren't all archived
- Check `MIN_RESURFACING_SCORE` threshold

### Suggestions not relevant
- Access a few bookmarks to establish patterns
- Add tags to bookmarks to improve relevance
- Check knowledge graph for entity connections

### Same bookmarks appearing repeatedly
- Mark as read to update access history
- Snooze for longer periods
- Consider archiving if no longer relevant

---

## Related Features

- **[Knowledge Graph](knowledge-graph.md)** - Powers relevance scoring
- **[Analytics](analytics.md)** - Tracks resurfacing effectiveness
- **[Content Intelligence](content-intelligence.md)** - Quality factor in scoring

---

## Research & References

The resurfacing algorithm is based on:
- **SuperMemo SM-2** - Original spaced repetition algorithm
- **Ebbinghaus Forgetting Curve** - Memory decay research
- **Leitner System** - Flashcard scheduling methodology

**Academic Papers:**
- Wozniak, P. (1990). "SuperMemo 2 Algorithm"
- Ebbinghaus, H. (1885). "Memory: A Contribution to Experimental Psychology"

**Implementation references:**
- [documentation/api/README.md](../api/README.md#resurfacing-endpoints)
- [documentation/architecture.md](../architecture.md)

---

**Last Updated:** May 10, 2026
**Status:** Implemented for in-app suggestions, snooze, archive, unarchive, and Memory Jogger
