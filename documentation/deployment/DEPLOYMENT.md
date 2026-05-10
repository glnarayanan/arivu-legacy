# Arivu Deployment Guide

**Last Updated:** May 10, 2026
**Current stack:** Frontend nginx entry point, FastAPI backend, MongoDB, Redis

This guide reflects the files currently present in the repository. The active Docker deployment file is `docker-compose.yml`.

## Architecture

```
Browser
  |
  v
frontend nginx :80
  |-- serves React/Vite static app
  |-- proxies /api/* to backend:8001
  v
backend FastAPI
  |-- MongoDB for users, bookmarks, AI summaries, imports, settings
  |-- Redis for rate limiting and lockout state
  |-- Gemini API for AI enrichment
```

Only the frontend container publishes a public port by default. Backend, MongoDB, and Redis stay on the Docker network.

## Local Docker Quick Start

Prerequisites:

- Docker Desktop or Docker Engine with Compose
- Ports `80`, `27017`, and `6379` available if you keep the default compose file
- A valid `SECRET_KEY` with at least 32 characters

```bash
cp .env.example .env
openssl rand -hex 32
# Paste the generated value into SECRET_KEY in .env.
# Add GEMINI_API_KEY if you want AI summaries, tagging, graph, and analytics.

docker compose up -d --build
docker compose ps
```

Access points:

- App: `http://localhost/auth`
- Dashboard after login: `http://localhost/dashboard`
- Backend health through nginx: `http://localhost/api/health`
- Direct backend docs from host are not exposed by default in Docker Compose. Use a manual backend run if you need `/docs` directly.

Useful commands:

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose restart backend
docker compose down
docker compose down -v
```

## Manual Development

Manual development is useful for faster frontend/backend iteration.

Start MongoDB and Redis:

```bash
docker compose up -d mongodb redis
```

Run the backend:

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env
# Edit backend/.env or export variables in your shell.
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

For local backend development, use a host-reachable database URL:

```bash
MONGO_URL=mongodb://admin:changeme123@localhost:27017/?authSource=admin
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<32+ character value>
GEMINI_API_KEY=<optional>
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

Run the frontend:

```bash
cd frontend
yarn install
yarn dev
```

The frontend uses a relative `/api` base path in `frontend/src/utils/axiosConfig.jsx`. In Docker, nginx proxies `/api` to the backend. In manual development, configure Vite proxying if you need the browser dev server to forward `/api` to `localhost:8001`.

## CLI Local Workflow

The backend package includes a Typer CLI that can manage the local Docker stack and create a `local` profile.

```bash
cd backend
pip install -r requirements.txt
pip install -e .

arivu local up
arivu auth login --profile local
arivu save https://example.com/article
arivu search "example topic"
arivu local logs backend
```

`arivu local up` expects a repo root `.env` with a valid `SECRET_KEY`.

## Production Deployment

1. Provision a host with Docker and Compose.
2. Point your domain or reverse proxy at the host.
3. Clone the repository and create `.env`.
4. Set production values:

```bash
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=<strong password>
DB_NAME=arivu_db
MONGO_URL=mongodb://admin:<strong password>@mongodb:27017/arivu_db?authSource=admin
REDIS_URL=redis://redis:6379/0
ENVIRONMENT=production
SECRET_KEY=<openssl rand -hex 32>
CORS_ORIGINS=https://your-domain.example
ADMIN_EMAILS=admin@your-domain.example
GEMINI_API_KEY=<gemini key>
APP_URL=https://your-domain.example
SIGNUPS_ENABLED=false
LOG_LEVEL=info
```

5. Start the stack:

```bash
docker compose up -d --build
docker compose ps
curl http://localhost/api/health
```

6. Put TLS in front of the frontend container. Common options:

- Cloudflare proxied DNS with HTTPS at the edge
- Host-level nginx/Caddy/Traefik terminating TLS and forwarding to `127.0.0.1:80`
- Platform-managed HTTPS on your VPS provider

Firewall guidance:

- Allow `80/tcp` and `443/tcp` as needed.
- Do not expose MongoDB or Redis publicly.
- If you expose direct backend access for debugging, restrict it by firewall or VPN.

## X Integration

Set these values to enable server-side X bookmarks sync:

```bash
X_INTEGRATION_ENABLED=true
X_CLIENT_ID=<x oauth client id>
X_CLIENT_SECRET=<x oauth client secret>
APP_URL=https://your-domain.example
# Optional override:
X_REDIRECT_URI=https://your-domain.example/settings?section=connections
X_MAX_BOOKMARK_PAGES=10
X_MAX_BOOKMARKS=300
```

The redirect URI configured in the X Developer Portal should match the value shown in the app settings flow.

## Runtime API Keys

Admins listed in `ADMIN_EMAILS` can configure Gemini, X, and Resend keys in the web app under **Settings -> API Keys**. Runtime overrides are stored in MongoDB and encrypted at rest. If an override is absent, the backend falls back to the corresponding environment variable.

Rotating `SECRET_KEY` invalidates auth sessions and makes existing encrypted runtime API key overrides unreadable; re-enter those keys after rotation.

## Verification

Run these checks after deployment:

```bash
docker compose ps
curl http://localhost/api/health
docker compose logs --tail=100 backend
```

Then verify in the browser:

- Login/signup behavior matches `SIGNUPS_ENABLED`.
- Saving a bookmark creates a pending item and later fills AI metadata when `GEMINI_API_KEY` is configured.
- `/settings?section=connections` shows X connection controls only when X integration is enabled.
- Admin-only pages are visible only to emails in `ADMIN_EMAILS`.

## Updates

```bash
git pull origin main
docker compose up -d --build
docker compose ps
```

If dependencies or database behavior changed, review `CHANGELOG.md`, `documentation/deployment/ENVIRONMENT_VARIABLES.md`, and any migration scripts under `backend/migrations/`.
