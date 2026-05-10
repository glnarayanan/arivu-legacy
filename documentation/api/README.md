# Arivu API Documentation

**Base URL:** `/api`
**Authentication:** HTTP-only cookies (access_token, refresh_token)
**Last Updated:** May 10, 2026

---

## Overview

The Arivu API is a RESTful API built with FastAPI. Most endpoints require authentication. Public endpoints include health checks, login/signup flows, token refresh flows that use a refresh token, password reset entry points, invite acceptance, and the X integration enabled check.

### Authentication

Authentication uses HTTP-only cookies set by the backend:
- `access_token` - Valid for 60 minutes
- `refresh_token` - Valid for 30 days

The frontend axios instance automatically sends cookies with each request via `withCredentials: true`.

---

## API Categories

1. [Authentication and User](#authentication-and-user-endpoints) - Login, logout, token refresh, profile, password, extension token
2. [X Integration](#x-integration-endpoints) - OAuth connect, sync, status, disconnect
3. [Bookmarks](#bookmarks-endpoints) - CRUD operations for bookmarks
4. [Search](#search-endpoints) - Hybrid keyword + semantic search
5. [Knowledge Graph](#knowledge-graph-endpoints) - Semantic AI knowledge graph
6. [Resurfacing](#resurfacing-endpoints) - Intelligent resurfacing engine
7. [Analytics](#analytics-endpoints) - Reading statistics and insights
8. [Duplicates](#duplicates-endpoints) - Duplicate detection and merging
9. [Collections](#collections-endpoints) - Bookmark collections
10. [Import/Export](#importexport-endpoints) - Data migration
11. [Content Intelligence](#content-intelligence-endpoints) - Content evaluation
12. [Admin](#admin-endpoints) - User management, runtime API keys, and system health
13. [Health](#health-endpoints) - Service health checks

---

## Authentication and User Endpoints

### POST /api/auth/signup
Create a new user account.

**Note:** Signups return `403` when `SIGNUPS_ENABLED=false`.

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

### POST /api/auth/cli/login
Authenticate a CLI user and return bearer tokens in the response body.

**Authentication:** Not required

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
  "token_type": "bearer",
  "access_token_expires_at": "2026-03-21T12:00:00+00:00",
  "refresh_token_expires_at": "2026-04-20T12:00:00+00:00",
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "name": "Example User"
  }
}
```

**Notes:**
- Intended for terminal and non-browser clients
- Uses the same credential validation and lockout rules as `/api/auth/login`

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

### POST /api/auth/extension-token
Generate bearer tokens for the browser extension from an authenticated web session.

**Authentication:** Required cookie session

**Response:** `200 OK`
```json
{
  "access_token": "...",
  "refresh_token": "..."
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

### POST /api/auth/cli/refresh
Refresh CLI bearer tokens using a refresh token.

**Authentication:** Refresh token required in request body

**Request Body:**
```json
{
  "refresh_token": "..."
}
```

**Response:** `200 OK`
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "access_token_expires_at": "2026-03-21T12:00:00+00:00",
  "refresh_token_expires_at": "2026-04-20T12:00:00+00:00",
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "name": "Example User"
  }
}
```

**Notes:**
- Rejects access tokens and invalid token types
- Rotates both access and refresh tokens for CLI consumers

---

### POST /api/auth/forgot-password
Request a password reset email when Resend email configuration is available.

**Authentication:** Not required

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

---

### POST /api/auth/reset-password
Complete password reset with a reset token.

**Authentication:** Not required

**Request Body:**
```json
{
  "token": "reset-token",
  "new_password": "new-secure-password"
}
```

---

### POST /api/auth/change-password
Change the current authenticated user's password.

**Authentication:** Required

**Request Body:**
```json
{
  "current_password": "old-password",
  "new_password": "new-secure-password"
}
```

---

### POST /api/auth/accept-invite
Accept an admin-created invite and set the account password.

**Authentication:** Not required

**Request Body:**
```json
{
  "token": "invite-token",
  "password": "secure-password"
}
```

---

### GET /api/user/profile
Return the current user's profile document excluding password hash.

**Authentication:** Required

---

### PUT /api/user/profile
Update the current user's `name` and/or `email`.

**Authentication:** Required

---

### POST /api/user/avatar
Upload a base64-encoded avatar image. The decoded image limit is 1.5 MB.

**Authentication:** Required

---

### DELETE /api/user/avatar
Remove the current user's avatar.

**Authentication:** Required

---

## X Integration Endpoints

These endpoints are available only when `X_INTEGRATION_ENABLED=true`.

### GET /api/auth/x/enabled
Returns whether X integration is enabled.

**Response:** `200 OK`
```json
{
  "enabled": true
}
```

---

### GET /api/auth/x/connect
Starts OAuth by generating and returning the X authorization URL.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "auth_url": "https://twitter.com/i/oauth2/authorize?..."
}
```

---

### POST /api/auth/x/callback
Completes OAuth exchange and stores the X connection.

**Authentication:** Required

**Request Body:**
```json
{
  "code": "oauth_code",
  "state": "oauth_state"
}
```

**Response:** `200 OK`
```json
{
  "connected": true,
  "x_username": "example_user",
  "x_name": "Example User"
}
```

---

### GET /api/auth/x/status
Returns connection metadata and sync status.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "connected": true,
  "x_username": "example_user",
  "x_name": "Example User",
  "last_sync_at": "2026-02-19T12:00:00Z",
  "sync_status": "idle",
  "total_synced": 240
}
```

---

### POST /api/auth/x/sync
Fetches bookmarks from X and imports new ones into Arivu.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "total_fetched": 100,
  "new_bookmarks": 32,
  "duplicates_skipped": 68
}
```

---

### POST /api/auth/x/disconnect
Revokes and removes X connection metadata.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "disconnected": true
}
```

---

## Bookmarks Endpoints

### POST /api/bookmarks
Create a new bookmark.

**Authentication:** Required

**Clients:**
- Web app via HTTP-only cookies
- Browser extension via bearer token from `/api/auth/extension-token`
- CLI via bearer token from `/api/auth/cli/login`

**Request Body:**
```json
{
  "url": "https://example.com/article",
  "collection_id": "optional-collection-id"
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

### POST /api/bookmarks/preview
Fetch URL metadata before saving a bookmark.

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
  "url": "https://example.com/article",
  "title": "Article Title",
  "description": "Short page description",
  "domain": "example.com",
  "favicon": "https://example.com/favicon.ico",
  "thumbnail": null,
  "reading_time": 5
}
```

**Security:** Uses the same server-side URL safety checks as bookmark ingestion, including DNS-aware private-address blocking and redirect revalidation.

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

## Search Endpoints

### GET /api/search
Unified hybrid search combining keyword matching and semantic similarity.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | string | required | Search query (min 2 chars) |
| limit | int | 20 | Max results to return |
| use_semantic | bool | true | Enable semantic similarity |
| use_keyword | bool | true | Enable keyword matching |
| domain | string | null | Filter by domain |
| collection_id | string | null | Filter by collection |
| read_status | string | null | "read" or "unread" |

**Response:** `200 OK`
```json
{
  "results": [
    {
      "id": "bookmark_id",
      "title": "Example Title",
      "url": "https://example.com",
      "relevance_score": 0.85,
      "keyword_score": 0.6,
      "semantic_score": 0.95,
      "ai_summary": {...}
    }
  ],
  "query": "machine learning",
  "total": 15,
  "search_mode": {
    "semantic": true,
    "keyword": true
  },
  "message": null
}
```

**Notes:**
- Uses two-stage retrieval: keyword candidate filtering → semantic reranking
- Combines scores: `relevance = 0.7 * semantic + 0.3 * keyword`
- Minimum semantic threshold of 0.25 filters low-quality matches

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

### GET /api/knowledge-graph/expand-query
Expand a search query with semantically related entities and concepts.

**Authentication:** Required

**Query Parameters:**
- `query`: Search query string

**Response:** `200 OK` - Returns expanded query terms and related concepts.

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

### GET /api/memory-jogger
Get a single featured bookmark for today's memory jogger.
Uses scoring algorithm to surface forgotten but relevant bookmarks.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "bookmark": {
    "id": "bookmark_xyz",
    "title": "Forgotten Gem",
    "url": "https://example.com",
    "ai_summary": { "one_sentence": "..." }
  },
  "context": {
    "days_since_saved": 45,
    "connection_count": 3,
    "connected_topics": ["ai", "react"],
    "reason": "You haven't visited this in 45 days"
  },
  "has_memory": true
}
```

---

### POST /api/memory-jogger/dismiss
Dismiss today's memory jogger.

**Authentication:** Required

**Request Body:**
```json
{
  "bookmark_id": "bookmark_xyz"
}
```

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
    "bookmark_ids": ["bookmark_1", "bookmark_2"],
    "user_id": "user_123",
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
  "name": "New Collection"
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
Raw UTF-8 file contents. Browser bookmark HTML, CSV, plain URL lists, and Raindrop JSON are accepted. Send `X-Import-Source: raindrop` for Raindrop JSON exports.

**Response:** `200 OK`
```json
{
  "message": "Imported 2 bookmarks",
  "count": 2,
  "import_job_id": "import_job_123"
}
```

**Supported Sources:**
- Pocket
- Raindrop.io
- Chrome Bookmarks
- Firefox Bookmarks
- Generic HTML, CSV, plain text URL lists, and Raindrop-style JSON

Unsafe URLs are skipped during import before placeholder bookmarks are created.

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

### POST /api/bookmarks/backup
Create a bookmark backup in the requested format.

**Authentication:** Required

**Request Body:**
```json
{
  "format": "json",
  "include_notes": true,
  "include_ai_summaries": true,
  "date_from": null,
  "date_to": null
}
```

**Response:** `200 OK` - Returns backup payload for the selected format.

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

## Admin Endpoints

Admin endpoints require an authenticated user whose email is listed in `ADMIN_EMAILS`.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/admin/overview` | High-level usage and system overview |
| GET | `/api/admin/api-usage` | API usage metrics |
| GET | `/api/admin/users` | Paginated user list |
| GET | `/api/admin/users/{user_id}` | User detail |
| POST | `/api/admin/users/invite` | Create an invite for a new user |
| POST | `/api/auth/accept-invite` | Accept an invite and create credentials |
| POST | `/api/admin/users/{user_id}/ban` | Ban a user |
| POST | `/api/admin/users/{user_id}/unban` | Unban a user |
| POST | `/api/admin/users/{user_id}/reset-password` | Admin-triggered password reset |
| DELETE | `/api/admin/users/{user_id}` | Delete a user and their data |
| GET | `/api/admin/api-keys` | Show runtime API key configuration status |
| PUT | `/api/admin/api-keys` | Save runtime API key overrides |
| DELETE | `/api/admin/api-keys/{key_name}` | Remove a runtime API key override |
| GET | `/api/admin/system` | Database and service health summary |
| GET | `/api/admin/activity` | Recent admin/system activity feed |
| GET | `/api/admin/collections-stats` | Collection usage stats |

Runtime API key overrides are stored in MongoDB `instance_settings`; sensitive values are encrypted with a Fernet key derived from `SECRET_KEY`. Environment variables remain the fallback when no DB override exists.

---

## Health Endpoints

### GET /api/health
Returns backend health and database connectivity status.

**Authentication:** Not required

---

## API Versioning

Current version: **v1** (implicit in `/api` prefix)

Future versions will use explicit versioning: `/api/v2`

---

**Last Updated:** May 10, 2026
**API Version:** 1.0
**Questions?** See main documentation at `/documentation/`
