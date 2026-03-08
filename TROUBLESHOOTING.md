# Troubleshooting

Common issues and solutions when running Arivu.

## Docker / Self-Hosting

### Container fails to start

**Symptom:** `docker-compose up` exits with errors.

**Check logs:**
```bash
docker-compose logs backend
docker-compose logs frontend
```

**Common causes:**
- Missing `.env` file — copy `.env.example` to `.env` and fill in required values
- Port conflicts — ensure ports 80, 8001, 27017, 6379 are available
- `SECRET_KEY` too short — must be at least 32 characters

### MongoDB connection refused

**Symptom:** Backend logs show `ServerSelectionTimeoutError`.

**Solutions:**
- Verify MongoDB container is running: `docker-compose ps`
- Check `MONGODB_URL` in `.env` matches the service name (use `mongodb://mongodb:27017` in Docker, `mongodb://localhost:27017` for local dev)
- If using authentication, ensure `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD` are set

### Frontend shows blank page

**Symptom:** Browser shows white screen at `http://localhost`.

**Solutions:**
- Check browser console for errors (F12 → Console)
- Verify the frontend container built successfully: `docker-compose logs frontend`
- Clear browser cache and hard refresh (Ctrl+Shift+R)
- Check nginx config is proxying `/api/*` correctly to the backend

### CORS errors in browser console

**Symptom:** `Access-Control-Allow-Origin` errors in console.

**Solutions:**
- Ensure `CORS_ORIGINS` in `.env` includes your frontend URL
- In Docker, the frontend nginx proxies API requests — CORS headers are set by the backend
- For local dev, the Vite dev server proxies `/api` to port 8001

## Authentication

### Login fails with "Invalid credentials"

- Verify the user exists in MongoDB: check the `users` collection
- Password is hashed with bcrypt — you cannot compare directly
- If using signup toggle, ensure `SIGNUPS_ENABLED=true` to allow new accounts

### Session expires too quickly

- Default access token lifetime is 60 minutes, refresh token is 30 days
- Check that cookies are being set: browser DevTools → Application → Cookies
- Verify `proxy_cookie_path` and `proxy_cookie_domain` in nginx config

### "Account locked" error

- Accounts lock after 5 failed login attempts within 15 minutes
- Wait for the lockout period to expire, or clear the lockout in MongoDB:
```bash
# In mongo shell
db.users.updateOne({email: "user@example.com"}, {$set: {failed_login_attempts: 0, locked_until: null}})
```

## AI Features

### Bookmarks show "Summary unavailable"

- Verify `GEMINI_API_KEY` is set and valid
- Check backend logs for Gemini API errors
- AI processing runs as a background task — wait a few seconds after saving
- Rate limits: Gemini free tier has request limits per minute

### Knowledge Graph is empty

- The graph requires at least 5-10 bookmarks with AI summaries
- Verify AI summaries are being generated (check `ai_summaries` collection)
- Try refreshing the page — graph data is fetched on page load

## Browser Extension

### Extension can't connect to server

- Verify the server URL in extension settings matches your deployment
- For self-hosted: use your public URL (not `localhost` unless testing locally)
- Check that the backend is accessible from your browser (visit `/api/health`)

### Extension popup shows "Not logged in"

- Log in to the web app first — the extension shares authentication
- For cookie-based auth, ensure the extension's configured URL matches the cookie domain

## Performance

### Slow bookmark loading

- Check MongoDB indexes exist: the backend creates them on startup
- Use pagination — avoid loading all bookmarks at once
- Check if Redis is running (used for caching): `docker-compose logs redis`

### High memory usage

- MongoDB: set `wiredTigerCacheSizeGB` in mongod config for memory-constrained environments
- Backend: Uvicorn workers default to 1 — increase for production with `--workers 4`
- Frontend: the built React app is static — memory usage should be minimal

## Development

### Backend tests fail

```bash
cd backend
pytest tests/ -m "not integration" -v
```

- Ensure you're in the `backend/` directory
- Install test dependencies: `pip install -r requirements.txt`
- Pin `pytest-asyncio<1.0` — version 1.x has breaking changes
- Set required env vars: `SECRET_KEY`, `MONGODB_URL`

### Frontend tests fail

```bash
cd frontend
yarn test --run
```

- Install dependencies first: `yarn install`
- Tests use `jsdom` environment — check `vite.config.js` for test config
- Mock issues: ensure `framer-motion` and `axios` mocks are in place

### Linting errors

```bash
# Backend
cd backend && black . && ruff check . --fix

# Frontend
cd frontend && yarn eslint src/ --fix
```
