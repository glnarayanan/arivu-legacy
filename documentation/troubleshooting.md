# Troubleshooting

**Last reviewed:** May 10, 2026

Common fixes for running and developing Arivu.

## Docker / Self-Hosting

### Containers fail to start

```bash
docker compose ps
docker compose logs backend
docker compose logs frontend
```

Common causes:

- Missing `.env`; copy `.env.example` to `.env`.
- `SECRET_KEY` is shorter than 32 characters.
- Port `80`, `27017`, or `6379` is already in use.
- `MONGO_ROOT_PASSWORD` in `.env` changed after the MongoDB volume was initialized. Reuse the original password or recreate the volume intentionally.

### Backend cannot connect to MongoDB

Use `MONGO_URL` in `.env`.

Docker value:

```bash
MONGO_URL=mongodb://admin:changeme123@mongodb:27017/?authSource=admin
```

Manual local value:

```bash
MONGO_URL=mongodb://admin:changeme123@localhost:27017/?authSource=admin
```

Check MongoDB health:

```bash
docker compose ps mongodb
docker compose logs mongodb
```

### Frontend shows a blank page

- Check `docker compose logs frontend`.
- Hard refresh the browser.
- Verify `http://localhost/health` returns `healthy`.
- Verify API proxying with `http://localhost/api/health`.

### API calls fail in manual frontend development

The app uses relative `/api` requests. Docker nginx proxies those automatically. If running `yarn dev`, configure the Vite dev server or another local proxy so `/api` reaches `http://localhost:8001`.

## Authentication

### Login fails

- Confirm the user exists.
- If creating a new account, check `SIGNUPS_ENABLED=true`.
- Confirm cookies are accepted by the browser.
- Review account lockout state if there were repeated failed attempts.

### Account locked

Default lockout behavior is five failed attempts for 15 minutes.

```bash
docker compose logs backend
```

For local development only, you can clear lockout fields in MongoDB after confirming the account owner.

### Sessions become invalid after deployment

Changing `SECRET_KEY` invalidates all existing tokens. Users must sign in again. It also affects encrypted runtime API key overrides; re-enter keys in the admin settings UI after rotating `SECRET_KEY`.

## AI Features

### Summaries or tags are missing

- Set `GEMINI_API_KEY` in `.env`, or configure it through **Settings -> API Keys** as an admin.
- Check backend logs for Gemini quota or auth errors.
- AI processing runs in the background after bookmark creation; wait briefly and refresh.

### Knowledge graph is sparse

- Add enough bookmarks with processed text and AI summaries.
- Confirm AI processing is completing.
- Use `documentation/features/knowledge-graph.md` for expected behavior.

## X Integration

### X connection controls are hidden

Set:

```bash
X_INTEGRATION_ENABLED=true
X_CLIENT_ID=<client id>
X_CLIENT_SECRET=<client secret>
APP_URL=https://your-domain.example
```

Then restart the backend unless using admin runtime overrides.

### OAuth callback fails

- Confirm the redirect URI in X Developer Portal matches the app flow.
- Default redirect is `{APP_URL}/settings?section=connections`.
- Check backend logs around `/api/auth/x/callback`.

## Browser Extension

### Extension cannot save

- Confirm the extension server URL matches your app origin.
- Log in to the web app first.
- Check `/api/health` from the same browser.
- See `extension/README.md` for installation and configuration.

## Tests and Checks

Backend:

```bash
cd backend
pytest tests/ -m "not integration"
```

Frontend:

```bash
cd frontend
yarn lint
yarn test --run
```

Common test setup issues:

- Install dependencies first.
- Set `SECRET_KEY` and `MONGO_URL` when running backend code that loads settings.
- Integration tests may require Docker-backed services.
