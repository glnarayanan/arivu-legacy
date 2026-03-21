"""
Locust load test scenarios for Arivu bookmarks API.

Simulates realistic user behavior: listing bookmarks, searching, viewing details,
and updating read status. Includes staged load shape ramping from 10 to 100 users.

Usage:
    cd backend
    locust -f load_tests/locustfile.py --host http://localhost:8001

    # Headless mode (CI-friendly):
    locust -f load_tests/locustfile.py --host http://localhost:8001 \
        --headless -u 50 -r 10 --run-time 5m

Web UI: http://localhost:8089
"""

import json
import os
import random

from locust import HttpUser, LoadTestShape, between, events, tag, task


# --- Custom CLI arguments ---
@events.init_command_line_parser.add_listener
def add_custom_arguments(parser):
    """Add auth-related CLI arguments for load testing."""
    parser.add_argument(
        "--test-email",
        type=str,
        default=os.environ.get("LOAD_TEST_EMAIL", "loadtest@arivu.test"),
        help="Email for the test user account",
    )
    parser.add_argument(
        "--test-password",
        type=str,
        default=os.environ.get("LOAD_TEST_PASSWORD", "LoadTest!SecureP@ss2026"),
        help="Password for the test user account",
    )


class BookmarkUser(HttpUser):
    """Simulates a typical Arivu user browsing and managing bookmarks.

    Weight distribution reflects real usage:
    - 50% listing/browsing (most common)
    - 30% searching (frequent)
    - 10% viewing bookmark details
    - 10% updating read status (least common)
    """

    wait_time = between(1, 3)

    # Cached state per user
    _access_token = None
    _bookmark_ids = []

    def on_start(self):
        """Authenticate and cache bookmark IDs for subsequent requests."""
        self._login()
        self._cache_bookmark_ids()

    def _login(self):
        """Authenticate via /api/auth/login and store the access token cookie."""
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": self.environment.parsed_options.test_email,
                "password": self.environment.parsed_options.test_password,
            },
            name="/api/auth/login",
        )
        if response.status_code == 200:
            # Cookies are automatically stored by locust's Session
            self._access_token = True
        else:
            # Log failure but don't crash; tasks will fail with 401
            self._access_token = None

    def _cache_bookmark_ids(self):
        """Fetch initial bookmark list to populate IDs for detail/update tasks."""
        if not self._access_token:
            return

        response = self.client.get(
            "/api/bookmarks",
            params={"limit": 100},
            name="/api/bookmarks (cache)",
        )
        if response.status_code == 200:
            try:
                data = response.json()
                self._bookmark_ids = [b["id"] for b in data if "id" in b]
            except (json.JSONDecodeError, KeyError):
                self._bookmark_ids = []

    def _random_bookmark_id(self):
        """Get a random bookmark ID from cache, or fallback to placeholder."""
        if self._bookmark_ids:
            return random.choice(self._bookmark_ids)
        return "nonexistent-bookmark-id"

    @tag("list")
    @task(5)
    def list_bookmarks(self):
        """GET /api/bookmarks -- list bookmarks with pagination."""
        limit = random.choice([20, 50, 100])
        sort_by = random.choice(["created_at", "title", "reading_time"])
        self.client.get(
            "/api/bookmarks",
            params={"limit": limit, "sort_by": sort_by},
            name="/api/bookmarks",
        )

    @tag("search")
    @task(3)
    def search_bookmarks(self):
        """GET /api/bookmarks with search query -- keyword search."""
        queries = [
            "python",
            "javascript",
            "machine learning",
            "api",
            "docker",
            "react",
            "fastapi",
            "mongodb",
            "tutorial",
            "guide",
        ]
        self.client.get(
            "/api/bookmarks",
            params={"search": random.choice(queries), "limit": 50},
            name="/api/bookmarks?search",
        )

    @tag("detail")
    @task(1)
    def view_bookmark_detail(self):
        """GET /api/bookmarks/{id} -- view a single bookmark."""
        bookmark_id = self._random_bookmark_id()
        self.client.get(
            f"/api/bookmarks/{bookmark_id}",
            name="/api/bookmarks/[id]",
        )

    @tag("update")
    @task(1)
    def update_read_status(self):
        """PATCH /api/bookmarks/{id}/read-status -- toggle read status."""
        bookmark_id = self._random_bookmark_id()
        read_status = random.choice([True, False])
        self.client.patch(
            f"/api/bookmarks/{bookmark_id}/read-status",
            params={"read_status": read_status},
            name="/api/bookmarks/[id]/read-status",
        )


class StagesShape(LoadTestShape):
    """Staged load shape: ramp up in steps, hold, then ramp down.

    Stages:
    1. Warm-up:   10 users for 60s  (baseline)
    2. Ramp-up:   50 users for 120s (normal load)
    3. Peak:     100 users for 120s (stress test)
    4. Cool-down:  25 users for 60s  (recovery)
    """

    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 2},
        {"duration": 180, "users": 50, "spawn_rate": 5},
        {"duration": 300, "users": 100, "spawn_rate": 10},
        {"duration": 360, "users": 25, "spawn_rate": 5},
    ]

    def tick(self):
        """Return (users, spawn_rate) for the current time in the test run."""
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]

        return None  # Stop the test after all stages
