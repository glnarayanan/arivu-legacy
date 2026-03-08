# Architecture

Arivu is an AI-native bookmarking application. This document describes the system architecture for contributors.

## System Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Browser    │     │   Extension  │     │  X OAuth API │
│   (React)    │     │  (Manifest   │     │              │
│              │     │    V3)       │     │              │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │  HTTP/Cookies      │  HTTP/Token        │  OAuth 2.0
       ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
│                    (server.py)                           │
│                                                         │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │  Auth   │ │Bookmarks │ │Analytics │ │ AI Service │ │
│  │ Router  │ │ Router   │ │ Router   │ │  (Gemini)  │ │
│  └─────────┘ └──────────┘ └──────────┘ └────────────┘ │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │Collections│ │Knowledge│ │Resurfacing│ │  Search   │ │
│  │ Router  │ │  Graph   │ │  Router  │ │  Router    │ │
│  └─────────┘ └──────────┘ └──────────┘ └────────────┘ │
└───────────────────────┬─────────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ MongoDB  │  │  Redis   │  │ Gemini   │
   │          │  │ (Cache / │  │   API    │
   │          │  │  Limits) │  │          │
   └──────────┘  └──────────┘  └──────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 19 + Vite | SPA with client-side routing |
| UI | Shadcn/ui + Tailwind CSS | Brutalist design system |
| Animation | Framer Motion | Page transitions, micro-interactions |
| Backend | FastAPI (Python) | REST API server |
| Database | MongoDB (Motor async driver) | Document store for bookmarks, users |
| Cache | Redis | Rate limiting, session cache |
| AI | Google Gemini 2.5 Flash | Summarization, tagging, categorization |
| Extension | Manifest V3 | Browser bookmark capture |
| Marketing | Hugo | Static site with blog |

## Backend Structure

The backend is intentionally monolithic (`server.py`) with extracted routers:

```
backend/
├── server.py                 # Main app — routes not yet extracted
├── analytics.py              # Analytics business logic
├── resurfacing.py            # Resurfacing engine logic
├── app/
│   ├── core/
│   │   ├── config.py         # Settings (env vars, defaults)
│   │   ├── database.py       # MongoDB connection
│   │   ├── dependencies.py   # Auth, rate limiter
│   │   ├── instance_config.py # Runtime API key management
│   │   ├── middleware.py     # CORS, request logging
│   │   └── security.py      # JWT, password hashing
│   ├── models/
│   │   └── bookmark.py       # Pydantic models
│   ├── routers/              # Extracted route handlers
│   │   ├── auth.py
│   │   ├── bookmarks.py
│   │   ├── collections.py
│   │   ├── analytics.py
│   │   ├── knowledge_graph.py
│   │   ├── resurfacing.py
│   │   ├── search.py
│   │   ├── content.py
│   │   └── import_export.py
│   └── services/
│       ├── ai_service.py     # Gemini integration
│       ├── content_service.py # URL content extraction
│       └── email_service.py  # Resend email integration
└── tests/
    ├── conftest.py           # Shared fixtures
    └── test_*.py             # Test modules
```

## Authentication Flow

Arivu uses **cookie-based JWT authentication**:

1. User logs in via `/api/auth/login`
2. Backend sets `access_token` (60 min) and `refresh_token` (30 days) as HTTP-only cookies
3. Frontend sends cookies automatically (`withCredentials: true`)
4. `get_current_user()` dependency validates the access token
5. On 401, the axios interceptor calls `/api/auth/refresh` to get new tokens
6. On refresh failure, the user is redirected to `/auth`

## Data Model

**Core Collections:**

| Collection | Purpose | Key Indexes |
|-----------|---------|-------------|
| `users` | User accounts | `email` (unique) |
| `bookmarks` | Saved URLs with AI metadata | `(user_id, created_at)`, `(user_id, url)` unique |
| `collections` | User-defined groups | `(user_id, name)` unique |
| `ai_summaries` | AI-generated content | `(bookmark_id)` |
| `password_reset_tokens` | Password reset flow | `(token)`, TTL index |
| `import_jobs` | Bulk import tracking | `(user_id, status)` |

## Deployment Options

### Self-Hosted (Recommended)
Uses `docker-compose.selfhosted.yml` — 4 containers:
- **frontend** (nginx serving React + proxying API)
- **backend** (FastAPI with Uvicorn)
- **mongodb** (data persistence)
- **redis** (rate limiting, cache)

### Full Stack (with Marketing Site)
Uses `docker-compose.prod.yml` — adds a 5th container:
- **marketing** (Hugo static site at root, proxies to frontend/backend)

## Key Design Decisions

1. **Monolithic backend** — Single `server.py` keeps deployment simple for self-hosters. Routers are being extracted incrementally.
2. **Cookie-based auth** — More secure than localStorage tokens; works across subdomains.
3. **Background tasks** — AI processing happens asynchronously after bookmark creation to keep responses fast.
4. **User data isolation** — Every database query filters by `user_id`. This is a critical security invariant.
5. **Brutalist design** — Intentional aesthetic choice: sharp corners, offset shadows, bold typography. See `DESIGN_SYSTEM.md`.
