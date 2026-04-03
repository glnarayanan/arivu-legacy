# Environment Variables Guide

**Last Updated:** February 20, 2026
**Purpose:** Comprehensive guide to all Arivu environment variables

---

## Admin UI Configuration (Recommended for Self-Hosters)

API keys for **Gemini AI**, **X (Twitter)**, and **Resend Email** can be configured through the **Settings → API Keys** panel in the web UI instead of editing `.env` files. This requires an admin account (set `ADMIN_EMAILS` in `.env`).

- **DB overrides take precedence** over environment variables
- Keys are **encrypted at rest** (Fernet) in MongoDB
- Changes take effect **immediately** — no server restart required
- Removing a DB override reverts to the `.env` value

To use: set `ADMIN_EMAILS=your-email@example.com` in `.env`, then navigate to **Settings → API Keys** after logging in.

---

## Quick Setup

```bash
# Copy the example file
cp .env.example .env

# Edit with your values
nano .env  # or your preferred editor

# Required: Add your Gemini API key
GEMINI_API_KEY=your_actual_api_key_here

# Required for production: Generate a secure secret
openssl rand -hex 32  # Copy output to SECRET_KEY
```

---

## Environment Variables Reference

### MongoDB Configuration

#### `MONGO_URL` (Required)
**Purpose:** MongoDB connection string
**Format:** `mongodb://[user]:[password]@[host]:[port]/`

**Values by Environment:**
```bash
# Local development (no auth)
MONGO_URL=mongodb://localhost:27017/

# Docker Compose
MONGO_URL=mongodb://admin:changeme123@mongodb:27017/

# Production (managed MongoDB)
MONGO_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
```

**Security Notes:**
- Use authentication in production
- Never commit credentials to git
- Use connection string with SSL/TLS in production

---

#### `DB_NAME` (Required)
**Purpose:** MongoDB database name
**Default:** `arivu_db`
**Example:**
```bash
DB_NAME=arivu_db
```

**Note:** Database is created automatically if it doesn't exist

---

#### `MONGO_ROOT_USERNAME` (Docker Only)
**Purpose:** MongoDB root username for Docker container initialization
**Default:** `admin`
**Example:**
```bash
MONGO_ROOT_USERNAME=admin
```

**Note:** Only used when initializing MongoDB container, not needed for managed MongoDB

---

#### `MONGO_ROOT_PASSWORD` (Docker Only)
**Purpose:** MongoDB root password for Docker container
**Default:** `changeme123`
**Example:**
```bash
MONGO_ROOT_PASSWORD=your_secure_password_here
```

**Security:**
- Change default password immediately
- Use strong password (20+ characters)
- Store securely (password manager, secrets vault)

---

### Application Security

#### `SECRET_KEY` (Required)
**Purpose:** JWT token signing key for authentication
**Format:** Hex string (minimum 32 characters)

**Generate Secure Key:**
```bash
openssl rand -hex 32
```

**Example:**
```bash
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

**Security:**
- **NEVER** use default value in production
- Generate unique key per environment
- Never commit to version control
- Rotate periodically (invalidates all tokens)

**Impact of Changing:**
- All existing user sessions invalidated
- Users must log in again
- Refresh tokens expire

---

### CORS Configuration

#### `CORS_ORIGINS` (Required)
**Purpose:** Allowed origins for Cross-Origin Resource Sharing
**Format:** Comma-separated list or `*`

**Values by Environment:**
```bash
# Development (allow all)
CORS_ORIGINS=*

# Production (specific domains)
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Multiple environments
CORS_ORIGINS=https://your-domain.com,https://staging.your-domain.com,http://localhost:3000
```

**Security:**
- **NEVER** use `*` in production
- Include all necessary domains (www, non-www)
- Use HTTPS in production
- Don't include trailing slashes

---

### AI Configuration

#### `GEMINI_API_KEY` (Required)
**Purpose:** Google Gemini API key for AI features
**Format:** String starting with `AI`

**Get Your Key:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create project and enable Gemini API
3. Generate API key
4. Copy to `.env` file

**Example:**
```bash
GEMINI_API_KEY=<your-gemini-api-key>
```

**Features Requiring This Key:**
- Bookmark summaries (one-sentence, bullet points, long-form)
- Smart highlights extraction
- Auto-tag suggestions
- Content quality scoring
- Knowledge graph entity extraction
- Analytics insights generation

**Quota & Pricing:**
- Free tier: 60 requests/minute
- Paid tier: Higher limits
- Monitor usage in Google Cloud Console

**Security:**
- Keep key private
- Don't commit to git
- Rotate if exposed
- Monitor usage for anomalies

---

### Frontend Configuration

#### `REACT_APP_BACKEND_URL` (Required for Frontend)
**Purpose:** Backend API URL for frontend to connect to
**Format:** Full URL with protocol, no trailing slash

**Values by Environment:**
```bash
# Local development
REACT_APP_BACKEND_URL=http://localhost:8001

