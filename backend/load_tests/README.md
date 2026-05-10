# Arivu Load Tests

Load testing infrastructure for the Arivu bookmarks API using [Locust](https://locust.io/).

## Prerequisites

- Python 3.11+ with `locust` and `motor` installed (`pip install -r requirements.txt`)
- MongoDB running (local or Docker)
- Backend API running on target host

## Quick Start

### 1. Seed Test Data

Create a test user and 50k+ realistic bookmarks:

```bash
cd backend
python load_tests/seed_data.py --count 50000
```

Options:
- `--count N` -- Number of bookmarks (default: 50,000)
- `--drop` -- Drop existing bookmark data before seeding
- `--mongo-url URL` -- MongoDB connection string (default: `$MONGO_URL` or `mongodb://localhost:27017`)
- `--email EMAIL` -- Test user email (default: `loadtest@arivu.test`)
- `--password PASS` -- Test user password (default: `LoadTest!SecureP@ss2026`)

### 2. Run Load Tests

```bash
cd backend

# With web UI (recommended for exploration)
locust -f load_tests/locustfile.py --host http://localhost:8001

# Headless mode (CI-friendly)
locust -f load_tests/locustfile.py --host http://localhost:8001 \
    --headless -u 50 -r 10 --run-time 5m
```

Web UI: http://localhost:8089

### 3. Custom Auth Credentials

```bash
locust -f load_tests/locustfile.py --host http://localhost:8001 \
    --test-email "custom@test.com" --test-password "CustomPass123!"
```

Or via environment variables:
```bash
export LOAD_TEST_EMAIL="custom@test.com"
export LOAD_TEST_PASSWORD="CustomPass123!"
```

## Test Scenarios

| Scenario | Weight | Endpoint | Description |
|----------|--------|----------|-------------|
| List bookmarks | 5 | `GET /api/bookmarks` | Paginated listing with varied limits/sorts |
| Search bookmarks | 3 | `GET /api/bookmarks?search=` | Keyword search across common terms |
| View detail | 1 | `GET /api/bookmarks/{id}` | Single bookmark with AI summary |
| Update read status | 1 | `PATCH /api/bookmarks/{id}/read-status` | Toggle read/unread |

## Load Shape

The `StagesShape` class defines a staged ramp:

| Stage | Duration | Users | Spawn Rate |
|-------|----------|-------|------------|
| Warm-up | 0-60s | 10 | 2/s |
| Normal | 60-180s | 50 | 5/s |
| Peak | 180-300s | 100 | 10/s |
| Cool-down | 300-360s | 25 | 5/s |

## Performance Targets

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| P50 list/search | < 200ms | > 500ms |
| P95 list/search | < 500ms | > 1s |
| P99 all operations | < 2s | > 5s |
| Error rate | 0% | > 1% |
| Throughput (50 users) | > 100 req/s | < 50 req/s |

## Seed Data Characteristics

The seeding script generates realistic bookmarks with:

- **30 domains** weighted by popularity (github.com most common)
- **Timestamps** spread over the last 365 days
- **70% have embeddings** (768-dimensional L2-normalized vectors)
- **30% marked as read**
- **60% have been accessed** (with view counts 1-20)
- **Varied reading times** (2-20 minutes, some null)
- **Unique URLs** per user (enforced by database index)

## Troubleshooting

**Auth failures (401):** Ensure the test user exists. Re-run `seed_data.py` to create it.

**Slow seeding:** Reduce `--count` or check MongoDB connection latency. The script inserts in batches of 1,000 for efficiency.

**Rate limiting:** The API has rate limits. If you see 429 responses, reduce the user count or add wait time in the Locust config.
