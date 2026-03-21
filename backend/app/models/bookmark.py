"""
Bookmark domain models - extracted from server.py (Phase 6, Plan 01).

Shared Pydantic models used by bookmarks router and other consumers.
"""

import ipaddress
import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, validator

UTC = timezone.utc

logger = logging.getLogger(__name__)


def is_safe_url(url: str) -> tuple:
    """Validate URL to prevent SSRF attacks (non-blocking validation)"""
    try:
        parsed = urlparse(url)

        # Only allow http/https schemes
        if parsed.scheme not in ["http", "https"]:
            return False, "Only HTTP and HTTPS URLs are allowed"

        # Must have a hostname
        if not parsed.hostname:
            return False, "Invalid URL: missing hostname"

        hostname = parsed.hostname.lower()

        # Block localhost and loopback addresses (check hostname directly)
        if hostname in ["localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"]:
            return False, "Cannot fetch from localhost or loopback addresses"

        # Block private hostnames
        if hostname.endswith(".local") or hostname.endswith(".localhost"):
            return False, "Cannot fetch from local network addresses"

        # Block private IP ranges (check if hostname is already an IP)
        try:
            # If hostname is an IP address, validate it directly (no DNS lookup needed)
            ip_obj = ipaddress.ip_address(hostname)

            # Block private, loopback, link-local, and reserved ranges
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                return False, "Cannot fetch from private or reserved IP addresses"

            # Block cloud metadata endpoints (AWS, GCP, Azure)
            if str(ip_obj) == "169.254.169.254":
                return False, "Cannot fetch from cloud metadata endpoints"

        except ValueError:
            # hostname is not an IP address, it's a domain name
            # Skip DNS resolution to avoid blocking - the requests library will handle it
            # and will timeout if the domain resolves to a bad IP
            pass

        return True, ""

    except Exception as e:
        logger.warning(f"URL validation error: {str(e)}")
        return False, "Invalid URL format"


class BookmarkCreate(BaseModel):
    url: str
    collection_id: str | None = None

    @validator("url")
    def validate_url(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("URL cannot be empty")
        if len(v) > 2048:
            raise ValueError("URL too long (max 2048 characters)")

        # Validate URL is safe (SSRF protection)
        safe, error_msg = is_safe_url(v)
        if not safe:
            raise ValueError(error_msg)

        return v.strip()


class Bookmark(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    url: str
    title: str | None = None
    description: str | None = None
    favicon: str | None = None
    thumbnail: str | None = None
    html_content: str | None = None
    text_content: str | None = None
    domain: str | None = None
    reading_time: int | None = None
    read_status: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # Phase 1: Access tracking fields
    last_accessed: datetime | None = None
    view_count: int | None = 0
    access_history: list[dict[str, str]] | None = []
    # Semantic Knowledge Graph: Embedding vector for semantic search
    embedding: list[float] | None = None
    embedding_model: str | None = None
    entities: list[str] | None = []  # Named entities extracted from content
    concepts: list[str] | None = []  # Key concepts/topics
    # X (Twitter) integration fields
    source: str | None = "web"  # "web" | "x"
    x_tweet_id: str | None = None
    x_author_username: str | None = None
    x_author_name: str | None = None
    x_tweet_url: str | None = None
    x_metrics: dict | None = None
    # Optimistic locking version (REL-03)
    version: int = 1


class QuickConnection(BaseModel):
    id: str
    title: str | None = None
    domain: str | None = None
    favicon: str | None = None
    connection_type: str
    connection_reason: str


class BookmarkWithConnections(BaseModel):
    bookmark: Bookmark
    connections: list[QuickConnection] = []
    connections_count: int = 0
