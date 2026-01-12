# Arivu API Documentation

**Base URL:** `/api`
**Authentication:** HTTP-only cookies (access_token, refresh_token)
**Last Updated:** January 12, 2026

---

## Overview

The Arivu API is a RESTful API built with FastAPI. All endpoints require authentication except for signup, login, and health check.

### Authentication

Authentication uses HTTP-only cookies set by the backend:
- `access_token` - Valid for 60 minutes
- `refresh_token` - Valid for 30 days

The frontend automatically sends cookies with each request via `axios.defaults.withCredentials = true`.

---

## API Categories

1. [Authentication](#authentication-endpoints) - Signup, login, logout, token refresh
2. [Bookmarks](#bookmarks-endpoints) - CRUD operations for bookmarks
3. [Knowledge Graph](#knowledge-graph-endpoints) - Semantic AI knowledge graph
4. [Resurfacing](#resurfacing-endpoints) - Intelligent resurfacing engine
5. [Analytics](#analytics-endpoints) - Reading statistics and insights
6. [Duplicates](#duplicates-endpoints) - Duplicate detection and merging
7. [Collections](#collections-endpoints) - Bookmark collections
8. [Import/Export](#importexport-endpoints) - Data migration
9. [Content Intelligence](#content-intelligence-endpoints) - Content evaluation

---

## Authentication Endpoints

### POST /api/auth/signup
Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

**Cookies Set:**
- `access_token` (HTTP-only, 60 min)
- `refresh_token` (HTTP-only, 30 days)

---

### POST /api/auth/login
Login to existing account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

**Cookies Set:** Same as signup

---

### GET /api/auth/me
Get current user information.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "id": "user_abc123",
  "email": "user@example.com",
  "created_at": "2026-01-01T00:00:00Z"
}
```

---

### POST /api/auth/logout
Logout and clear authentication cookies.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "message": "Logged out successfully"
}
```

**Cookies Cleared:** `access_token`, `refresh_token`

---

### POST /api/auth/refresh
Refresh access token using refresh token.

**Authentication:** Refresh token required

**Response:** `200 OK`
```json
{
  "access_token": "new_token",
  "token_type": "bearer"
}
```

---

## Bookmarks Endpoints

### POST /api/bookmarks
Create a new bookmark.

**Authentication:** Required

**Request Body:**
```json
{
  "url": "https://example.com/article",
  "title": "Optional custom title",
  "tags": ["optional", "tags"]
}
```

**Response:** `200 OK`
```json
{
  "id": "bookmark_xyz789",
  "url": "https://example.com/article",
  "title": "Article Title",
  "summary": null,
  "highlights": [],
  "tags": [],
  "created_at": "2026-01-12T10:00:00Z",
  "status": "processing"
}
```

**Note:** Content fetching and AI processing happens in background. Status will change to "completed" once processing finishes.

---

### GET /api/bookmarks
List all bookmarks for the authenticated user.

**Authentication:** Required

**Query Parameters:**
- `limit` (optional): Number of bookmarks to return (default: 100, max: 500)
- `offset` (optional): Pagination offset (default: 0)
- `tag` (optional): Filter by tag
- `search` (optional): Search in title and content

**Response:** `200 OK`
```json
[
  {
    "id": "bookmark_xyz789",
    "url": "https://example.com/article",
    "title": "Article Title",
    "summary": "One-sentence summary",
    "one_sentence_summary": "One-sentence summary",
    "bullet_points": ["Point 1", "Point 2", "Point 3"],
    "highlights": ["Key quote 1", "Key quote 2"],
    "tags": ["ai", "technology"],
    "created_at": "2026-01-12T10:00:00Z",
    "read_status": false,
    "reading_time_minutes": 5,
    "status": "completed"
  }
]
```

---

### GET /api/bookmarks/{bookmark_id}
Get a single bookmark by ID.

**Authentication:** Required

**Response:** `200 OK` - Returns full bookmark object with all fields

---

### GET /api/bookmarks/{bookmark_id}/related
Get related bookmarks based on content similarity.

**Authentication:** Required

**Query Parameters:**
- `limit` (optional): Number of related bookmarks (default: 5, max: 20)

**Response:** `200 OK`
```json
[
  {
    "id": "related_bookmark_1",
    "title": "Related Article",
    "url": "https://example.com/related",
    "similarity_score": 0.85
  }
]
```

---

### DELETE /api/bookmarks/{bookmark_id}
Delete a bookmark.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "message": "Bookmark deleted successfully"
}
```

---

### POST /api/bookmarks/bulk-delete
Delete multiple bookmarks at once.

**Authentication:** Required

**Request Body:**
```json
{
  "bookmark_ids": ["id1", "id2", "id3"]
}
```

**Response:** `200 OK`
```json
{
  "deleted_count": 3
}
```

---

### PATCH /api/bookmarks/{bookmark_id}/read-status
Mark bookmark as read or unread.

**Authentication:** Required

**Request Body:**
```json
{
  "read_status": true
}
```

**Response:** `200 OK`

---

### POST /api/bookmarks/bulk-mark-read
Mark multiple bookmarks as read.

**Authentication:** Required

**Request Body:**
```json
{
  "bookmark_ids": ["id1", "id2", "id3"]
}
```

**Response:** `200 OK`

---

### POST /api/bookmarks/{bookmark_id}/accessed
Record that a bookmark was accessed (for analytics).

**Authentication:** Required

**Response:** `200 OK`

---

## Knowledge Graph Endpoints

### GET /api/knowledge-graph/explore
Explore the knowledge graph with entities and relationships.

**Authentication:** Required

**Query Parameters:**
- `entity` (optional): Focus on specific entity
- `depth` (optional): Graph depth (default: 2, max: 5)

**Response:** `200 OK`
```json
{
  "nodes": [
    {
      "id": "entity_1",
      "label": "Artificial Intelligence",
      "type": "concept",
      "bookmark_count": 15
    }
  ],
  "edges": [
    {
      "source": "entity_1",
      "target": "entity_2",
      "relationship": "related_to",
      "strength": 0.85
    }
  ]
}
```

---

### GET /api/knowledge-graph/search
Search for entities in the knowledge graph.

**Authentication:** Required

**Query Parameters:**
- `query`: Search query string
- `limit` (optional): Max results (default: 10, max: 50)

**Response:** `200 OK`
```json
{
  "results": [
    {
      "entity": "Machine Learning",
      "type": "concept",
      "related_bookmarks": 8,
      "relevance_score": 0.92
    }
  ]
}
```

---

### POST /api/knowledge-graph/regenerate-embeddings
Regenerate embeddings for the knowledge graph (admin operation).

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "message": "Embeddings regeneration started",
  "job_id": "job_123"
}
```

---

## Resurfacing Endpoints

### GET /api/resurfacing
Get bookmarks recommended for resurfacing based on spaced repetition algorithm.

**Authentication:** Required

**Query Parameters:**
- `limit` (optional): Number of bookmarks (default: 10, max: 50)

**Response:** `200 OK`
```json
[
  {
    "id": "bookmark_xyz",
    "title": "Article to review",
    "url": "https://example.com/article",
    "resurfacing_score": 0.85,
    "resurfacing_reason": "Optimal review interval reached",
    "days_since_last_access": 14,
    "previous_access_count": 2
  }
]
```

---

### GET /api/bookmarks/aged
Get bookmarks that haven't been accessed in a long time.

**Authentication:** Required

**Query Parameters:**
- `days` (optional): Minimum days since last access (default: 30)
- `limit` (optional): Max results (default: 20)

**Response:** `200 OK` - Returns array of bookmark objects

---

### POST /api/resurfacing/{bookmark_id}/snooze
Snooze a bookmark from resurfacing suggestions.

**Authentication:** Required

**Request Body:**
```json
{
  "days": 7
}
```

**Response:** `200 OK`
```json
{
  "message": "Bookmark snoozed for 7 days",
  "snooze_until": "2026-01-19T00:00:00Z"
}
```

---

### POST /api/resurfacing/{bookmark_id}/archive
Archive a bookmark (remove from resurfacing).

**Authentication:** Required

**Response:** `200 OK`

---

### POST /api/resurfacing/{bookmark_id}/unarchive
Unarchive a bookmark.

**Authentication:** Required

**Response:** `200 OK`

---

## Analytics Endpoints

### GET /api/analytics/reading-stats
Get reading statistics for the user.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "total_bookmarks": 156,
  "bookmarks_read": 89,
  "bookmarks_unread": 67,
  "reading_percentage": 57.1,
  "total_reading_time_minutes": 2340,
  "average_reading_time_minutes": 15,
  "bookmarks_this_week": 12,
  "bookmarks_this_month": 45
}
```

---

### GET /api/analytics/topics
Get topic distribution across bookmarks.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "topics": [
    {
      "topic": "Artificial Intelligence",
      "count": 45,
      "percentage": 28.8
    },
    {
      "topic": "Web Development",
      "count": 32,
      "percentage": 20.5
    }
  ]
}
```

---

### GET /api/analytics/patterns
Get reading patterns and habits.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "most_active_day": "Monday",
  "most_active_hour": 14,
  "average_bookmarks_per_day": 2.3,
  "reading_streak_days": 7,
  "longest_streak_days": 21
}
```

---

### GET /api/analytics/insights
Get AI-generated insights about reading habits.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "insights": [
    "You've been reading more about AI lately",
    "Your reading consistency has improved by 20% this month",
    "Consider revisiting your unread bookmarks from 2 months ago"
  ],
  "recommendations": [
    "Check out the Knowledge Graph to discover connections",
    "Try the Resurfacing feature to review past content"
  ]
}
```

---

### GET /api/analytics/summary
Get comprehensive analytics summary.

**Authentication:** Required

**Response:** `200 OK` - Combines stats, topics, patterns, and insights

---

## Duplicates Endpoints

### GET /api/bookmarks/duplicates/detect
Detect duplicate bookmarks.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "duplicate_groups": [
    {
      "canonical_id": "bookmark_1",
      "duplicates": [
        {
          "id": "bookmark_2",
          "similarity_score": 0.95,
          "reason": "Same URL"
        },
        {
          "id": "bookmark_3",
          "similarity_score": 0.87,
          "reason": "High content similarity"
        }
      ]
    }
  ],
  "total_duplicates": 2
}
```

---

### POST /api/bookmarks/merge
Merge duplicate bookmarks.

**Authentication:** Required

**Request Body:**
```json
{
  "primary_id": "bookmark_1",
  "duplicate_ids": ["bookmark_2", "bookmark_3"],
  "merge_strategy": "keep_all_tags"
}
```

**Response:** `200 OK`
```json
{
  "merged_bookmark": {
    "id": "bookmark_1",
    "tags": ["merged", "tags", "from", "all"],
    "highlights": ["merged highlights"]
  },
  "deleted_ids": ["bookmark_2", "bookmark_3"]
}
```

---

## Collections Endpoints

### GET /api/collections
List all collections for the user.

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "collection_1",
    "name": "AI Research",
    "description": "Articles about AI",
    "bookmark_count": 23,
    "created_at": "2026-01-01T00:00:00Z"
  }
]
```

---

### POST /api/collections
Create a new collection.

**Authentication:** Required

**Request Body:**
```json
{
  "name": "New Collection",
  "description": "Optional description"
}
```

**Response:** `200 OK` - Returns created collection object

---

### POST /api/collections/{collection_id}/add
Add a bookmark to a collection.

**Authentication:** Required

**Request Body:**
```json
{
  "bookmark_id": "bookmark_xyz"
}
```

**Response:** `200 OK`

---

## Import/Export Endpoints

### POST /api/bookmarks/import
Import bookmarks from external services.

**Authentication:** Required

**Request Body:**
```json
{
  "source": "pocket",
  "file_content": "... (HTML or JSON export)",
  "format": "html"
}
```

**Response:** `200 OK`
```json
{
  "job_id": "import_job_123",
  "status": "processing",
  "message": "Import started"
}
```

**Supported Sources:**
- Pocket
- Raindrop.io
- Chrome Bookmarks
- Firefox Bookmarks
- Generic HTML/JSON

---

### GET /api/import-jobs
List all import jobs for the user.

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "import_job_123",
    "status": "completed",
    "source": "pocket",
    "total_bookmarks": 150,
    "imported_count": 145,
    "failed_count": 5,
    "created_at": "2026-01-12T10:00:00Z",
    "completed_at": "2026-01-12T10:05:00Z"
  }
]
```

---

### GET /api/import-jobs/{job_id}
Get status of a specific import job.

**Authentication:** Required

**Response:** `200 OK` - Returns import job object

---

### GET /api/bookmarks/export
Export all bookmarks.

**Authentication:** Required

**Query Parameters:**
- `format`: Export format (`json`, `html`, `csv`)

**Response:** `200 OK`
```json
{
  "format": "json",
  "data": [ /* array of bookmarks */ ],
  "export_date": "2026-01-12T10:00:00Z",
  "total_bookmarks": 156
}
```

---

## Content Intelligence Endpoints

### POST /api/content/evaluate
Evaluate content quality of a URL.

**Authentication:** Required

**Request Body:**
```json
{
  "url": "https://example.com/article"
}
```

**Response:** `200 OK`
```json
{
  "quality_score": 0.85,
  "factors": {
    "readability": 0.9,
    "depth": 0.8,
    "originality": 0.85,
    "citations": 0.7
  },
  "recommendation": "High quality content worth saving"
}
```

---

### POST /api/content/check-duplicate
Check if content is a duplicate before saving.

**Authentication:** Required

**Request Body:**
```json
{
  "url": "https://example.com/article"
}
```

**Response:** `200 OK`
```json
{
  "is_duplicate": true,
  "existing_bookmark_id": "bookmark_abc",
  "similarity_score": 0.95
}
```

---

## Error Responses

All endpoints may return these error codes:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Access denied"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

- **Default:** 100 requests per minute per user
- **Import endpoints:** 10 requests per hour per user
- **Export endpoints:** 5 requests per hour per user

Rate limit headers:
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets

---

## Pagination

List endpoints support pagination via query parameters:
- `limit`: Number of items (default varies by endpoint)
- `offset`: Skip N items

Response includes pagination metadata:
```json
{
  "data": [ /* items */ ],
  "pagination": {
    "total": 156,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

---

## Webhooks

*Coming soon in Q2 2026*

---

## API Versioning

Current version: **v1** (implicit in `/api` prefix)

Future versions will use explicit versioning: `/api/v2`

---

**Last Updated:** January 12, 2026
**API Version:** 1.0
**Questions?** See main documentation at `/documentation/`
