# Arivu Backup Restoration Guide

**Version:** 1.0
**Created:** December 31, 2025
**Last Updated:** December 31, 2025

**⚠️ CRITICAL:** This document contains step-by-step instructions for restoring Arivu from Backblaze B2 backups.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Reference](#quick-reference)
4. [Restoration Scenarios](#restoration-scenarios)
5. [Step-by-Step Procedures](#step-by-step-procedures)
6. [Troubleshooting](#troubleshooting)
7. [Verification](#verification)

---

## Overview

### Backup Architecture

**Location:** Backblaze B2 bucket `arivu-app-backups`
**Encryption:** GPG AES-256 (client-side)
**Format:** Compressed tar.gz archives
**Retention:**
- Daily backups: 30 days (`/daily/`)
- Weekly backups: 52 weeks (`/weekly/`)
- Monthly backups: 12 months (`/monthly/`)

### What's Backed Up

Each backup contains:
- **MongoDB database dump** (all collections: users, bookmarks, ai_summaries, collections)
- **Environment variables** (.env file with secrets and API keys)
- **Docker Compose configuration** (docker-compose.prod.yml)
- **Deployment scripts** (deploy.sh, etc.)
- **Manifest file** (backup metadata and counts)

### Recovery Objectives

- **RPO (Recovery Point Objective):** 24 hours (daily backups)
- **RTO (Recovery Time Objective):** 15 minutes (complete restoration)

---

## Prerequisites

### Required Credentials

You need access to:

1. **Backblaze B2 Credentials**
   - Application Key ID: `003551ea72863bb0000000006`
   - Application Key: (stored securely)
   - Bucket: `arivu-app-backups`
   - Endpoint: Auto-detected by rclone

2. **GPG Encryption Passphrase**
   - Passphrase: (32+ characters, stored in password manager)
   - Used for: Decrypting backup files

3. **Server Access**
   - SSH access to production server OR
   - Ability to provision new server

### Required Tools

- `rclone` (for downloading from B2)
- `gpg` (for decrypting backups)
- `tar` (for extracting archives)
- `docker` and `docker compose` (for running MongoDB)
- `mongorestore` (included in MongoDB container)

---

## Quick Reference

### List Available Backups

```bash
# List all backups
./validate-backup.sh list

# Or manually with rclone
rclone lsf b2:arivu-app-backups/daily/
rclone lsf b2:arivu-app-backups/weekly/
rclone lsf b2:arivu-app-backups/monthly/
```

### Download a Backup

```bash
# Download specific backup
rclone copy b2:arivu-app-backups/daily/backup-20251231-030000.tar.gz.enc /tmp/

# Download latest backup
LATEST=$(rclone lsf b2:arivu-app-backups/daily/ | sort -r | head -1)
rclone copy "b2:arivu-app-backups/daily/${LATEST}" /tmp/
```

### Decrypt and Extract

```bash
# Decrypt
gpg --decrypt \
    --batch \
    --passphrase-file /home/ubuntu/.backup-encryption-key \
    --output /tmp/backup.tar.gz \
    /tmp/backup-20251231-030000.tar.gz.enc

# Extract
tar xzf /tmp/backup.tar.gz -C /tmp/
```

### Restore MongoDB

```bash
# Copy dump into MongoDB container
docker cp /tmp/backup-20251231-030000/mongodb-dump arivu-mongodb:/tmp/restore

# Restore database
docker exec arivu-mongodb mongorestore \
    --drop \
    --username=admin \
    --password=YOUR_MONGO_ROOT_PASSWORD \
    --authenticationDatabase=admin \
    /tmp/restore

# Cleanup
docker exec arivu-mongodb rm -rf /tmp/restore
```

---

## Restoration Scenarios

### Scenario 1: Single User Data Restoration

**When to use:** User accidentally deleted their bookmarks, need to restore specific user data.

**Time:** ~5 minutes
**Data Loss:** None (if backup exists before deletion)
**See:** [Restore Single User](#restore-single-user)

---

### Scenario 2: Complete Database Restoration

**When to use:** Database corruption, accidental data deletion affecting multiple users.

**Time:** ~15 minutes
**Data Loss:** Up to 24 hours (since last backup)
**See:** [Restore Complete Database](#restore-complete-database)

---

### Scenario 3: Complete Server Rebuild

**When to use:** Server failure, migration to new VPS, complete disaster recovery.

**Time:** ~30 minutes (plus DNS propagation if needed)
**Data Loss:** Up to 24 hours (since last backup)
**See:** [Complete Server Rebuild](#complete-server-rebuild)

---

### Scenario 4: Point-in-Time Recovery

**When to use:** Need data from specific date (audit, compliance, research).

**Time:** ~10 minutes
**Data Loss:** N/A (read-only recovery)
**See:** [Point-in-Time Recovery](#point-in-time-recovery)

---

## Step-by-Step Procedures

### Setup: Configure rclone and GPG

**Required before any restoration:**

```bash
# 1. Install rclone
sudo apt update && sudo apt install -y rclone

# 2. Configure rclone for B2
mkdir -p ~/.config/rclone
cat > ~/.config/rclone/rclone.conf <<EOF
[b2]
type = b2
account = 003551ea72863bb0000000006
key = YOUR_B2_APPLICATION_KEY
EOF
chmod 600 ~/.config/rclone/rclone.conf

# 3. Test B2 connection
rclone lsf b2:arivu-app-backups/daily/

# 4. Setup GPG passphrase
echo "YOUR_GPG_PASSPHRASE" > ~/.backup-encryption-key
chmod 600 ~/.backup-encryption-key

# 5. Test decryption
# (Will be verified during actual restoration)
```

---

### Restore Complete Database

**Scenario:** Need to restore entire MongoDB database to a previous state.

#### Step 1: Stop the Application

```bash
cd ~/arivu.app
docker compose -f docker-compose.prod.yml stop arivu-backend arivu-frontend
```

**Why:** Prevents new data from being written during restoration.

#### Step 2: Download Latest Backup

```bash
# Find latest backup
LATEST=$(rclone lsf b2:arivu-app-backups/daily/ | sort -r | head -1)
echo "Latest backup: ${LATEST}"

# Download to temporary location
mkdir -p /tmp/arivu-restore
rclone copy "b2:arivu-app-backups/daily/${LATEST}" /tmp/arivu-restore/ --progress
```

#### Step 3: Decrypt Backup

```bash
cd /tmp/arivu-restore

# Decrypt the backup
gpg --decrypt \
    --batch \
    --passphrase-file ~/.backup-encryption-key \
    --output "${LATEST%.enc}" \
    "${LATEST}"

# Verify decryption succeeded
ls -lh "${LATEST%.enc}"
```

#### Step 4: Extract Backup

```bash
# Extract tar.gz archive
tar xzf "${LATEST%.enc}"

# Find extracted backup directory
BACKUP_DIR=$(ls -d backup-* | head -1)
echo "Extracted to: ${BACKUP_DIR}"

# Verify contents
ls -la "${BACKUP_DIR}"/
cat "${BACKUP_DIR}/manifest.json"
```

#### Step 5: Restore MongoDB Data

```bash
# Get MongoDB password from backup .env
MONGO_PASSWORD=$(grep "^MONGO_ROOT_PASSWORD=" "${BACKUP_DIR}/.env" | cut -d'=' -f2 | tr -d '"' | tr -d "'")

# Copy dump into MongoDB container
docker cp "${BACKUP_DIR}/mongodb-dump" arivu-mongodb:/tmp/restore-dump

# Restore database (--drop removes existing data first)
docker exec arivu-mongodb mongorestore \
    --drop \
    --username=admin \
    --password="${MONGO_PASSWORD}" \
    --authenticationDatabase=admin \
    /tmp/restore-dump

# Cleanup inside container
docker exec arivu-mongodb rm -rf /tmp/restore-dump
```

#### Step 6: Verify Restoration

```bash
# Check database counts
docker exec arivu-mongodb mongosh \
    --username=admin \
    --password="${MONGO_PASSWORD}" \
    --authenticationDatabase=admin \
    --eval '
        db = db.getSiblingDB("arivu_db");
        print("Users:", db.users.countDocuments());
        print("Bookmarks:", db.bookmarks.countDocuments());
        print("AI Summaries:", db.ai_summaries.countDocuments());
    '
```

#### Step 7: Restart Application

```bash
cd ~/arivu.app
docker compose -f docker-compose.prod.yml up -d arivu-backend arivu-frontend

# Check health
docker compose -f docker-compose.prod.yml ps
curl -s http://localhost:8001/api/health | jq '.'
```

#### Step 8: Test Functionality

```bash
# Test login
# Test bookmark listing
# Test AI summary display
# Verify user data is correct
```

#### Step 9: Cleanup

```bash
# Remove temporary restoration files
rm -rf /tmp/arivu-restore
```

---

### Complete Server Rebuild

**Scenario:** Server failure, migration to new VPS, complete disaster recovery.

#### Prerequisites

- New server with Docker installed
- SSH access to new server
- Backblaze B2 credentials
- GPG encryption passphrase

#### Step 1: Provision New Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install required tools
sudo apt install -y git rclone gpg curl jq

# Logout and login again for docker group to take effect
```

#### Step 2: Setup rclone and GPG

```bash
# Configure rclone (see "Setup: Configure rclone and GPG" section)
mkdir -p ~/.config/rclone
cat > ~/.config/rclone/rclone.conf <<EOF
[b2]
type = b2
account = 003551ea72863bb0000000006
key = YOUR_B2_APPLICATION_KEY
EOF
chmod 600 ~/.config/rclone/rclone.conf

# Setup GPG passphrase
echo "YOUR_GPG_PASSPHRASE" > ~/.backup-encryption-key
chmod 600 ~/.backup-encryption-key
```

#### Step 3: Clone Application Repository

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/arivu.app.git
cd arivu.app
```

#### Step 4: Download and Restore Configuration

```bash
# Download latest backup
LATEST=$(rclone lsf b2:arivu-app-backups/daily/ | sort -r | head -1)
mkdir -p /tmp/restore
rclone copy "b2:arivu-app-backups/daily/${LATEST}" /tmp/restore/ --progress

# Decrypt and extract
cd /tmp/restore
gpg --decrypt --batch --passphrase-file ~/.backup-encryption-key \
    --output "${LATEST%.enc}" "${LATEST}"
tar xzf "${LATEST%.enc}"

# Find backup directory
BACKUP_DIR=$(ls -d backup-* | head -1)

# Restore .env file
cp "${BACKUP_DIR}/.env" ~/arivu.app/.env
chmod 600 ~/arivu.app/.env

# Restore docker-compose if needed
if [ -f "${BACKUP_DIR}/docker-compose.prod.yml" ]; then
    cp "${BACKUP_DIR}/docker-compose.prod.yml" ~/arivu.app/
fi
```

#### Step 5: Start Application

```bash
cd ~/arivu.app

# Start all containers
docker compose -f docker-compose.prod.yml up -d

# Wait for MongoDB to be ready
sleep 10
docker compose -f docker-compose.prod.yml ps
```

#### Step 6: Restore Database

```bash
# Get MongoDB password
MONGO_PASSWORD=$(grep "^MONGO_ROOT_PASSWORD=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")

# Copy dump into container
docker cp "/tmp/restore/${BACKUP_DIR}/mongodb-dump" arivu-mongodb:/tmp/restore-dump

# Restore database
docker exec arivu-mongodb mongorestore \
    --username=admin \
    --password="${MONGO_PASSWORD}" \
    --authenticationDatabase=admin \
    /tmp/restore-dump

# Cleanup
docker exec arivu-mongodb rm -rf /tmp/restore-dump
```

#### Step 7: Verify Application

```bash
# Check all containers running
docker compose -f docker-compose.prod.yml ps

# Test backend health
curl http://localhost:8001/api/health

# Test frontend (if applicable)
curl http://localhost:3000
```

#### Step 8: Update DNS (if new IP)

```bash
# Get new server IP
curl -s http://ifconfig.me
echo "Update DNS records to point to this IP"

# Configure firewall if needed
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

#### Step 9: Setup Backup System

```bash
# Copy backup scripts from repository or backup
cp /tmp/restore/${BACKUP_DIR}/deploy.sh ~/deploy.sh 2>/dev/null || true
chmod +x ~/deploy.sh 2>/dev/null || true

# Reinstall backup automation
# (Setup cron jobs as described in setup section)
```

#### Step 10: Cleanup

```bash
rm -rf /tmp/restore
```

---

### Restore Single User

**Scenario:** Single user accidentally deleted data, need selective restoration.

#### Step 1: Download and Extract Backup

```bash
# Follow steps 2-4 from "Restore Complete Database" section
# This will give you the backup extracted in /tmp/arivu-restore/
```

#### Step 2: Export User Data from Backup

```bash
# Get user email to restore
USER_EMAIL="user@example.com"

# Get MongoDB password
MONGO_PASSWORD=$(grep "^MONGO_ROOT_PASSWORD=" ~/arivu.app/.env | cut -d'=' -f2 | tr -d '"' | tr -d "'")

# Create temporary MongoDB instance for backup data
docker run -d --name arivu-restore-temp -p 27018:27017 \
    -e MONGO_INITDB_ROOT_USERNAME=admin \
    -e MONGO_INITDB_ROOT_PASSWORD=temppass \
    mongo:latest

# Wait for it to start
sleep 10

# Restore backup into temporary instance
docker cp /tmp/arivu-restore/${BACKUP_DIR}/mongodb-dump arivu-restore-temp:/tmp/dump
docker exec arivu-restore-temp mongorestore \
    --username=admin \
    --password=temppass \
    --authenticationDatabase=admin \
    /tmp/dump

# Export user's bookmarks
docker exec arivu-restore-temp mongosh \
    --username=admin \
    --password=temppass \
    --authenticationDatabase=admin \
    --quiet \
    --eval "
        db = db.getSiblingDB('arivu_db');
        var user = db.users.findOne({email: '${USER_EMAIL}'});
        if (!user) { print('User not found'); quit(1); }
        print('User ID: ' + user.id);
        print('Bookmarks count: ' + db.bookmarks.countDocuments({user_id: user.id}));
    "
```

#### Step 3: Import User Data to Production

```bash
# Export user data from temporary DB
docker exec arivu-restore-temp mongoexport \
    --username=admin \
    --password=temppass \
    --authenticationDatabase=admin \
    --db=arivu_db \
    --collection=bookmarks \
    --query="{\"user_id\": \"USER_ID_HERE\"}" \
    --out=/tmp/user-bookmarks.json

# Copy export file out of container
docker cp arivu-restore-temp:/tmp/user-bookmarks.json /tmp/

# Import into production MongoDB
docker cp /tmp/user-bookmarks.json arivu-mongodb:/tmp/
docker exec arivu-mongodb mongoimport \
    --username=admin \
    --password="${MONGO_PASSWORD}" \
    --authenticationDatabase=admin \
    --db=arivu_db \
    --collection=bookmarks \
    --mode=upsert \
    --file=/tmp/user-bookmarks.json
```

#### Step 4: Cleanup

```bash
# Stop and remove temporary MongoDB
docker stop arivu-restore-temp
docker rm arivu-restore-temp

# Clean up files
rm -rf /tmp/arivu-restore
rm /tmp/user-bookmarks.json
```

---

### Point-in-Time Recovery

**Scenario:** Need to access data from a specific date (audit, compliance, historical analysis).

#### Step 1: Find Backup for Specific Date

```bash
# List backups by date
rclone lsf b2:arivu-app-backups/daily/ --format "tp" | grep "2025-12-25"

# Or search weekly/monthly
rclone lsf b2:arivu-app-backups/weekly/ --format "tp"
rclone lsf b2:arivu-app-backups/monthly/ --format "tp"
```

#### Step 2: Download Specific Backup

```bash
# Download backup for specific date
BACKUP_FILE="backup-20251225-030000.tar.gz.enc"
rclone copy "b2:arivu-app-backups/daily/${BACKUP_FILE}" /tmp/pit-recovery/
```

#### Step 3: Extract to Read-Only Location

```bash
cd /tmp/pit-recovery

# Decrypt
gpg --decrypt --batch --passphrase-file ~/.backup-encryption-key \
    --output "${BACKUP_FILE%.enc}" "${BACKUP_FILE}"

# Extract
tar xzf "${BACKUP_FILE%.enc}"

# View manifest
BACKUP_DIR=$(ls -d backup-* | head -1)
cat "${BACKUP_DIR}/manifest.json"
```

#### Step 4: Create Temporary Read-Only MongoDB

```bash
# Start temporary MongoDB on different port
docker run -d --name arivu-historical \
    -p 27019:27017 \
    -e MONGO_INITDB_ROOT_USERNAME=admin \
    -e MONGO_INITDB_ROOT_PASSWORD=readonly \
    mongo:latest

# Wait for startup
sleep 10

# Restore historical data
docker cp "${BACKUP_DIR}/mongodb-dump" arivu-historical:/tmp/dump
docker exec arivu-historical mongorestore \
    --username=admin \
    --password=readonly \
    --authenticationDatabase=admin \
    /tmp/dump
```

#### Step 5: Query Historical Data

```bash
# Connect and query
docker exec -it arivu-historical mongosh \
    --username=admin \
    --password=readonly \
    --authenticationDatabase=admin

# In mongosh:
# use arivu_db
# db.users.countDocuments()
# db.bookmarks.find({}).limit(10)
# exit
```

#### Step 6: Export Required Data

```bash
# Export specific data to JSON
docker exec arivu-historical mongoexport \
    --username=admin \
    --password=readonly \
    --authenticationDatabase=admin \
    --db=arivu_db \
    --collection=bookmarks \
    --out=/tmp/historical-export.json

# Copy out of container
docker cp arivu-historical:/tmp/historical-export.json /tmp/
```

#### Step 7: Cleanup

```bash
docker stop arivu-historical
docker rm arivu-historical
rm -rf /tmp/pit-recovery
```

---

## Troubleshooting

### Problem: Cannot Connect to B2

**Symptoms:** `rclone` commands fail with authentication errors

**Solutions:**
```bash
# 1. Verify credentials in rclone config
cat ~/.config/rclone/rclone.conf

# 2. Test authentication
rclone lsd b2:

# 3. Reconfigure if needed
rclone config

# 4. Check B2 application key hasn't been revoked in B2 dashboard
```

---

### Problem: GPG Decryption Fails

**Symptoms:** `gpg: decryption failed: Bad session key`

**Solutions:**
```bash
# 1. Verify passphrase file exists
cat ~/.backup-encryption-key

# 2. Check file permissions
ls -la ~/.backup-encryption-key  # Should be -rw-------

# 3. Verify passphrase is correct
# Try decrypting a test backup manually

# 4. If passphrase lost, recovery impossible
# Backups are encrypted and cannot be recovered without passphrase
```

---

### Problem: MongoDB Restore Fails

**Symptoms:** `mongorestore` errors, authentication failures

**Solutions:**
```bash
# 1. Verify MongoDB is running
docker ps | grep arivu-mongodb

# 2. Check MongoDB credentials
docker exec arivu-mongodb mongosh \
    --username=admin \
    --password=YOUR_PASSWORD \
    --authenticationDatabase=admin \
    --eval 'db.version()'

# 3. Ensure database name matches
# Database should be 'arivu_db'

# 4. Check dump directory structure
ls -la /path/to/dump/arivu_db/
```

---

### Problem: Backup Download Slow

**Symptoms:** Slow B2 download speeds

**Solutions:**
```bash
# 1. Use rclone with multiple transfers
rclone copy b2:arivu-app-backups/daily/backup.tar.gz.enc /tmp/ \
    --transfers=4 \
    --checkers=8 \
    --progress

# 2. Check your internet connection
speedtest-cli

# 3. Try different time of day (peak hours may be slower)
```

---

## Verification

### Verify Backup Contents

```bash
# Use the validation script
./validate-backup.sh backup-20251231-030000.tar.gz.enc

# Or manually:
./validate-backup.sh latest
```

### Verify Database Counts After Restore

```bash
# Connect to MongoDB and count documents
docker exec arivu-mongodb mongosh \
    --username=admin \
    --password=YOUR_PASSWORD \
    --authenticationDatabase=admin \
    --eval '
        db = db.getSiblingDB("arivu_db");
        print("Users:", db.users.countDocuments());
        print("Bookmarks:", db.bookmarks.countDocuments());
        print("AI Summaries:", db.ai_summaries.countDocuments());
        print("Collections:", db.collections.countDocuments());
    '
```

### Verify Application Health

```bash
# Check all containers
docker compose -f docker-compose.prod.yml ps

# Test backend API
curl http://localhost:8001/api/health

# Test authentication
curl -X POST http://localhost:8001/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "test@example.com", "password": "testpass"}'

# Check logs for errors
docker compose -f docker-compose.prod.yml logs --tail=50
```

---

## Important Notes

### Security

- ✅ Always verify backup integrity before deleting old production data
- ✅ Keep GPG passphrase in a secure password manager
- ✅ Store B2 credentials securely (not in version control)
- ✅ Use read-only temporary containers for point-in-time recovery

### Best Practices

- 🔄 Test restoration quarterly on a separate server
- 📊 Document actual restoration times vs. RTO
- 🔍 Verify restored data matches expected counts from manifest
- 🧹 Clean up temporary files and containers after restoration
- 📝 Update this document if restoration procedures change

### Recovery Time Estimates

| Scenario | Estimated Time | Actual Time |
|----------|---------------|-------------|
| Single User Restore | 5 minutes | ____________ |
| Complete Database | 15 minutes | ____________ |
| Server Rebuild | 30 minutes | ____________ |
| Point-in-Time | 10 minutes | ____________ |

*Fill in actual times during disaster recovery drills*

---

## Contact & Support

**For restoration assistance:**
- Review this documentation thoroughly
- Check troubleshooting section
- Verify all prerequisites are met
- Document any errors encountered

**Critical credential locations:**
- B2 credentials: `~/.config/rclone/rclone.conf`
- GPG passphrase: `~/.backup-encryption-key`
- MongoDB credentials: `~/arivu.app/.env`

---

**End of Restoration Guide**

*Last tested: _____________ (Update after disaster recovery drills)*
