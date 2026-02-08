"""
Data seeding script for Arivu load tests.

Creates a test user and inserts 50k+ realistic bookmarks with varied domains,
timestamps, tags, reading times, and embedding presence.

Usage:
    cd backend
    python load_tests/seed_data.py                  # Default: 50,000 bookmarks
    python load_tests/seed_data.py --count 100000   # Custom count
    python load_tests/seed_data.py --drop            # Drop existing data first

Requires:
    - MongoDB running (MONGO_URL env var or default localhost:27017)
    - No Docker needed (connects directly to MongoDB)
"""

import argparse
import asyncio
import hashlib
import os
import random
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient

# Realistic domain distribution (weighted to simulate real bookmarking patterns)
DOMAINS = [
    ("github.com", 15),
    ("stackoverflow.com", 12),
    ("medium.com", 10),
    ("dev.to", 8),
    ("docs.python.org", 6),
    ("news.ycombinator.com", 5),
    ("arxiv.org", 4),
    ("reddit.com", 4),
    ("developer.mozilla.org", 4),
    ("en.wikipedia.org", 3),
    ("blog.cloudflare.com", 3),
    ("aws.amazon.com", 3),
    ("kubernetes.io", 2),
    ("reactjs.org", 2),
    ("fastapi.tiangolo.com", 2),
    ("mongodb.com", 2),
    ("youtube.com", 2),
    ("twitter.com", 2),
    ("vercel.com", 1),
    ("tailwindcss.com", 1),
    ("nextjs.org", 1),
    ("svelte.dev", 1),
    ("rust-lang.org", 1),
    ("golang.org", 1),
    ("docker.com", 1),
    ("postgresql.org", 1),
    ("redis.io", 1),
    ("nginx.org", 1),
    ("grafana.com", 1),
    ("prometheus.io", 1),
]

# Flatten weighted domains into a selection pool
DOMAIN_POOL = []
for domain, weight in DOMAINS:
    DOMAIN_POOL.extend([domain] * weight)

# Title templates for realistic bookmark names
TITLE_TEMPLATES = [
    "How to {verb} {tech} in {year}",
    "{tech} {noun} Guide: {adjective} Approach",
    "Understanding {tech} {noun}",
    "Building a {adjective} {noun} with {tech}",
    "{tech} vs {tech2}: Which is Better?",
    "Top {number} {tech} {noun} for Developers",
    "{adjective} {tech} {noun} Tutorial",
    "Introduction to {tech} {noun}",
    "Advanced {tech} {noun} Patterns",
    "Why {tech} is the Future of {noun}",
    "{tech} Best Practices for {noun}",
    "Migrating from {tech} to {tech2}",
    "Deep Dive into {tech} {noun}",
    "The Complete {tech} {noun} Reference",
    "Debugging {tech} {noun}: Common Pitfalls",
]

VERBS = ["deploy", "configure", "optimize", "debug", "test", "scale", "monitor", "secure"]
TECH = [
    "Python", "JavaScript", "React", "FastAPI", "MongoDB", "Docker",
    "Kubernetes", "Redis", "GraphQL", "TypeScript", "Rust", "Go",
    "PostgreSQL", "Nginx", "Terraform", "AWS", "Tailwind", "Next.js",
]
NOUNS = [
    "applications", "microservices", "APIs", "databases", "pipelines",
    "clusters", "containers", "services", "workflows", "deployments",
    "architectures", "patterns", "testing", "monitoring", "security",
]
ADJECTIVES = ["scalable", "production-ready", "modern", "efficient", "resilient", "secure"]
TAGS = [
    "python", "javascript", "react", "fastapi", "mongodb", "docker",
    "kubernetes", "devops", "tutorial", "guide", "reference", "api",
    "machine-learning", "web-development", "backend", "frontend",
    "database", "security", "testing", "performance", "architecture",
]


def _generate_title():
    """Generate a realistic bookmark title."""
    template = random.choice(TITLE_TEMPLATES)
    tech1 = random.choice(TECH)
    tech2 = random.choice([t for t in TECH if t != tech1])
    return template.format(
        verb=random.choice(VERBS),
        tech=tech1,
        tech2=tech2,
        noun=random.choice(NOUNS),
        adjective=random.choice(ADJECTIVES),
        year=random.choice(["2024", "2025", "2026"]),
        number=random.choice(["5", "7", "10", "15", "20"]),
    )


