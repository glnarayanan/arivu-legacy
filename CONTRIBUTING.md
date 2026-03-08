# Contributing to Arivu

Thanks for your interest in contributing! This guide will help you get started.

## Local Development Setup

### Docker (Recommended)

```bash
git clone https://github.com/glnarayanan/arivu.git
cd arivu
cp .env.example .env
docker compose up -d --build
```

Access the app at `http://localhost/auth`.

### Manual Setup

**Backend:**

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Requires MongoDB running locally or via Docker.

**Frontend:**

```bash
cd frontend
yarn install
yarn dev
```

## Architecture Notes

- **`backend/server.py` is monolithic by design.** Do not split it into separate modules.
- The frontend uses a relative `/api` path behind the nginx proxy. No explicit backend URL config is needed in production.
- The design system follows a **brutalist aesthetic**: sharp corners, 2px black borders, offset shadows. See `documentation/design/DESIGN_SYSTEM.md`.
- **Light mode only.** No dark mode.

## Making Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes following existing code patterns
4. Run tests: `cd backend && python backend_test.py`
5. Submit a pull request

## Commit Messages

Use conventional commit format:

```
type(scope): description
```

Examples:

- `feat(backend): add bookmark export endpoint`
- `fix(frontend): correct tag filter behavior`
- `docs: update deployment guide`

## Code Style

- **Python:** Follow existing patterns in `server.py`. Always filter by `user_id` in database queries. Always use field projections.
- **React/JSX:** Follow existing component patterns. Use Shadcn/ui components, Tailwind CSS, and framer-motion.
- **No new dependencies** without discussion — open an issue first if you need a new library.

## Testing

```bash
cd backend && python backend_test.py
```

## Questions?

Open a [GitHub issue](https://github.com/glnarayanan/arivu/issues) for questions or feature discussions.
