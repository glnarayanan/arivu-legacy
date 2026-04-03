# Arivu - AI-Native Bookmarking Application

**Status:** Production Ready ✅  
**License:** MIT

> Transform saved web pages into instantly useful knowledge with AI-powered summaries, highlights, and smart organization.

---

## Quick Start

```bash
git clone https://github.com/glnarayanan/arivu.git
cd arivu
cp .env.example .env  # Add GEMINI_API_KEY and SECRET_KEY
docker-compose up -d --build

# Access: http://localhost/auth
```

This runs four containers: frontend (port 80), backend, MongoDB, and Redis.

### Manual Development

**Prerequisites:** Python 3.9+, Node.js 18+, MongoDB, Gemini API Key

```bash
# Backend (Terminal 1)
cd backend
pip install -r requirements.txt
cp .env.example .env  # Add MONGO_URL and GEMINI_API_KEY
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend (Terminal 2)
cd frontend
yarn install
yarn start
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
✅ **Instant Bookmarking** - Non-blocking save with background AI processing
✅ **AI Summaries** - Automatic one-sentence, bullet points, and long-form summaries
✅ **Smart Highlights** - AI-extracted key quotes from content
✅ **Auto-Tagging** - Intelligent tag suggestions
✅ **Duplicate Detection** - URL + text similarity matching with smart merging
✅ **Dual Views** - List and grid view modes
✅ **Keyboard Shortcuts** - Power user navigation
✅ **Reading List** - Auto-calculated reading times

### Advanced Features
✅ **Knowledge Graph** - Semantic AI-powered entity and relationship mapping
✅ **Intelligent Resurfacing** - Spaced repetition engine with context-aware suggestions
✅ **Learning Analytics** - Reading stats, topic analysis, and pattern detection
✅ **Content Intelligence** - Quality scoring and content evaluation
✅ **Import/Export** - Seamless migration from Pocket, Raindrop.io, and other services
✅ **Collections** - Organize bookmarks into custom collections  
✅ **X Bookmarks Sync** - OAuth-based import from X bookmarks API

---

## Documentation

📚 Full documentation is in the `/documentation/` folder:

```
documentation/
├── api/               # API reference (35+ endpoints)
├── features/          # Feature guides (Knowledge Graph, Resurfacing, Analytics)
├── deployment/        # Production deployment and restoration
├── development/       # Security patterns and architecture
├── design/            # Brutalist design system
├── roadmap/           # Roadmap and planning
└── archive/           # Historical docs and verbose guides
```

📖 **User-facing docs** are also available at [arivu.app/documentation](https://arivu.app/documentation/)

### Quick Links
- **API Docs:** `documentation/api/README.md`
- **Feature Guides:** `documentation/features/`
- **X Integration:** `documentation/features/x-api-bookmarks.md`
- **Deployment:** `documentation/deployment/DEPLOYMENT.md`
- **Environment Variables:** `documentation/deployment/ENVIRONMENT_VARIABLES.md`

---

## Testing

```bash
cd backend
python backend_test.py
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

**Contact:** For questions or support, open a [GitHub issue](https://github.com/glnarayanan/arivu/issues).