# Docker Compose (internal)
REACT_APP_BACKEND_URL=http://backend:8001

# Production
REACT_APP_BACKEND_URL=https://your-domain.com
```

**Note:**
- Must be accessible from browser (user's machine)
- Use HTTPS in production
- Docker internal URLs won't work from browser

---

#### `WDS_SOCKET_PORT` (Development Only)
**Purpose:** Webpack Dev Server socket port for hot reload
**Default:** `3000`
**Example:**
```bash
WDS_SOCKET_PORT=3000
```

**Note:** Only needed for local development, not used in production builds

---

### Admin & Access Control

#### `ADMIN_EMAILS` (Recommended)
**Purpose:** Comma-separated list of email addresses with admin access
**Default:** (empty — no admins)

Admins can access the API Keys configuration UI and system health panel.

```bash
ADMIN_EMAILS=admin@example.com,ops@example.com
```

---

#### `SIGNUPS_ENABLED` (Optional)
**Purpose:** Enable or disable new user registration
**Default:** `true`

```bash
# Disable public signups (invite-only mode)
SIGNUPS_ENABLED=false
```

---

### X Integration Configuration

#### `X_INTEGRATION_ENABLED` (Optional)
**Purpose:** Master feature flag for X bookmark OAuth + sync endpoints
**Default:** `false`

```bash
X_INTEGRATION_ENABLED=true
```

---

#### `X_CLIENT_ID` (Required when X integration enabled)
**Purpose:** OAuth client ID from X Developer Portal

```bash
X_CLIENT_ID=your_x_client_id
```

---

#### `X_CLIENT_SECRET` (Required when X integration enabled)
**Purpose:** OAuth client secret from X Developer Portal

```bash
X_CLIENT_SECRET=your_x_client_secret
```

---

#### `X_REDIRECT_URI` (Optional)
**Purpose:** OAuth redirect override
**Default:** `{APP_URL}/settings?section=connections`

```bash
X_REDIRECT_URI=https://your-domain.example/settings?section=connections
```

---

#### `X_MAX_BOOKMARK_PAGES` (Optional)
**Purpose:** Max X API pages fetched per sync
**Default:** `10`
**Special value:** `0` means unlimited pages

```bash
X_MAX_BOOKMARK_PAGES=10
```

---

#### `X_MAX_BOOKMARKS` (Optional)
**Purpose:** Max bookmarks imported per sync run
**Default:** `300`
**Special value:** `0` means unlimited bookmarks

```bash
X_MAX_BOOKMARKS=300
```

---

### Production with X Integration
```bash
MONGO_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
DB_NAME=arivu_production
SECRET_KEY=a1b2c3...long-secure-key...x4y5z6
CORS_ORIGINS=https://your-domain.example
GEMINI_API_KEY=AIza...your-key...
REACT_APP_BACKEND_URL=https://your-domain.example/api
X_INTEGRATION_ENABLED=true
X_CLIENT_ID=your_x_client_id
X_CLIENT_SECRET=your_x_client_secret
X_REDIRECT_URI=https://your-domain.example/settings?section=connections
X_MAX_BOOKMARK_PAGES=10
X_MAX_BOOKMARKS=300
LOG_LEVEL=info
```

**Impact:**
- `debug`: All logs (very verbose)
- `info`: Normal operations (recommended)
- `warning`: Only warnings and errors
- `error`: Only errors

---

#### `LOG_LEVEL` (Optional)
**Purpose:** Application logging verbosity
**Default:** `info`
**Values:** `debug`, `info`, `warning`, `error`

**Example:**
```bash
# Development (verbose)
LOG_LEVEL=debug

