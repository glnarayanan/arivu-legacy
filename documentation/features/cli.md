# CLI

**Status:** ✅ Implemented  
**Implemented:** March 21, 2026  
**Runtime:** Python CLI bundled with the backend  
**Primary command:** `arivu`

---

## Overview

The Arivu CLI gives users a terminal-first way to save links and query their second brain without relying on the browser UI. It is a thin client over the existing Arivu API, so bookmark ingestion, AI processing, hybrid search, resurfacing, and knowledge graph behavior stay aligned with the main application.

The CLI also includes Docker-based local orchestration commands so a user can run a full local Arivu stack and use the CLI against `http://localhost/api` instead of deploying the product online.

---

## Command Surface

### Profiles and Auth

```bash
arivu profile add local --url http://localhost
arivu profile use local
arivu auth login --profile local
arivu auth whoami
arivu auth logout
```

### Save and Read

```bash
arivu save https://example.com/article
arivu save https://example.com/article --collection Inbox
arivu search "python embeddings"
arivu show <bookmark-id>
arivu open <bookmark-id>
```

### Power-User Commands

```bash
arivu collections list
arivu collections create Research
arivu collections add Research <bookmark-id>

arivu resurface list
arivu resurface snooze <bookmark-id> --days 14
arivu resurface archive <bookmark-id>

arivu graph search "memory systems"
arivu graph overview
```

---

## Local Stack Commands

```bash
arivu local up
arivu local status
arivu local logs backend
arivu local down
```

Behavior:
- Uses the repo `docker-compose.yml`
- Validates the root `.env` before startup
- Creates or updates a `local` profile pointing at `http://localhost/api`
- Boots the full frontend + backend + MongoDB + Redis stack

---

## Install Notes

From the `backend/` directory:

```bash
pip install -r requirements.txt
pip install -e .
```

You can also run the CLI without installing the console entrypoint:

```bash
python -m app.cli --help
```

---

## Auth Model

- Browser and frontend auth remain cookie-based
- CLI auth is bearer-token based and separate from the browser session
- Tokens are stored in the user config directory with restrictive file permissions
- Logout removes stored CLI credentials locally; v1 does not implement server-side token revocation
