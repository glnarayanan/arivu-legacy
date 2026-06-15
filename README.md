# Arivu Legacy

**Status:** Archived legacy implementation
**License:** MIT

> Transform saved web pages into instantly useful knowledge with AI-powered summaries, highlights, and smart organization.

## This Repository Is Archived

The active Arivu project now lives at [glnarayanan/arivu](https://github.com/glnarayanan/arivu).

This repository is kept as `arivu-legacy` for historical reference to the original Python/FastAPI, MongoDB, Redis, React, and Vite implementation. The project moved to a new repository because Arivu was rebuilt as a low-dependency Go single-binary application with embedded frontend assets, SQLite persistence, and a smaller supply-chain surface.

The rewrite preserves the product direction and user workflows while making the deployable artifact simpler to operate, easier to audit, and less dependent on broad npm/Python dependency trees. New development, issues, security fixes, and documentation updates should happen in the new repository.

---

## Quick Start

For the current supported implementation:

```bash
git clone https://github.com/glnarayanan/arivu.git
cd arivu
```

For this archived legacy implementation:

```bash
git clone https://github.com/glnarayanan/arivu-legacy.git
cd arivu-legacy
cp .env.example .env  # Add GEMINI_API_KEY and SECRET_KEY
docker-compose up -d --build

# Access: http://localhost/auth
```

This runs four containers: frontend (port 80), backend, MongoDB, and Redis.

### Manual Development

**Prerequisites:** Python 3.11+, Node.js 18+, MongoDB, Gemini API Key

```bash
# Backend (Terminal 1)
cd backend
pip install -r requirements.txt
cp ../.env.example .env  # Add MONGO_URL, SECRET_KEY, and GEMINI_API_KEY
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend (Terminal 2)
cd frontend
yarn install
yarn dev
```

### Browser Extension

See `extension/README.md` for Chrome/Firefox installation instructions.

---

## Architecture

Four containers — frontend nginx is the entry point:

```
┌─────────────────────────────────────────────────────────┐
│                  Port 80 (Frontend nginx)               │
│  ┌─────────────────────────────────────────────────┐   │
│  │  /                  → React app (→ /auth)       │   │
│  │  /auth              → React app                 │   │
│  │  /dashboard         → React app                 │   │
│  │  /bookmark/*        → React app                 │   │
│  │  /settings          → React app                 │   │
│  │  /knowledge-graph   → React app                 │   │
│  │  /analytics         → React app                 │   │
│  │  /api/*             → Backend FastAPI           │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Backend:** FastAPI + MongoDB + Gemini 2.5 Flash
- **Frontend:** React 19 + Vite + Shadcn/ui + Tailwind CSS + Framer Motion
- **Extension:** Chrome/Firefox Manifest V3
- **Design:** Brutalist aesthetic with sharp corners, 2px black borders, and offset shadows

---

## Key Features

### Core Features

- **Instant Bookmarking** - Non-blocking save with background AI processing
- **AI Summaries** - Automatic one-sentence, bullet points, and long-form summaries
- **Smart Highlights** - AI-extracted key quotes from content
- **Auto-Tagging** - Intelligent tag suggestions
- **Duplicate Detection** - URL + text similarity matching with smart merging
- **Dual Views** - List and grid view modes
- **Keyboard Shortcuts** - Power user navigation
- **Reading List** - Auto-calculated reading times

### Advanced Features

- **Knowledge Graph** - Semantic AI-powered entity and relationship mapping
- **Intelligent Resurfacing** - Spaced repetition engine with context-aware suggestions
- **Learning Analytics** - Reading stats, topic analysis, and pattern detection
- **Content Intelligence** - Quality scoring and content evaluation
- **Import/Export** - Seamless migration from Pocket, Raindrop.io, and other services
- **Collections** - Organize bookmarks into custom collections
- **X Bookmarks Sync** - OAuth-based import from X bookmarks API
- **Admin Console** - User management, system health, and runtime API key configuration
- **CLI** - Save, search, list, import, and manage local stacks from the terminal

---

## Documentation

📚 Full documentation is in the `/documentation/` folder:

```
documentation/
├── api/               # API reference (60+ endpoints)
├── features/          # Feature guides (Knowledge Graph, Resurfacing, Analytics)
├── deployment/        # Production deployment and restoration
├── architecture.md    # System architecture
├── troubleshooting.md # Common operational and development fixes
└── security.md        # Security notes and recent security fixes
```

### Quick Links

- **API Docs:** `documentation/api/README.md`
- **Feature Guides:** `documentation/features/`
- **X Integration:** `documentation/features/x-api-bookmarks.md`
- **Deployment:** `documentation/deployment/DEPLOYMENT.md`
- **Environment Variables:** `documentation/deployment/ENVIRONMENT_VARIABLES.md`
- **Architecture:** `documentation/architecture.md`
- **Troubleshooting:** `documentation/troubleshooting.md`

---

## Testing

```bash
cd backend && pytest tests/ -m "not integration"
cd frontend && yarn test --run
cd frontend && yarn lint
```

---

## Deployment

See `documentation/deployment/DEPLOYMENT.md` for production deployment instructions.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution guidelines.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

**Contact:** For current questions or support, open a [GitHub issue](https://github.com/glnarayanan/arivu/issues) in the new repository.
