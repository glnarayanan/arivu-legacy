# Architecture

**Last reviewed:** May 10, 2026

Arivu is an AI-native bookmarking application with a React frontend, FastAPI backend, browser extension, and Typer CLI.

## System Overview

```
Browser / Extension / CLI
        |
        v
frontend nginx or direct API client
        |
        | /api/*
        v
FastAPI backend
        |
        |-- MongoDB: users, bookmarks, collections, AI summaries, imports, runtime settings
        |-- Redis: rate limiting and account lockout state
        |-- Gemini: summaries, tags, highlights, graph enrichment, analytics insights
        |-- Resend: password reset email when configured
        |-- X API: OAuth-based bookmark sync when enabled
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React 19 + Vite | SPA with client-side routing |
| UI | Shadcn/ui + Tailwind CSS | Brutalist component system |
| Animation | Framer Motion | Page transitions and interaction feedback |
| Backend | FastAPI + Uvicorn | REST API server |
| Database | MongoDB + Motor | Async document persistence |
| Cache/state | Redis | Rate limiting and lockout state |
| AI | Google Gemini | Content enrichment and semantic features |
| Extension | Manifest V3 | Browser save flow |
| CLI | Typer + Rich | Terminal workflow and local stack orchestration |

## Backend Structure

`backend/server.py` is the FastAPI entry point. Feature routes are split between extracted routers and remaining routes in `server.py`.

```
backend/
├── server.py
├── analytics.py
├── resurfacing.py
├── app/
│   ├── core/          # config, database, auth dependencies, middleware
│   ├── routers/       # auth, bookmarks, collections, content, search, graph, analytics, imports
│   ├── services/      # AI, content extraction, email, lockout, search helpers
│   ├── models/        # Pydantic models
│   └── cli/           # Typer CLI
├── migrations/
└── tests/
```

Security invariant: user-scoped data access must filter by `user_id`. Keep this explicit in database queries.

## Authentication

- Web auth uses HTTP-only `access_token` and `refresh_token` cookies.
- Access tokens last 60 minutes; refresh tokens last 30 days by default.
- CLI auth uses `/api/auth/cli/login` and stores bearer tokens in the CLI config store.
- Browser extension auth uses `/api/auth/extension-token`.
- Account lockout state is tracked through Redis when available.

## Deployment

The active Docker stack is `docker-compose.yml`:

- `frontend`: nginx serves the built React app and proxies `/api/*` to `backend:8001`
- `backend`: FastAPI/Uvicorn
- `mongodb`: persistence
- `redis`: rate limiting and lockout state

See `documentation/deployment/DEPLOYMENT.md` for current commands and environment guidance.

## Runtime Configuration

Core settings come from environment variables loaded by `backend/app/core/config.py`.

Admin runtime API key overrides are handled by `backend/app/core/instance_config.py` and stored in MongoDB `instance_settings`. Sensitive overrides are encrypted with a Fernet key derived from `SECRET_KEY`.

## Feature Areas

- Bookmark CRUD, preview, duplicates, related bookmarks, read status, bulk operations
- Content intelligence and AI enrichment
- Collections
- Hybrid keyword and semantic search
- Knowledge graph exploration and query expansion
- Resurfacing and Memory Jogger
- Analytics
- Import/export and backup
- X OAuth/API bookmark sync
- Admin console for users, API keys, system health, and activity
