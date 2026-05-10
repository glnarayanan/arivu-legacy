# CLI

**Status:** ✅ Implemented  
**Implemented:** March 21, 2026  
**Runtime:** Python CLI bundled with the backend  
**Primary command:** `arivu`

---

## Overview

The Arivu CLI gives users a terminal-first way to save links and query their second brain without relying on the browser UI. It is a thin client over the existing Arivu API, so bookmark ingestion, AI processing, hybrid search, resurfacing, and knowledge graph behavior stay aligned with the main application.

The CLI also includes Docker-based local orchestration commands so a user can run a full local Arivu stack and use the CLI against `http://localhost/api` instead of deploying the product online.

The CLI preview command now fetches URL metadata through the authenticated API (`POST /api/bookmarks/preview`) instead of making unauthenticated local HTTP requests from the terminal. That keeps redirect handling, size limits, and SSRF protections shared with normal bookmark ingestion.

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
# Save a single bookmark
arivu save https://example.com/article
arivu save https://example.com/article --collection Inbox

# Save multiple bookmarks at once
arivu save https://example.com/article1 https://example.com/article2 --collection Research

# List bookmarks with filters
arivu list
arivu list --unread
arivu list --collection Research
arivu list --since 2026-01-01
arivu list --limit 50

# Search bookmarks
arivu search "python embeddings"
arivu search "memory systems" --limit 20

# Show bookmark details
arivu show <bookmark-id>

# Open bookmark in browser
arivu open <bookmark-id>

# Delete a bookmark
arivu delete <bookmark-id>
arivu delete <bookmark-id> --force  # Skip confirmation
```

### Import Bookmarks

```bash
# Import from Pocket HTML export
arivu import pocket pocket_export.html

# Import from Raindrop.io JSON export
arivu import raindrop raindrop_export.json
```

### Analytics and Preview

```bash
# Show reading statistics
arivu stats
arivu stats --weekly
arivu stats --monthly

# Preview a URL before saving
arivu preview https://example.com/article
arivu preview https://example.com/article --collection Inbox
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

### Interactive Mode

Start an interactive REPL session for a more conversational experience:

```bash
arivu interactive
```

Supported commands in interactive mode:
- `save <url> [--collection NAME]` - Save a bookmark
- `search <query> [--limit N]` - Search bookmarks; quote multi-word queries, for example `search "python embeddings"`
- `list [--unread] [--limit N]` - List bookmarks
- `show <bookmark-id>` - Show bookmark details
- `open <bookmark-id>` - Open bookmark in browser
- `delete <bookmark-id> [--force]` - Delete a bookmark
- `stats [--weekly|--monthly]` - Show analytics
- `help` - Show available commands
- `quit` - Exit interactive mode

---

## Local Stack Commands

Run local stack commands from inside an Arivu repo checkout. The checkout must include the root `docker-compose.yml`, and the root `.env` must exist before `arivu local up` runs.

```bash
arivu local up
arivu local status
arivu local logs backend
arivu local down
```

Behavior:
- Discovers and uses the repo root `docker-compose.yml`
- Validates the root `.env` before startup and requires a real 32+ character `SECRET_KEY`
- Creates or updates a `local` profile pointing at `http://localhost/api`
- Boots the full frontend + backend + MongoDB + Redis stack

---

## Install Notes

The backend and CLI require Python 3.11 or newer.

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

## Shell Completion

The CLI supports shell completion for bash, zsh, and fish:

```bash
# Install completion for your current shell
arivu --install-completion

# Show completion script to customize installation
arivu --show-completion
```

After installing completion, restart your shell or source your shell config file:

```bash
# bash
source ~/.bashrc

# zsh
source ~/.zshrc

# fish
source ~/.config/fish/config.fish
```

---

## Auth Model

- Browser and frontend auth remain cookie-based
- CLI auth is bearer-token based and separate from the browser session
- `arivu auth login` authenticates an existing Arivu user; create the account in the web app first because the CLI does not provide a signup command
- Tokens are stored in the user config directory with restrictive file permissions
- Logout removes stored CLI credentials locally; v1 does not implement server-side token revocation

## Security Notes

- URL preview and bookmark ingestion reject embedded credentials, private IPs, loopback, link-local, multicast, reserved, and unresolved unsafe hosts.
- Server-side fetches revalidate the URL before each redirect hop and do not rely on client-side preview filtering.
- Import parsing skips unsafe URLs before creating placeholder bookmarks.

---

## Environment Variables

The CLI respects these environment variables:

- `ARIVU_PROFILE` - Default profile to use
- `ARIVU_CONFIG_DIR` - Custom config directory path

---

## Tips and Tricks

### Quick Save with Clipboard

```bash
# macOS
arivu save $(pbpaste)

# Linux
arivu save $(xclip -o)
```

### Pipe URLs from File

```bash
cat bookmarks.txt | xargs -n1 arivu save
```

### Search and Open First Result

```bash
arivu search "python" --json | jq -r '.[0].id' | xargs arivu open
```