def _generate_bookmark(user_id: str, index: int):
    """Generate a single realistic bookmark document."""
    domain = random.choice(DOMAIN_POOL)
    bookmark_id = str(uuid.uuid4())

    # Spread creation dates over the last 365 days
    days_ago = random.randint(0, 365)
    created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    updated_at = created_at + timedelta(hours=random.randint(0, 48))

    # 60% have been accessed at some point
    last_accessed = None
    view_count = 0
    if random.random() < 0.6:
        last_accessed = (created_at + timedelta(days=random.randint(1, days_ago + 1))).isoformat()
        view_count = random.randint(1, 20)

    # 70% have embeddings (simulates AI processing completion)
    embedding = None
    if random.random() < 0.7:
        # Generate a fake 768-dimensional L2-normalized embedding
        raw = [random.gauss(0, 1) for _ in range(768)]
        norm = sum(x * x for x in raw) ** 0.5
        embedding = [x / norm for x in raw]

    # Generate URL path based on domain and index for uniqueness
    path_hash = hashlib.md5(f"{index}-{bookmark_id}".encode()).hexdigest()[:12]
    url = f"https://{domain}/article/{path_hash}"

    bookmark = {
        "id": bookmark_id,
        "user_id": user_id,
        "url": url,
        "title": _generate_title(),
        "description": f"Bookmark {index} description" if random.random() < 0.8 else None,
        "domain": domain,
        "favicon": f"https://{domain}/favicon.ico",
        "thumbnail": f"https://{domain}/thumb/{path_hash}.jpg" if random.random() < 0.5 else None,
        "read_status": random.random() < 0.3,  # 30% read
        "reading_time": random.choice([2, 3, 5, 7, 10, 15, 20, None]),
        "version": 1,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "last_accessed": last_accessed,
        "view_count": view_count,
    }

    # Add embedding if generated
    if embedding is not None:
        bookmark["embedding"] = embedding

    return bookmark


async def ensure_test_user(db, email: str, password: str) -> str:
    """Create or find the load test user. Returns user ID."""
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    existing = await db.users.find_one({"email": email})
    if existing:
        print(f"  Test user already exists: {email} (id: {existing['id']})")
        return existing["id"]

    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": email,
        "name": "Load Test User",
        "hashed_password": pwd_context.hash(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    print(f"  Created test user: {email} (id: {user_id})")
    return user_id


async def create_indexes(db):
    """Create production-matching indexes for realistic performance testing."""
    print("  Creating indexes...")
    await db.bookmarks.create_index(
        [("user_id", 1), ("created_at", -1)],
        name="idx_user_created",
        background=True,
    )
    await db.bookmarks.create_index(
        [("user_id", 1), ("url", 1)],
        unique=True,
        name="idx_user_url_unique",
        background=True,
    )
    await db.bookmarks.create_index(
        [("user_id", 1), ("domain", 1)],
        name="idx_user_domain",
        background=True,
    )
    await db.bookmarks.create_index(
        [("user_id", 1), ("read_status", 1)],
        name="idx_user_readstatus",
        background=True,
    )
    print("  Indexes created.")


async def seed_bookmarks(
    db,
    user_id: str,
    count: int = 50000,
    batch_size: int = 1000,
):
    """Insert bookmarks in batches for efficiency."""
    print(f"  Seeding {count:,} bookmarks for user {user_id}...")
    total_inserted = 0
    start = time.time()

    for batch_start in range(0, count, batch_size):
        batch_end = min(batch_start + batch_size, count)
        batch = [
            _generate_bookmark(user_id, i)
            for i in range(batch_start, batch_end)
        ]

        try:
            result = await db.bookmarks.insert_many(batch, ordered=False)
            total_inserted += len(result.inserted_ids)
        except Exception as e:
            # ordered=False continues on duplicate key errors
            # Count successful inserts from the error
            if hasattr(e, "details") and "nInserted" in e.details:
                total_inserted += e.details["nInserted"]
            else:
                print(f"  Warning: Batch error at {batch_start}: {e}")

        # Progress report every 10k
        if (batch_end % 10000) == 0 or batch_end == count:
            elapsed = time.time() - start
            rate = total_inserted / elapsed if elapsed > 0 else 0
            print(
                f"  Progress: {total_inserted:,}/{count:,} "
                f"({total_inserted * 100 // count}%) "
                f"- {rate:,.0f} docs/sec"
            )

    elapsed = time.time() - start
    print(f"  Done: {total_inserted:,} bookmarks seeded in {elapsed:.1f}s")
    return total_inserted


async def main():
    parser = argparse.ArgumentParser(description="Seed Arivu load test data")
    parser.add_argument("--count", type=int, default=50000, help="Number of bookmarks to create")
    parser.add_argument("--drop", action="store_true", help="Drop existing bookmark data first")
    parser.add_argument(
        "--mongo-url",
        type=str,
        default=os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
        help="MongoDB connection URL",
    )
    parser.add_argument(
        "--db-name",
        type=str,
        default=os.environ.get("DB_NAME", "arivu_db"),
        help="Database name",
    )
    parser.add_argument("--email", type=str, default="loadtest@arivu.test", help="Test user email")
    parser.add_argument(
        "--password",
        type=str,
        default="LoadTest!SecureP@ss2026",
        help="Test user password",
    )
    args = parser.parse_args()

    print(f"Connecting to MongoDB: {args.mongo_url}")
    client = AsyncIOMotorClient(args.mongo_url)
    db = client[args.db_name]

    try:
        # Test connection
        await client.admin.command("ping")
        print("  Connected successfully.")

        if args.drop:
            print("  Dropping existing bookmarks...")
            await db.bookmarks.drop()
            print("  Dropped.")

        # Ensure test user exists
        user_id = await ensure_test_user(db, args.email, args.password)

        # Create indexes
        await create_indexes(db)

        # Seed bookmarks
        await seed_bookmarks(db, user_id, count=args.count)

        # Summary
        bookmark_count = await db.bookmarks.count_documents({"user_id": user_id})
        print(f"\nSummary:")
        print(f"  User: {args.email} (id: {user_id})")
        print(f"  Total bookmarks: {bookmark_count:,}")
        print(f"  Database: {args.db_name}")

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
