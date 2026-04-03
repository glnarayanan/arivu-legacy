# Arivu Deployment Guide
## Complete Setup for Local Development & Production

**Version:** 2.2 (Updated with Marketing Site Integration)
**Last Updated:** February 19, 2026
**Platforms:** Local (Docker), VPS (Production), Cloudflare (CDN)

---

## Open-Source / Self-Hosted Quick Links

- Public docs hub: `/documentation/` (marketing site route)
- Self-hosting guide: `marketing/content/documentation/self-hosting-arivu.md`
- Extension self-hosting guide: `marketing/content/documentation/extension-self-hosted-setup.md`
- X API setup guide: `marketing/content/documentation/x-bookmarks-api-setup.md`

---

## Table of Contents

1. [Overview](#overview)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment (VPS)](#production-deployment-vps)
4. [Cloudflare Configuration](#cloudflare-configuration)
5. [Environment Variables Reference](#environment-variables-reference)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Security Hardening](#security-hardening)

---

## Overview

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Internet (HTTPS)                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
              Cloudflare Edge
              (SSL Termination)
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Production VPS                         │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │           nginx (Ports 80, 443)                 │   │
│  │                                                  │   │
│  └──────────────────┬──────────────────────────────┘   │
│                     │                                   │
│  ┌──────────────────▼──────────────────────────────┐   │
│  │         Docker Network (arivu-network)          │   │
│  │                                                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐     │   │
│  │  │Marketing │  │ Frontend │  │ Backend  │     │   │
│  │  │nginx:80  │  │ nginx:80 │  │  :8001   │     │   │
│  │  └────┬─────┘  └──────────┘  └──────────┘     │   │
│  │       │                                         │   │
│  │       │ Routes:                                 │   │
│  │       │  /           → Hugo static (landing)   │   │
│  │       │  /auth       → Frontend React app      │   │
│  │       │  /dashboard  → Frontend React app      │   │
│  │       │  /bookmark/* → Frontend React app      │   │
│  │       │  /api/*      → Backend FastAPI         │   │
│  │       │                                         │   │
│  │  ┌──────────┐                                   │   │
│  │  │ MongoDB  │                                   │   │
│  │  │ :27017   │                                   │   │
│  │  └──────────┘                                   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Deployment Options

| Environment | Entry Point | Frontend | Backend | MongoDB | Use Case |
|-------------|-------------|----------|---------|---------|----------|
| **Local (Docker)** | Marketing:80 | Container | Container | Container | Full local testing |
| **Local (Manual)** | Frontend:3000 | 3000 | 8001 | Local/Cloud | Development |
| **Production** | Marketing:80 | Internal | Internal | Container | Live deployment |

### Key Features
- ✅ **Single-domain architecture** - Marketing + App on same domain
- ✅ **Hugo landing page** - Fast static marketing site
- ✅ **Seamless auth flow** - /auth proxied to React app
- ✅ **Fully containerized** - All services in Docker
- ✅ **Self-contained** - No external dependencies
- ✅ **Auto-scaling ready** - Resource limits configured
- ✅ **Health checks** - All services monitored
- ✅ **SSL/TLS** - Cloudflare handles certificates

---

## Local Development Setup

### Option 1: Docker Compose (Recommended)

**Prerequisites:**
- Docker Desktop installed and running
- 8GB+ RAM available
- Ports 80, 8001, 27017 available

**Quick Start:**

```bash
# 1. Clone repository
git clone https://github.com/glnarayanan/arivu.git
cd arivu

# 2. Create environment file
cp .env.example .env

# 3. Update .env with your Gemini API key
# Get key from: https://makersuite.google.com/app/apikey
nano .env  # or use your preferred editor

# Required in .env:
# GEMINI_API_KEY=AIzaSy_YOUR_KEY_HERE
# SECRET_KEY=<generate with: openssl rand -hex 32>

# 4. Start all services (marketing + frontend + backend + mongodb)
docker-compose up -d

# 5. Check container status
docker-compose ps

# Expected output:
# arivu-mongodb    Up (healthy)
# arivu-backend    Up (healthy)
# arivu-frontend   Up (healthy)
# arivu-marketing  Up (healthy)

# 6. View logs
docker-compose logs -f

# 7. Access application
# Landing page: http://localhost (Hugo marketing site)
# Auth page: http://localhost/auth (React app)
# Dashboard: http://localhost/dashboard (React app)
# Backend API: http://localhost/api (proxied through marketing nginx)
# API Docs: http://localhost:8001/docs (direct backend access)
```

**Environment Variables for Local Docker:**

Create `.env` file in project root:

```bash
# MongoDB (Docker internal networking)
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=changeme123
DB_NAME=arivu_db

# Backend
SECRET_KEY=<generate with: openssl rand -hex 32>
CORS_ORIGINS=*
GEMINI_API_KEY=AIzaSy_YOUR_KEY_HERE

# Frontend (localhost for browser access)
REACT_APP_BACKEND_URL=http://localhost:8001

# Optional
LOG_LEVEL=debug
```

**Common Commands:**

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart a specific service
docker-compose restart backend

# View logs for specific service
docker-compose logs -f backend

# Rebuild after code changes
docker-compose build --no-cache
docker-compose up -d

# Clean everything (including volumes)
docker-compose down -v
docker system prune -a --volumes
```

---

### Option 2: Manual Setup (Without Docker)

**Use Case:** When Docker is not available or for faster development iteration

**Prerequisites:**
- Python 3.11+
- Node.js 18+ and Yarn
- MongoDB 7.0+ (local or cloud)

**Step-by-Step Setup:**

**Terminal 1 - MongoDB:**

```bash
# Option A: Local MongoDB
sudo systemctl start mongodb
sudo systemctl status mongodb

# Option B: Docker MongoDB only
docker run -d -p 27017:27017 --name arivu-mongo \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=changeme123 \
  mongo:7.0

# Option C: MongoDB Atlas (cloud)
# Get connection string from https://www.mongodb.com/cloud/atlas
# Update .env: MONGO_URL=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/
```

**Terminal 2 - Backend:**

```bash
cd backend

# First time setup
pip install -r requirements.txt

# Create .env file
cat > .env << 'EOF'
MONGO_URL=mongodb://admin:changeme123@localhost:27017/
DB_NAME=arivu_db
SECRET_KEY=<generate with: openssl rand -hex 32>
GEMINI_API_KEY=AIzaSy_YOUR_KEY_HERE
CORS_ORIGINS=*
LOG_LEVEL=debug
EOF

# Start backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Expected output:
# INFO: Uvicorn running on http://0.0.0.0:8001
# INFO: Application startup complete
```

**Terminal 3 - Frontend:**

```bash
cd frontend

# First time setup
yarn install

# Create .env file
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env

# Start frontend
yarn start

# Expected output:
# Compiled successfully!
# Local: http://localhost:3000
```

**Access Points:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8001/api
- API Docs: http://localhost:8001/docs

**Testing the Setup:**

```bash
# Test backend health
curl http://localhost:8001/api/health

# Expected: {"status":"healthy","timestamp":"..."}

# Test frontend (open in browser)
open http://localhost:3000  # macOS
start http://localhost:3000  # Windows
xdg-open http://localhost:3000  # Linux
```

---

## Production Deployment (VPS)

### Prerequisites

- ✅ VPS with 4GB+ RAM, 2+ CPU cores
- ✅ Docker and Docker Compose installed on VPS
- ✅ Domain name (optional but recommended)
- ✅ Gemini API Key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### Step 1: Prepare Repository

```bash
# Ensure all changes are committed
git add .
git commit -m "Prepare for deployment"
git push origin main

# Verify these files exist:
ls docker-compose.prod.yml  # Production config
ls backend/Dockerfile       # Backend image
ls frontend/Dockerfile      # Frontend image
ls frontend/nginx.conf      # Nginx proxy config
```

### Step 2: Set Up Application on VPS

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Clone the repository
git clone https://github.com/glnarayanan/arivu.git
cd arivu

# Copy the example environment file
cp .env.example .env

# Edit with your production values (see Step 3 below)
nano .env
```

### Step 3: Configure Environment Variables

Add the following to your `.env` file on the server:

```bash
# ===================================
# MongoDB Configuration
# ===================================
# CRITICAL: Change these passwords!
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=<generate-secure-password>

# Database name
DB_NAME=arivu_db

# MongoDB connection URL (backend uses this)
# Format: mongodb://username:password@mongodb:27017/database_name?authSource=admin
# NOTE: Use "mongodb" as hostname (Docker service name)
MONGO_URL=mongodb://admin:<your-password>@mongodb:27017/arivu_db?authSource=admin

# ===================================
# Application Security
# ===================================
# Generate with: openssl rand -hex 32
SECRET_KEY=<generate-32-char-hex-key>

# ===================================
# CORS Configuration
# ===================================
# IMPORTANT: Set to your actual domain for security
# Development: * (allow all - NOT recommended for production)
# Production: https://your-domain.com (your domain)
CORS_ORIGINS=https://your-domain.com

# ===================================
# AI Configuration
# ===================================
# Get from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=AIzaSy_YOUR_GEMINI_API_KEY_HERE

# ===================================
# Frontend Configuration
# ===================================
# CRITICAL: Must match your frontend domain (nginx proxies /api to backend)
# Example: https://your-domain.com
REACT_APP_BACKEND_URL=https://your-domain.com

# ===================================
# Optional Configuration
# ===================================
LOG_LEVEL=info
```

**Important Notes:**
- Replace ALL `<placeholder>` values with actual values
- `REACT_APP_BACKEND_URL` must be set BEFORE build (it's baked into the React bundle)
- Use the same domain for both `CORS_ORIGINS` and `REACT_APP_BACKEND_URL`

**Generate Secure Values:**

```bash
# Generate SECRET_KEY (32 bytes)
openssl rand -hex 32

# Generate MongoDB password (24 bytes, base64)
openssl rand -base64 24

# Example output:
# SECRET_KEY: 3c4f5e6d7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d
# MONGO_ROOT_PASSWORD: K8mN3pQ7rT9vW2xY5zA8bC1dE4fG6hI0
```

### Step 4: Configure Domain & Networking

**Port Configuration:**
- Frontend nginx listens on port 80
- Backend on port 8001 (internal only)
- MongoDB on port 27017 (internal only)
- Only the marketing/frontend container needs to be publicly accessible

**Firewall:**
```bash
# Open HTTP/HTTPS ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block MongoDB from public access
sudo ufw deny 27017/tcp
```

**Optional: Set up a host-level nginx reverse proxy** if you need SSL termination on the server (instead of Cloudflare Flexible mode):

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

For SSL with Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Step 5: Deploy

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d --build

# Monitor build progress
docker-compose -f docker-compose.prod.yml logs -f
```

**Verify Deployment:**

```bash
# Check container status
docker ps --format "table {{.Names}}\t{{.Status}}"

# Expected output:
# NAME              STATUS
# arivu-frontend    Up (healthy)
# arivu-backend     Up (healthy)
# arivu-mongodb     Up (healthy)
```

### Step 6: Update Deployments

To deploy updates from the repository:

```bash
cd arivu
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## Cloudflare Configuration

### DNS Setup

1. **Add A Record:**
   - Type: `A`
   - Name: `app` (for your-domain.com) or `@` (for your-domain.com)
   - Content: Your VPS IP address
   - Proxy status: **Proxied** (orange cloud icon ☁️)
   - TTL: Auto

2. **Verify DNS Propagation:**
```bash
# Check DNS resolution
dig your-domain.com

# Or use online tool:
# https://dnschecker.org
```

### SSL/TLS Configuration

1. **Navigate to:** SSL/TLS Settings in Cloudflare
2. **Encryption Mode:** Set to **Flexible**
   - **Flexible:** Cloudflare → Server = HTTP (recommended for this setup)
   - **Full:** Requires SSL on server (needs Let's Encrypt on server)
   - **Full (Strict):** Requires valid certificate on server

3. **Recommended: Use Flexible Mode**
   - Simpler setup (no server-side SSL needed)
   - Cloudflare handles all SSL/TLS
   - Traffic from Cloudflare to server is HTTP

### Edge Certificates

1. **Navigate to:** SSL/TLS → Edge Certificates
2. **Enable These Settings:**
   - ✅ **Always Use HTTPS:** ON (redirects HTTP to HTTPS)
   - ✅ **Automatic HTTPS Rewrites:** ON
   - ✅ **Opportunistic Encryption:** ON
   - ✅ **TLS 1.3:** ON

### Page Rules (Optional but Recommended)

1. **Create Rule for API Caching:**
   - URL: `your-domain.com/api/*`
   - Setting: **Cache Level** → Bypass
   - Reason: API responses should not be cached

2. **Create Rule for Static Assets:**
   - URL: `your-domain.com/static/*`
   - Setting: **Cache Level** → Standard
   - Reason: Cache JS/CSS files for faster load times

### Architecture with Cloudflare

```
User Browser
    ↓ (HTTPS - TLS 1.3)
Cloudflare Edge Network
(SSL Termination, DDoS Protection, CDN)
    ↓ (HTTP - Flexible SSL mode)
Your VPS
    ↓
Docker: arivu-frontend (Port 80)
    ↓ (proxies /api/* to backend:8001)
Docker: arivu-backend (Port 8001)
    ↓
Docker: arivu-mongodb (Port 27017)
```

### Cloudflare Security Settings

1. **Firewall Rules:**
   - Consider rate limiting for API endpoints
   - Example: Max 100 requests/minute per IP for /api/*

2. **Bot Fight Mode:**
   - Enable for basic bot protection
   - Or use Cloudflare Bot Management (paid)

3. **WAF (Web Application Firewall):**
   - Enable OWASP ModSecurity Core Rule Set
   - Monitor for SQL injection, XSS attempts

---

## Environment Variables Reference

### Complete Variable List

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| **MONGO_URL** | ✅ Yes | - | MongoDB connection string | `mongodb://admin:pass@mongodb:27017/arivu_db?authSource=admin` |
| **DB_NAME** | ✅ Yes | `arivu_db` | Database name | `arivu_db` |
| **MONGO_ROOT_USERNAME** | ✅ Yes | `admin` | MongoDB root user | `admin` |
| **MONGO_ROOT_PASSWORD** | ✅ Yes | - | MongoDB root password | `<secure-password>` |
| **SECRET_KEY** | ✅ Yes | - | JWT signing key (32+ chars) | `<32-hex-chars>` |
| **GEMINI_API_KEY** | ✅ Yes | - | Google AI API key | `AIzaSy...` |
| **REACT_APP_BACKEND_URL** | ✅ Yes | - | Frontend → Backend URL | `https://your-domain.com` |
| **CORS_ORIGINS** | ✅ Yes | `*` | Allowed CORS origins | `https://your-domain.com` |
| **LOG_LEVEL** | ❌ No | `info` | Logging verbosity | `debug`, `info`, `warning`, `error` |

### Environment-Specific Configurations

**Local Development:**
```bash
MONGO_URL=mongodb://admin:changeme123@localhost:27017/
REACT_APP_BACKEND_URL=http://localhost:8001
CORS_ORIGINS=*
LOG_LEVEL=debug
```

**Local Docker:**
```bash
MONGO_URL=mongodb://admin:changeme123@mongodb:27017/
REACT_APP_BACKEND_URL=http://localhost:8001
CORS_ORIGINS=*
LOG_LEVEL=debug
```

**Production:**
```bash
MONGO_URL=mongodb://admin:<secure-pass>@mongodb:27017/arivu_db?authSource=admin
REACT_APP_BACKEND_URL=https://your-domain.com
CORS_ORIGINS=https://your-domain.com
LOG_LEVEL=info
```

### Important Notes

1. **REACT_APP_BACKEND_URL:**
   - Must be set BEFORE build time (baked into React bundle)
   - Cannot be changed at runtime
   - Must match your actual domain
   - No trailing slash

2. **MONGO_URL Format:**
   - Local: Use `localhost` as hostname
   - Docker: Use `mongodb` as hostname (service name)
   - Must include `?authSource=admin` for authentication
   - Password must match `MONGO_ROOT_PASSWORD`

3. **CORS_ORIGINS:**
   - Development: `*` (allow all - convenient but less secure)
   - Production: Specific domain (e.g., `https://your-domain.com`)
   - Multiple domains: Comma-separated (e.g., `https://your-domain.com,https://www.your-domain.com`)

---

## Post-Deployment Verification

### Step 1: Health Checks

**Backend Health:**
```bash
# Test via curl
curl https://your-domain.com/api/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-12-29T10:30:00Z",
  "database": "connected",
  "ai_service": "available"
}

# Or via browser:
https://your-domain.com/api/health
```

**Frontend Health:**
```bash
# Test nginx health endpoint
curl https://your-domain.com/health

# Expected response:
healthy

# Test React app loads
curl https://your-domain.com

# Should return HTML with React root div
```

### Step 2: Functional Testing

**Create Test Account:**
1. Open https://your-domain.com
2. Click "Sign Up"
3. Enter email and password
4. Verify successful account creation
5. Should redirect to dashboard

**Create Test Bookmark:**
1. Click "Add Bookmark" (or press Q key)
2. Enter URL: `https://paulgraham.com/greatwork.html`
3. Bookmark should save immediately (placeholder)
4. AI summary should appear within 10-20 seconds
5. Verify all AI fields populated:
   - One-sentence summary
   - Bullet points
   - Long-form summary
   - Highlights
   - Suggested tags

**Test Search & Filters:**
1. Create 2-3 bookmarks
2. Test search functionality
3. Test filters (read/unread, collections)
4. Test sorting (date, reading time)

### Step 3: Performance Verification

**Response Time Testing:**
```bash
# Test API response time
curl -w "\nTime: %{time_total}s\n" https://your-domain.com/api/health

# Expected: < 200ms for health check
# Expected: < 1s for bookmark creation
# Expected: 5-15s for AI summary generation
```

**Load Testing (Optional):**
```bash
# Using Apache Bench
ab -n 100 -c 10 https://your-domain.com/api/health

# Expected:
# - 100% success rate
# - < 500ms average response time
# - No timeout errors
```

### Step 4: Log Verification

**Check Container Logs:**
```bash
# Via SSH to server:
docker logs arivu-backend --tail 50
docker logs arivu-frontend --tail 50
docker logs arivu-mongodb --tail 50
```

**Healthy Backend Logs:**
```
INFO: Started server process [1]
INFO: Waiting for application startup
INFO: Application startup complete
INFO: Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO: 172.20.0.5:xxxxx - "GET /api/health HTTP/1.1" 200 OK
```

**Healthy Frontend Logs:**
```
/docker-entrypoint.sh: Configuration complete; ready for start up
```

**Common Warning Logs (Safe to Ignore):**
```
WARNING: Gemini API quota approaching limit (safe if < 80%)
INFO: Background task completed for bookmark_id=...
```

### Step 5: Database Verification

**Connect to MongoDB:**
```bash
# Via Docker exec
docker exec -it arivu-mongodb mongosh \
  -u admin \
  -p <your-password> \
  --authenticationDatabase admin

# Expected prompt:
test>
```

**Verify Collections:**
```javascript
// Switch to database
use arivu_db

// List collections
show collections

// Expected output:
// users
// bookmarks
// ai_summaries
// collections

// Check document counts
db.users.countDocuments()
db.bookmarks.countDocuments()
db.ai_summaries.countDocuments()

// Verify indexes exist
db.bookmarks.getIndexes()

// Expected indexes:
// - _id (default)
// - user_id
// - created_at
// - last_accessed
```

---

## Monitoring & Maintenance

### Health Monitoring Script

Create `/home/ubuntu/monitor-arivu.sh` (if not exists):

```bash
#!/bin/bash
# Continuous health monitoring for Arivu production

LOG_FILE="/home/ubuntu/arivu-uptime.log"

while true; do
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

  # Test with 10-second timeout
  START_TIME=$(date +%s.%N)
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 10 \
    https://your-domain.com/api/health 2>/dev/null)
  END_TIME=$(date +%s.%N)
  DURATION=$(echo "$END_TIME - $START_TIME" | bc)

  if [ "$STATUS" != "200" ]; then
    echo "[$TIMESTAMP] ❌ DOWN - HTTP $STATUS - Response time: ${DURATION}s" >> "$LOG_FILE"
  else
    if (( $(echo "$DURATION > 5" | bc -l) )); then
      echo "[$TIMESTAMP] ⚠️  SLOW - HTTP $STATUS - Response time: ${DURATION}s" >> "$LOG_FILE"
    else
      echo "[$TIMESTAMP] ✅ UP - HTTP $STATUS - Response time: ${DURATION}s" >> "$LOG_FILE"
    fi
  fi

  sleep 60  # Check every minute
done
```

**Setup Monitoring:**
```bash
chmod +x /home/ubuntu/monitor-arivu.sh

# Start in background
nohup /home/ubuntu/monitor-arivu.sh > /dev/null 2>&1 &

# View logs
tail -f /home/ubuntu/arivu-uptime.log
```

### Database Backup Strategy

**Daily Automated Backup:**

```bash
#!/bin/bash
# /home/ubuntu/backup-mongodb.sh

BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d)
MONGO_USER="admin"
MONGO_PASS="<your-password>"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker exec arivu-mongodb mongodump \
  --username=$MONGO_USER \
  --password=$MONGO_PASS \
  --authenticationDatabase=admin \
  --db=arivu_db \
  --out=/tmp/backup-$DATE

# Copy backup out of container
docker cp arivu-mongodb:/tmp/backup-$DATE $BACKUP_DIR/

# Compress backup
tar -czf $BACKUP_DIR/backup-$DATE.tar.gz $BACKUP_DIR/backup-$DATE

# Remove uncompressed backup
rm -rf $BACKUP_DIR/backup-$DATE

# Keep only last 7 days of backups
find $BACKUP_DIR -name "backup-*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/backup-$DATE.tar.gz"
```

**Setup Daily Cron:**
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /home/ubuntu/backup-mongodb.sh >> /home/ubuntu/backup.log 2>&1
```

**Restore from Backup:**
```bash
# Extract backup
tar -xzf /home/ubuntu/backups/backup-20251229.tar.gz

# Restore to database
docker cp backup-20251229 arivu-mongodb:/tmp/

docker exec arivu-mongodb mongorestore \
  --username=admin \
  --password=<your-password> \
  --authenticationDatabase=admin \
  --db=arivu_db \
  /tmp/backup-20251229/arivu_db
```

### Performance Monitoring

**Create MongoDB Indexes (After Deployment):**

```javascript
// Connect to MongoDB
use arivu_db

// Bookmarks collection indexes
db.bookmarks.createIndex({ "user_id": 1 })
db.bookmarks.createIndex({ "user_id": 1, "created_at": -1 })
db.bookmarks.createIndex({ "user_id": 1, "last_accessed": 1 })
db.bookmarks.createIndex({ "user_id": 1, "view_count": -1 })
db.bookmarks.createIndex({ "domain": 1 })

// AI Summaries indexes
db.ai_summaries.createIndex({ "bookmark_id": 1 }, { unique: true })
db.ai_summaries.createIndex({ "processing_status": 1 })

// Collections indexes
db.collections.createIndex({ "user_id": 1 })
db.collections.createIndex({ "user_id": 1, "created_at": -1 })

// Verify indexes
db.bookmarks.getIndexes()
```

**Resource Monitoring:**

```bash
# Check Docker container stats
docker stats --no-stream

# Expected resource usage:
# arivu-frontend:  < 100MB RAM, < 5% CPU
# arivu-backend:   < 500MB RAM, < 20% CPU
# arivu-mongodb:   < 300MB RAM, < 10% CPU

# Check disk usage
df -h

# Check MongoDB database size
docker exec arivu-mongodb mongosh \
  -u admin -p <password> \
  --authenticationDatabase admin \
  --eval "db.stats(1024*1024)"  # Size in MB
```

### Log Rotation

Create `/etc/logrotate.d/arivu`:

```
/home/ubuntu/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ubuntu ubuntu
}
```

Test log rotation:
```bash
sudo logrotate -f /etc/logrotate.d/arivu
```

---

## Security Hardening

### Security Checklist

**Before Going Live:**

- ✅ **SECRET_KEY:** Generated with `openssl rand -hex 32` (minimum 32 characters)
- ✅ **MongoDB:** Authentication enabled, not exposed to public internet
- ✅ **CORS:** Whitelisted to specific domain (not `*` in production)
- ✅ **HTTPS:** Enabled via Cloudflare
- ✅ **Environment Variables:** Not committed to Git, only on server
- ✅ **MongoDB User:** Has minimum required permissions (readWrite only)
- ✅ **Firewall:** MongoDB port (27017) blocked from internet
- ✅ **Passwords:** All default passwords changed
- ✅ **API Keys:** Valid, with appropriate rate limits
- ✅ **Container Resources:** Limits set to prevent DoS
- ✅ **Non-root User:** Backend runs as `appuser`, not root

### Firewall Configuration

**Using UFW (Ubuntu):**

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block MongoDB from internet (only allow Docker internal)
sudo ufw deny 27017/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### Rate Limiting

**Cloudflare Rate Limiting:**

1. **Navigate to:** Security → WAF → Rate Limiting Rules
2. **Create Rule:**
   - Name: "API Rate Limit"
   - If: Hostname equals `your-domain.com` AND Path starts with `/api/`
   - Then: Block when rate exceeds 100 requests per minute
   - Duration: 1 hour

**Backend Rate Limiting (Optional):**

Add to `backend/server.py`:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to specific endpoints
@app.post("/api/bookmarks")
@limiter.limit("10/minute")
async def create_bookmark(...):
    ...
```

### Security Headers

**Add to `frontend/nginx.conf`:**

```nginx
# Add to server block
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

# CSP (Content Security Policy)
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://your-domain.com;" always;
```

### Regular Security Maintenance

**Weekly Tasks:**
- Review access logs for suspicious activity
- Check for failed login attempts
- Monitor API rate limit violations
- Review Cloudflare security events

**Monthly Tasks:**
- Update Docker images (`docker-compose pull`)
- Review and rotate secrets if compromised
- Audit user accounts and permissions
- Check for outdated dependencies (`pip list --outdated`, `yarn outdated`)

**Quarterly Tasks:**
- Perform security audit
- Review and update firewall rules
- Test disaster recovery procedures
- Review backup integrity

---

## Troubleshooting

### Common Issues

See detailed troubleshooting guide: [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md)

**Quick Fixes:**

| Issue | Quick Fix |
|-------|-----------|
| Backend won't start | Check MongoDB connection, verify `MONGO_URL` |
| Frontend blank page | Rebuild with correct `REACT_APP_BACKEND_URL` |
| CORS errors | Update `CORS_ORIGINS` to match frontend domain |
| AI summaries stuck | Verify `GEMINI_API_KEY`, check quota |
| 504 Gateway Timeout | Check backend logs, restart backend container |
| MongoDB connection refused | Ensure MongoDB container is healthy |

**Get Help:**

1. Check container logs: `docker logs <container-name>`
2. Review [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md)
3. Check Docker container logs: `docker-compose logs -f`
4. Verify environment variables
5. Test health endpoints

---

## Summary

### Quick Deployment Checklist

**Local Development:**
- [ ] Docker installed and running
- [ ] `.env` file created with `GEMINI_API_KEY`
- [ ] `docker-compose up -d` executed
- [ ] All containers healthy
- [ ] Frontend accessible at http://localhost
- [ ] Backend health check passes

**Production Deployment:**
- [ ] VPS provisioned with Docker and Docker Compose
- [ ] Repository cloned on server
- [ ] `.env` file configured with production values
- [ ] `docker-compose -f docker-compose.prod.yml up -d --build` executed
- [ ] Cloudflare DNS A record created
- [ ] Cloudflare SSL mode set to Flexible
- [ ] Deployed successfully
- [ ] Health checks passing
- [ ] Test account created
- [ ] Test bookmark with AI summary works
- [ ] Monitoring scripts setup
- [ ] Database backups configured
- [ ] Security checklist completed

### Support Resources

- **Troubleshooting Guide:** [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md)
- **Architecture:** [ARCHITECTURE.md](../../ARCHITECTURE.md)
- **Contributing:** [CONTRIBUTING.md](../../CONTRIBUTING.md)

### External Documentation

- **Cloudflare Docs:** https://developers.cloudflare.com
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **MongoDB Docs:** https://docs.mongodb.com
- **Docker Compose:** https://docs.docker.com/compose/

---

**Deployment Status:** Production Ready ✅

**Estimated Deployment Time:**
- Local: 5-10 minutes
- Production: 20-30 minutes

---

*End of Deployment Guide - Version 2.2*