# Production (minimal)
LOG_LEVEL=warning
```

---

## Environment-Specific Configurations

### Local Development
```bash
MONGO_URL=mongodb://localhost:27017/
DB_NAME=arivu_db
SECRET_KEY=dev-secret-key-not-for-production
CORS_ORIGINS=*
GEMINI_API_KEY=AIza...your-key...
REACT_APP_BACKEND_URL=http://localhost:8001
LOG_LEVEL=debug
```

### Docker Compose
```bash
MONGO_URL=mongodb://admin:changeme123@mongodb:27017/
DB_NAME=arivu_db
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=changeme123
SECRET_KEY=docker-secret-key-change-me
CORS_ORIGINS=http://localhost:80,http://localhost:3000
GEMINI_API_KEY=AIza...your-key...
REACT_APP_BACKEND_URL=http://localhost:8001
LOG_LEVEL=info
```

### Production
```bash
MONGO_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
DB_NAME=arivu_production
SECRET_KEY=a1b2c3...long-secure-key...x4y5z6
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
GEMINI_API_KEY=AIza...your-key...
REACT_APP_BACKEND_URL=https://your-domain.com
LOG_LEVEL=warning
```

---

## Security Best Practices

### 1. Never Commit Secrets
```bash
# Add to .gitignore (already done)
.env
.env.local
.env.production
*.env
```

### 2. Use Strong Passwords
- MongoDB password: 20+ characters, random
- SECRET_KEY: 64+ characters, hex generated
- Change all defaults immediately

### 3. Restrict CORS in Production
```bash
# BAD (allows any origin)
CORS_ORIGINS=*

# GOOD (specific domains)
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### 4. Use HTTPS in Production
- All URLs should use `https://`
- Enable SSL/TLS for MongoDB connections
- Use secure cookies (handled by backend)

### 5. Rotate Keys Periodically
- SECRET_KEY: Every 90 days
- GEMINI_API_KEY: If exposed or annually
- MongoDB password: Every 6 months

### 6. Monitor API Usage
- Track Gemini API usage
- Set billing alerts
- Monitor for unusual patterns

---

## Troubleshooting

### "Cannot connect to MongoDB"
**Check:**
```bash
# Verify MONGO_URL is correct
echo $MONGO_URL

# Test MongoDB connection
mongosh "$MONGO_URL"

# Check if MongoDB is running
docker ps | grep mongo
```

### "Invalid JWT token"
**Causes:**
- SECRET_KEY changed (invalidates all tokens)
- Token expired (60 min for access token)
- Clock skew between servers

**Fix:**
- Use same SECRET_KEY across all instances
- Log out and log back in
- Sync server clocks with NTP

### "CORS error in browser"
**Symptoms:** Frontend can't connect to backend
**Check:**
```bash
# Verify CORS_ORIGINS includes frontend domain
echo $CORS_ORIGINS

# Check browser console for exact error
# Should see allowed origins list
```

**Fix:**
```bash
# Add frontend domain to CORS_ORIGINS
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### "Gemini API quota exceeded"
**Symptoms:** Summaries fail, "Quota exceeded" errors

**Check Quota:**
1. Visit Google Cloud Console
2. Navigate to Gemini API
3. Check usage metrics

**Solutions:**
- Wait for quota reset (next minute/day)
- Upgrade to paid tier
- Implement rate limiting in code

---

## Migration Guide

### Updating Environment Variables
```bash
# 1. Backup current .env
cp .env .env.backup

# 2. Check new variables in .env.example
diff .env .env.example

# 3. Add any new variables
nano .env

# 4. Restart application
docker-compose restart  # or pm2 restart all
```

### Rotating SECRET_KEY
```bash
# 1. Generate new key
NEW_KEY=$(openssl rand -hex 32)

# 2. Update .env
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$NEW_KEY/" .env

# 3. Restart application
docker-compose restart backend

# 4. Notify users (all sessions invalidated)
```

---

## Environment Variable Checklist

Before deploying to production:

- [ ] Changed default `SECRET_KEY`
- [ ] Changed default `MONGO_ROOT_PASSWORD`
- [ ] Set production `MONGO_URL`
- [ ] Restricted `CORS_ORIGINS` to actual domains
- [ ] Set production `REACT_APP_BACKEND_URL`
- [ ] Added valid `GEMINI_API_KEY`
- [ ] Set `LOG_LEVEL=warning` or `error`
- [ ] All URLs use HTTPS
- [ ] `.env` added to `.gitignore`
- [ ] Secrets stored in password manager
- [ ] Tested all environment configurations

---

## Related Documentation

- **Deployment Guide:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Security Best Practices:** [../development/SECURITY_IMPROVEMENTS.md](../development/SECURITY_IMPROVEMENTS.md)
- **Backup & Restoration:** [RESTORATION.md](RESTORATION.md)

---

**Last Updated:** February 20, 2026
**Version:** 1.1
**Status:** Production Ready
