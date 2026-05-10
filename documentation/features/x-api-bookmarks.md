# X (Twitter) Bookmarks Integration

**Last Updated:** May 10, 2026
**Status:** Active (API-based)

This document describes the current X integration implemented in Arivu.

## Overview

Arivu integrates with X using OAuth 2.0 and server-side API calls.

The integration lets users:
- Connect an X account from Settings
- Sync bookmarks from X into Arivu
- Deduplicate by tweet ID and normalized URL
- Process imported bookmarks through Arivu's existing AI pipeline

## Architecture

### Backend Endpoints

All endpoints are under `/api/auth/x`:

- `GET /enabled`: Returns feature flag status
- `GET /connect`: Returns X OAuth authorization URL
- `POST /callback`: Exchanges auth code for tokens and stores connection metadata
- `GET /status`: Returns connection/sync status and profile metadata
- `POST /sync`: Fetches X bookmarks and writes new bookmarks to Arivu
- `POST /disconnect`: Revokes and removes stored X connection

### Frontend Integration

Settings page dynamically shows a `Connections` section when X integration is enabled.

In `Connections`, users can:
- Connect account
- Run manual sync
- View last sync status
- Disconnect account

### Data Flow

1. User clicks `Connect X`
2. Backend builds OAuth URL with PKCE state tracking
3. Callback exchanges code for access and refresh tokens
4. Sync fetches `/2/users/me` then `/2/users/:id/bookmarks`
5. Tweets are mapped into Arivu bookmark schema
6. New bookmarks are enqueued for content and AI processing

## Environment Variables

Set these in `.env` for self-hosted deployments:

- `X_INTEGRATION_ENABLED=true`
- `X_CLIENT_ID=<x-client-id>`
- `X_CLIENT_SECRET=<x-client-secret>`
- `X_REDIRECT_URI=<optional-override>`
- `X_MAX_BOOKMARK_PAGES=<optional, default 10>`
- `X_MAX_BOOKMARKS=<optional, default 300, set 0 for unlimited>`

If `X_REDIRECT_URI` is not set, Arivu defaults to:
- `{APP_URL}/settings?section=connections`

## Deduplication Strategy

Arivu avoids duplicates with two checks:

1. Exact `x_tweet_id` match for existing user bookmarks
2. Normalized URL match (strips tracking query params and fragments)

This prevents duplicate imports when users re-sync.

## Error Handling

Sync status is persisted on the X connection record:

- `idle`
- `syncing`
- `auth_expired`
- `rate_limited`
- `error`

Backend maps X API failures into these statuses for predictable UI behavior.

## Security Notes

- OAuth state is short-lived and stored in Redis
- Access and refresh tokens are stored server-side
- Disconnect attempts token revocation before removing local record
- X integration can be globally disabled with `X_INTEGRATION_ENABLED=false`

## Known Limits

- Sync runs on-demand (manual trigger)
- Maximum sync volume is controlled by `X_MAX_BOOKMARK_PAGES` and `X_MAX_BOOKMARKS`
- Large libraries may require multiple sync runs when caps are configured

## Files to Review

- `backend/server.py`
- `frontend/src/components/settings/ConnectionsSection.jsx`
- `frontend/src/pages/SettingsPage.jsx`
- `backend/tests/test_x_integration.py`
