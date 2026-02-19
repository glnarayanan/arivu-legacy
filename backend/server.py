from fastapi import (
    FastAPI,
    APIRouter,
    HTTPException,
    Depends,
    status,
    BackgroundTasks,
    Request,
    Response,
)
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr, validator
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import asyncio
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse, quote
import requests
import re
import ipaddress
import socket
import sys
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.dependencies import limiter
import time
import resend
import secrets
import redis.asyncio as aioredis
import httpx
from cryptography.fernet import Fernet
import hashlib
import base64
from app.core.database import init_db as init_core_db, close_db as close_core_db
from app.routers.bookmarks import router as bookmarks_router
from app.routers.collections import router as collections_router
from app.routers.analytics import router as analytics_router
from app.routers.resurfacing import router as resurfacing_router
from app.routers.auth import router as auth_router
from app.routers.search import router as search_router
from app.routers.knowledge_graph import router as knowledge_graph_router
from app.routers.import_export import router as import_export_router
from app.routers.content import router as content_router
from app.services.ai_service import (
    gemini_rate_limiter,
    generate_ai_summaries,
    generate_embedding,
    extract_entities_and_concepts,
)
from app.services.content_service import (
    fetch_webpage_content,
    calculate_reading_time,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")


# Environment detection for security settings
IS_PRODUCTION = os.environ.get("ENVIRONMENT", "development") == "production"

# Configure structured logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
logger.info(f"Server running in {'PRODUCTION' if IS_PRODUCTION else 'DEVELOPMENT'} mode")

mongo_url = os.environ["MONGO_URL"]
# Configure MongoDB client with timeouts to prevent hanging connections
client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=5000,  # 5 second timeout for server selection
    connectTimeoutMS=10000,  # 10 second timeout for initial connection
    socketTimeoutMS=30000,  # 30 second timeout for socket operations
    maxPoolSize=50,  # Limit connection pool size
    minPoolSize=10,  # Keep connections warm to avoid cold starts
    maxIdleTimeMS=45000,  # Close idle connections after 45 seconds
    waitQueueTimeoutMS=10000,  # 10 second timeout waiting for connection from pool
    retryWrites=True,  # Enable retry for write operations
    retryReads=True,  # Enable retry for read operations
    compressors=["snappy"],  # Network compression for large embeddings
)
db_name = os.environ.get("DB_NAME", "arivu_db")
db = client[db_name]

init_core_db()

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Extracted routers (Phase 4, 5, 6)
# import_export_router MUST be before bookmarks_router because
# /bookmarks/import, /bookmarks/export, /bookmarks/backup must match
# before the bookmarks router's /bookmarks/{bookmark_id} catch-all.
api_router.include_router(import_export_router)
api_router.include_router(content_router)
api_router.include_router(bookmarks_router)
api_router.include_router(collections_router)
api_router.include_router(analytics_router)
api_router.include_router(resurfacing_router)
api_router.include_router(auth_router)
api_router.include_router(search_router)
api_router.include_router(knowledge_graph_router)

# Initialize rate limiter (single instance from app.core.dependencies)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Validate SECRET_KEY is set and strong
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    logger.error("SECRET_KEY must be set and at least 32 characters long")
    raise ValueError("SECRET_KEY must be set and at least 32 characters long")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour for access tokens
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days for refresh tokens
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 1  # 1 hour for password reset tokens

SERVER_START_TIME = datetime.now(timezone.utc)

ADMIN_EMAILS = [e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()]

# Account lockout configuration (SEC-04)
LOCKOUT_THRESHOLD = 5  # Failed attempts before lockout
LOCKOUT_DURATION_SECONDS = 15 * 60  # 15 minutes

# Content fetching limits (SEC-05)
MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10MB max for webpage content

# Resend email configuration
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "noreply@arivu.app")
APP_URL = os.environ.get("APP_URL", "https://arivu.app")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    logger.info("Resend email configured successfully")
else:
    logger.warning("RESEND_API_KEY not set - password reset emails will not work")

# X (Twitter) Integration
X_INTEGRATION_ENABLED = os.environ.get("X_INTEGRATION_ENABLED", "false").lower() in ("true", "1", "yes")
X_CLIENT_ID = os.environ.get("X_CLIENT_ID")
X_CLIENT_SECRET = os.environ.get("X_CLIENT_SECRET")
X_REDIRECT_URI = os.environ.get("X_REDIRECT_URI") or f"{APP_URL}/settings?section=connections"
_x_max_pages = int(os.environ.get("X_MAX_BOOKMARK_PAGES", "10"))
X_MAX_BOOKMARK_PAGES = None if _x_max_pages <= 0 else _x_max_pages
# Cap total bookmarks fetched per sync. Set to 0 or remove to fetch all.
# To remove: delete this line and the "total tweet cap" block in x_sync().
_x_max_bookmarks = int(os.environ.get("X_MAX_BOOKMARKS", "300"))
X_MAX_BOOKMARKS = None if _x_max_bookmarks <= 0 else _x_max_bookmarks

if X_INTEGRATION_ENABLED and X_CLIENT_ID:
    logger.info("X (Twitter) integration enabled and configured")
elif X_INTEGRATION_ENABLED:
    logger.warning("X (Twitter) integration enabled but X_CLIENT_ID not set")
else:
    logger.info("X_CLIENT_ID not set - X bookmark integration disabled")

X_TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "gclid",
    "fbclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
}

# Fernet encryption for storing OAuth tokens at rest
_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest())
fernet = Fernet(_fernet_key)


def encrypt_token(token: str) -> str:
    """Encrypt a token string using Fernet symmetric encryption."""
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted token string."""
    return fernet.decrypt(encrypted.encode()).decode()


def normalize_url_for_dedup(url: str) -> str:
    """Normalize URLs for deduplication by removing tracking params and fragments."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return url

        scheme = parsed.scheme.lower() if parsed.scheme else "https"
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        query_params = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in X_TRACKING_QUERY_PARAMS
        ]
        query = urlencode(query_params, doseq=True)

        return urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return url


def build_x_oauth_url(
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    scopes: str,
) -> str:
    """Build a properly-encoded OAuth URL for X authorization."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"https://twitter.com/i/oauth2/authorize?{urlencode(params, quote_via=quote)}"


def map_x_sync_error_status(status_code: int) -> str:
    """Map X sync errors to connection sync_status values."""
    if status_code == 401:
        return "auth_expired"
    if status_code == 429:
        return "rate_limited"
    return "error"


# Redis client for account lockout tracking (SEC-04)
redis_client = None


async def get_redis():
    """Get or create Redis client for lockout tracking"""
    global redis_client
    if redis_client is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        redis_client = await aioredis.from_url(redis_url, decode_responses=True)
        logger.info("Redis client initialized for account lockout tracking")
    return redis_client


async def is_account_locked(email: str) -> bool:
    """Check if account is locked due to too many failed attempts"""
    try:
        r = await get_redis()
        attempts = await r.get(f"login_attempts:{email}")
        return attempts is not None and int(attempts) >= LOCKOUT_THRESHOLD
    except Exception as e:
        logger.exception(f"Redis error checking lockout for {email}")
        return False  # Fail open - don't block login if Redis is down


async def record_failed_login(email: str):
    """Increment failed login counter with expiry"""
    try:
        r = await get_redis()
        key = f"login_attempts:{email}"
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, LOCKOUT_DURATION_SECONDS)
        await pipe.execute()
    except Exception as e:
        logger.exception(f"Redis error recording failed login for {email}")


async def clear_failed_logins(email: str):
    """Clear failed login counter on successful login"""
    try:
        r = await get_redis()
        await r.delete(f"login_attempts:{email}")
    except Exception as e:
        logger.exception(f"Redis error clearing failed logins for {email}")


# Security validation functions
def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets security requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, ""


def is_safe_url(url: str) -> tuple[bool, str]:
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
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
            ):
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


class BackupRequest(BaseModel):
    format: str = "html"  # "html" | "json" | "csv"
    include_notes: bool = True
    include_ai_summaries: bool = True
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class BookmarkCreate(BaseModel):
    url: str
    collection_id: Optional[str] = None

    @validator("url")
    def validate_url(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("URL cannot be empty")
        if len(v) > 2048:
            raise ValueError("URL too long (max 2048 characters)")

        # Validate URL is safe (SSRF protection)
        is_safe, error_msg = is_safe_url(v)
        if not is_safe:
            raise ValueError(error_msg)

        return v.strip()


class Bookmark(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    favicon: Optional[str] = None
    thumbnail: Optional[str] = None
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    domain: Optional[str] = None
    reading_time: Optional[int] = None
    read_status: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Phase 1: Access tracking fields
    last_accessed: Optional[datetime] = None
    view_count: Optional[int] = 0
    access_history: Optional[List[Dict[str, str]]] = []
    # Semantic Knowledge Graph: Embedding vector for semantic search
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    entities: Optional[List[str]] = []  # Named entities extracted from content
    concepts: Optional[List[str]] = []  # Key concepts/topics
    # X (Twitter) integration fields
    source: Optional[str] = "web"  # "web" | "x"
    x_tweet_id: Optional[str] = None
    x_author_username: Optional[str] = None
    x_author_name: Optional[str] = None
    x_tweet_url: Optional[str] = None
    x_metrics: Optional[Dict] = None
    # Optimistic locking version (REL-03)
    version: int = 1


class QuickConnection(BaseModel):
    id: str
    title: Optional[str] = None
    domain: Optional[str] = None
    favicon: Optional[str] = None
    connection_type: str
    connection_reason: str


class BookmarkWithConnections(BaseModel):
    bookmark: Bookmark
    connections: List[QuickConnection] = []
    connections_count: int = 0


class AISummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bookmark_id: str
    one_sentence: Optional[str] = None
    bullet_points: List[str] = []
    long_form: Optional[str] = None
    highlights: List[str] = []
    suggested_tags: List[str] = []
    processing_status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ImportJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    total_bookmarks: int
    content_fetched: int = 0
    ai_processed: int = 0
    failed: int = 0
    status: str = "processing"  # processing, completed, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_completion_time: Optional[datetime] = None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# get_current_user defined locally for auth endpoints still in server.py


# Health check endpoint for Docker/Kubernetes
@api_router.get("/health")
async def health_check():
    """Health check endpoint for monitoring and container orchestration."""
    try:
        # Check database connectivity
        await db.command("ping")
        return {
            "status": "healthy",
            "service": "arivu-backend",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


async def get_current_user(request: Request):
    """Dependency function to get current authenticated user info from cookies"""
    token = request.cookies.get("access_token")
    if not token:
        # Fallback to Authorization header for backwards compatibility
        auth_header = request.headers.get("Authorization", "")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Verify this is an access token
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        if user.get("banned"):
            raise HTTPException(status_code=403, detail="Account has been suspended")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def send_invite_email(email: str, name: str, invite_token: str):
    """Send account setup invite email via Resend"""
    if not RESEND_API_KEY:
        logger.error("Cannot send invite email - RESEND_API_KEY not configured")
        return False

    setup_url = f"{APP_URL}/accept-invite?token={invite_token}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'DM Sans', Arial, sans-serif; background: #F7F7F7; padding: 40px 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #fff; border: 2px solid #0F0F0F; padding: 40px; }}
            h1 {{ font-family: 'Bebas Neue', Arial, sans-serif; font-size: 28px; letter-spacing: 2px; text-transform: uppercase; margin: 0 0 20px 0; }}
            p {{ color: #333; line-height: 1.6; margin: 0 0 20px 0; }}
            .button {{ display: inline-block; background: #F97316; color: #fff; text-decoration: none; padding: 14px 28px; border: 2px solid #0F0F0F; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 2px solid #0F0F0F; font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>YOU'RE INVITED TO ARIVU</h1>
            <p>Hi {name},</p>
            <p>You've been invited to join Arivu - your AI-powered second brain. Click the button below to set up your password and get started.</p>
            <p><a href="{setup_url}" class="button">SET UP YOUR ACCOUNT</a></p>
            <p>This link will expire in 7 days.</p>
            <p>If you weren't expecting this, you can safely ignore this email.</p>
            <div class="footer">ARIVU - YOUR AI-POWERED SECOND BRAIN</div>
        </div>
    </body>
    </html>
    """

    try:
        params = {
            "from": RESEND_FROM_EMAIL,
            "to": [email],
            "subject": "You're Invited to Arivu",
            "html": html_content,
        }
        resend.Emails.send(params)
        logger.info(f"Invite email sent to {email}")
        return True
    except Exception as e:
        logger.exception(f"Failed to send invite email")
        return False


class AcceptInviteRequest(BaseModel):
    token: str
    password: str


@api_router.post("/auth/accept-invite")
async def accept_invite(request: Request, accept: AcceptInviteRequest):
    """Accept invite and set password"""
    token_doc = await db.invite_tokens.find_one({"token": accept.token})
    if not token_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired invite link")

    expires_at = datetime.fromisoformat(token_doc["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await db.invite_tokens.delete_one({"token": accept.token})
        raise HTTPException(status_code=400, detail="Invite link has expired. Please ask the admin to resend your invite.")

    user = await db.users.find_one({"id": token_doc["user_id"]})
    if not user:
        raise HTTPException(status_code=400, detail="User account not found")

    if not user.get("invite_pending"):
        raise HTTPException(status_code=400, detail="Account has already been set up")

    is_valid, error_msg = validate_password_strength(accept.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    new_hash = pwd_context.hash(accept.password)
    await db.users.update_one(
        {"id": token_doc["user_id"]},
        {"$set": {
            "password_hash": new_hash,
            "invite_pending": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    await db.invite_tokens.delete_one({"token": accept.token})

    logger.info(f"Invite accepted, password set for user: {token_doc['user_id']}")
    return {"message": "Account set up successfully. You can now log in."}


# ============================================
# X (Twitter) Integration Endpoints
# ============================================


async def refresh_x_token(user_id: str) -> Optional[dict]:
    """Refresh expired X access token using stored refresh_token."""
    connection = await db.x_connections.find_one({"user_id": user_id})
    if not connection or not connection.get("refresh_token_enc"):
        return None

    try:
        refresh_token = decrypt_token(connection["refresh_token_enc"])
        async with httpx.AsyncClient() as client_http:
            response = await client_http.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": X_CLIENT_ID,
                },
                auth=(X_CLIENT_ID, X_CLIENT_SECRET),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if response.status_code != 200:
            logger.error(f"X token refresh failed: {response.text}")
            await db.x_connections.update_one(
                {"user_id": user_id},
                {"$set": {"sync_status": "auth_expired"}},
            )
            return None

        data = response.json()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 7200))
        await db.x_connections.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "access_token_enc": encrypt_token(data["access_token"]),
                    "refresh_token_enc": encrypt_token(data["refresh_token"]),
                    "token_expires_at": expires_at.isoformat(),
                    "sync_status": "idle",
                }
            },
        )
        return data
    except Exception as e:
        logger.exception(f"Error refreshing X token for user {user_id}")
        return None


async def x_api_request(user_id: str, method: str, url: str, **kwargs) -> httpx.Response:
    """Make an authenticated X API request with auto-refresh on token expiry."""
    connection = await db.x_connections.find_one({"user_id": user_id})
    if not connection:
        raise HTTPException(status_code=404, detail="X account not connected")

    # Check if token is expired
    expires_at = connection.get("token_expires_at")
    if expires_at:
        exp_dt = datetime.fromisoformat(expires_at)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= exp_dt - timedelta(minutes=5):
            refreshed = await refresh_x_token(user_id)
            if not refreshed:
                raise HTTPException(status_code=401, detail="X authentication expired. Please reconnect.")
            connection = await db.x_connections.find_one({"user_id": user_id})

    access_token = decrypt_token(connection["access_token_enc"])
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {access_token}"

    async with httpx.AsyncClient() as client_http:
        response = await client_http.request(method, url, headers=headers, **kwargs)

    # Handle 401 with one retry after refresh
    if response.status_code == 401:
        refreshed = await refresh_x_token(user_id)
        if not refreshed:
            raise HTTPException(status_code=401, detail="X authentication expired. Please reconnect.")
        connection = await db.x_connections.find_one({"user_id": user_id})
        access_token = decrypt_token(connection["access_token_enc"])
        headers["Authorization"] = f"Bearer {access_token}"
        async with httpx.AsyncClient() as client_http:
            response = await client_http.request(method, url, headers=headers, **kwargs)

    # Handle rate limiting
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "60")
        raise HTTPException(status_code=429, detail=f"X API rate limited. Retry after {retry_after}s.")

    return response


def require_x_enabled():
    if not X_INTEGRATION_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")


@api_router.get("/auth/x/enabled")
async def x_enabled():
    """Public endpoint: is X integration available?"""
    return {"enabled": X_INTEGRATION_ENABLED}


@api_router.get("/auth/x/connect")
async def x_connect(current_user: dict = Depends(get_current_user)):
    """Generate X OAuth authorization URL with PKCE."""
    require_x_enabled()
    if not X_CLIENT_ID:
        raise HTTPException(status_code=503, detail="X integration not configured")

    # Generate PKCE code verifier and challenge
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")

    # Generate state with user_id for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store PKCE state in Redis (10 min TTL)
    r = await get_redis()
    state_data = f"{current_user['id']}:{code_verifier}"
    await r.setex(f"x_oauth_state:{state}", 600, state_data)

    scopes = "bookmark.read tweet.read users.read offline.access"
    auth_url = build_x_oauth_url(
        client_id=X_CLIENT_ID,
        redirect_uri=X_REDIRECT_URI,
        state=state,
        code_challenge=code_challenge,
        scopes=scopes,
    )

    return {"auth_url": auth_url}


class XCallbackRequest(BaseModel):
    code: str
    state: str


@api_router.post("/auth/x/callback")
async def x_callback(
    callback: XCallbackRequest,
    current_user: dict = Depends(get_current_user),
):
    """Exchange OAuth code for tokens, store encrypted connection."""
    require_x_enabled()
    if not X_CLIENT_ID:
        raise HTTPException(status_code=503, detail="X integration not configured")

    # Validate state from Redis
    r = await get_redis()
    state_data = await r.get(f"x_oauth_state:{callback.state}")
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        stored_user_id, code_verifier = state_data.split(":", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid OAuth state format")
    if stored_user_id != current_user["id"]:
        raise HTTPException(status_code=400, detail="OAuth state mismatch")

    # Clean up used state
    await r.delete(f"x_oauth_state:{callback.state}")

    # Exchange code for tokens (Confidential Client auth)
    async with httpx.AsyncClient() as client_http:
        token_response = await client_http.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": callback.code,
                "redirect_uri": X_REDIRECT_URI,
                "code_verifier": code_verifier,
                "client_id": X_CLIENT_ID,
            },
            auth=(X_CLIENT_ID, X_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if token_response.status_code != 200:
        logger.error(f"X token exchange failed: {token_response.text}")
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

    token_data = token_response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        logger.error(f"X token response missing access_token: {token_data.keys()}")
        raise HTTPException(status_code=502, detail="X API returned invalid token response")
    refresh_token = token_data.get("refresh_token")

    # Fetch X user profile
    async with httpx.AsyncClient() as client_http:
        profile_response = await client_http.get(
            "https://api.twitter.com/2/users/me",
            params={"user.fields": "profile_image_url,name,username"},
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if profile_response.status_code != 200:
        logger.error(f"X profile fetch failed: {profile_response.text}")
        raise HTTPException(status_code=400, detail="Failed to fetch X profile")

    profile_data = profile_response.json().get("data", {})
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 7200))

    connection_doc = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "x_user_id": profile_data.get("id"),
        "x_username": profile_data.get("username"),
        "x_name": profile_data.get("name"),
        "x_profile_image": profile_data.get("profile_image_url"),
        "access_token_enc": encrypt_token(access_token),
        "refresh_token_enc": encrypt_token(refresh_token) if refresh_token else None,
        "token_expires_at": expires_at.isoformat(),
        "scopes": token_data.get("scope", "").split(),
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "last_sync_at": None,
        "sync_status": "idle",
        "total_synced": 0,
        "next_cursor": None,
    }

    # Upsert: replace existing connection for this user
    await db.x_connections.replace_one(
        {"user_id": current_user["id"]},
        connection_doc,
        upsert=True,
    )

    logger.info(f"X account connected: @{profile_data.get('username')} for user {current_user['id']}")
    return {
        "connected": True,
        "x_username": profile_data.get("username"),
        "x_name": profile_data.get("name"),
        "x_profile_image": profile_data.get("profile_image_url"),
    }


@api_router.post("/auth/x/disconnect")
async def x_disconnect(current_user: dict = Depends(get_current_user)):
    """Disconnect X account: revoke token (best-effort) and delete connection."""
    require_x_enabled()
    connection = await db.x_connections.find_one({"user_id": current_user["id"]})
    if not connection:
        raise HTTPException(status_code=404, detail="X account not connected")

    # Best-effort token revocation
    try:
        access_token = decrypt_token(connection["access_token_enc"])
        async with httpx.AsyncClient() as client_http:
            await client_http.post(
                "https://api.twitter.com/2/oauth2/revoke",
                data={"token": access_token, "client_id": X_CLIENT_ID},
                auth=(X_CLIENT_ID, X_CLIENT_SECRET),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except Exception as e:
        logger.warning(f"X token revocation failed (best-effort): {e}")

    await db.x_connections.delete_one({"user_id": current_user["id"]})
    logger.info(f"X account disconnected for user {current_user['id']}")
    return {"disconnected": True}


@api_router.get("/auth/x/status")
async def x_status(current_user: dict = Depends(get_current_user)):
    """Get X connection status (never returns encrypted tokens)."""
    require_x_enabled()
    connection = await db.x_connections.find_one(
        {"user_id": current_user["id"]},
        {"_id": 0, "access_token_enc": 0, "refresh_token_enc": 0},
    )
    if not connection:
        return {"connected": False}

    return {
        "connected": True,
        "x_username": connection.get("x_username"),
        "x_name": connection.get("x_name"),
        "x_profile_image": connection.get("x_profile_image"),
        "connected_at": connection.get("connected_at"),
        "last_sync_at": connection.get("last_sync_at"),
        "sync_status": connection.get("sync_status", "idle"),
        "total_synced": connection.get("total_synced", 0),
    }


@api_router.post("/auth/x/sync")
@limiter.limit("5/minute")
async def x_sync(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Sync X bookmarks: fetch, deduplicate, store, and trigger AI processing."""
    require_x_enabled()
    if not X_CLIENT_ID:
        raise HTTPException(status_code=503, detail="X integration not configured")

    connection = await db.x_connections.find_one({"user_id": current_user["id"]})
    if not connection:
        raise HTTPException(status_code=404, detail="X account not connected")

    # Concurrency guard
    if connection.get("sync_status") == "syncing":
        raise HTTPException(status_code=409, detail="Sync already in progress")

    await db.x_connections.update_one(
        {"user_id": current_user["id"]},
        {"$set": {"sync_status": "syncing"}},
    )

    try:
        # Fetch X bookmarks with pagination (resume from saved cursor if present)
        x_user_id = connection.get("x_user_id")
        if not x_user_id:
            raise HTTPException(status_code=400, detail="X user ID not found. Please reconnect your X account.")

        all_tweets = []
        all_users = {}
        pagination_token = connection.get("next_cursor")
        pages_fetched = 0

        while True:
            if X_MAX_BOOKMARK_PAGES and pages_fetched >= X_MAX_BOOKMARK_PAGES:
                break
            params = {
                "max_results": 100,
                "tweet.fields": "created_at,public_metrics,entities",
                "expansions": "author_id",
                "user.fields": "username,name,profile_image_url",
            }
            if pagination_token:
                params["pagination_token"] = pagination_token

            response = await x_api_request(
                current_user["id"],
                "GET",
                f"https://api.twitter.com/2/users/{x_user_id}/bookmarks",
                params=params,
            )

            if response.status_code != 200:
                logger.error(f"X bookmarks fetch failed: {response.status_code} {response.text}")
                await db.x_connections.update_one(
                    {"user_id": current_user["id"]},
                    {"$set": {"sync_status": "error"}},
                )
                raise HTTPException(status_code=502, detail="Failed to fetch X bookmarks")

            data = response.json()
            meta = data.get("meta", {})
            tweets = data.get("data", [])
            logger.info(
                f"X sync page {pages_fetched + 1}: got {len(tweets)} tweets, "
                f"meta={meta}, "
                f"response_keys={list(data.keys())}, "
                f"errors={data.get('errors', 'none')}"
            )
            if not tweets:
                break

            all_tweets.extend(tweets)
            pages_fetched += 1

            # Build authors map from includes
            for user in data.get("includes", {}).get("users", []):
                all_users[user["id"]] = user

            # Total tweet cap — stop early if we have enough.
            # To remove this limit: set X_MAX_BOOKMARKS=0 in .env or delete this block.
            if X_MAX_BOOKMARKS and len(all_tweets) >= X_MAX_BOOKMARKS:
                all_tweets = all_tweets[:X_MAX_BOOKMARKS]
                logger.info(f"X sync capped at {X_MAX_BOOKMARKS} bookmarks")
                break

            # Check for next page
            pagination_token = data.get("meta", {}).get("next_token")
            if not pagination_token:
                break

        if not all_tweets:
            await db.x_connections.update_one(
                {"user_id": current_user["id"]},
                {
                    "$set": {
                        "sync_status": "idle",
                        "last_sync_at": datetime.now(timezone.utc).isoformat(),
                        "next_cursor": None,
                    }
                },
            )
            return {"total_fetched": 0, "new_bookmarks": 0, "duplicates_skipped": 0, "sync_status": "idle"}

        # Get existing tweet IDs and URLs for dedup
        existing_tweet_ids = set()
        existing_urls = set()
        existing_cursor = db.bookmarks.find(
            {"user_id": current_user["id"], "x_tweet_id": {"$exists": True, "$ne": None}},
            {"x_tweet_id": 1, "url": 1},
        )
        async for doc in existing_cursor:
            existing_tweet_ids.add(doc.get("x_tweet_id"))
            normalized = normalize_url_for_dedup(doc.get("url") or "")
            if normalized:
                existing_urls.add(normalized)

        # Also get existing web bookmark URLs for cross-source dedup
        web_urls_cursor = db.bookmarks.find(
            {"user_id": current_user["id"], "x_tweet_id": None},
            {"url": 1},
        )
        async for doc in web_urls_cursor:
            normalized = normalize_url_for_dedup(doc.get("url") or "")
            if normalized:
                existing_urls.add(normalized)

        new_bookmarks = []
        duplicates_skipped = 0

        for tweet in all_tweets:
            tweet_id = tweet["id"]
            if tweet_id in existing_tweet_ids:
                duplicates_skipped += 1
                continue

            author = all_users.get(tweet.get("author_id"), {})
            tweet_url = f"https://x.com/{author.get('username', 'i')}/status/{tweet_id}"

            # Smart URL mapping: if tweet contains external URL, use it
            bookmark_url = tweet_url
            entities = tweet.get("entities", {})
            external_urls = entities.get("urls", [])
            for url_entity in external_urls:
                expanded = url_entity.get("expanded_url", "")
                parsed = urlparse(expanded)
                if parsed.netloc and "x.com" not in parsed.netloc and "twitter.com" not in parsed.netloc:
                    bookmark_url = expanded
                    break

            bookmark_url_normalized = normalize_url_for_dedup(bookmark_url)
            if bookmark_url_normalized and bookmark_url_normalized in existing_urls:
                duplicates_skipped += 1
                continue

            metrics = tweet.get("public_metrics", {})
            tweet_text = tweet.get("text", "")

            bookmark_doc = {
                "id": str(uuid.uuid4()),
                "user_id": current_user["id"],
                "url": bookmark_url,
                "title": tweet_text[:100] + ("..." if len(tweet_text) > 100 else ""),
                "description": tweet_text,
                "domain": urlparse(bookmark_url).netloc,
                "text_content": tweet_text,
                "read_status": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "source": "x",
                "x_tweet_id": tweet_id,
                "x_author_username": author.get("username"),
                "x_author_name": author.get("name"),
                "x_tweet_url": tweet_url,
                "x_metrics": {
                    "retweet_count": metrics.get("retweet_count", 0),
                    "like_count": metrics.get("like_count", 0),
                    "reply_count": metrics.get("reply_count", 0),
                    "quote_count": metrics.get("quote_count", 0),
                },
            }

            new_bookmarks.append(bookmark_doc)
            existing_tweet_ids.add(tweet_id)
            if bookmark_url_normalized:
                existing_urls.add(bookmark_url_normalized)

        # Bulk insert new bookmarks
        if new_bookmarks:
            await db.bookmarks.insert_many(new_bookmarks)

            # Create pending AI summary docs
            ai_docs = [
                {
                    "id": str(uuid.uuid4()),
                    "bookmark_id": b["id"],
                    "processing_status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                for b in new_bookmarks
            ]
            await db.ai_summaries.insert_many(ai_docs)

            # Queue background AI processing
            bookmark_ids = [b["id"] for b in new_bookmarks]
            background_tasks.add_task(process_x_bookmarks_batch, bookmark_ids, current_user["id"])

        # Update connection stats
        has_more = pagination_token is not None
        total_synced = connection.get("total_synced", 0) + len(new_bookmarks)
        await db.x_connections.update_one(
            {"user_id": current_user["id"]},
            {
                "$set": {
                    "sync_status": "idle",
                    "last_sync_at": datetime.now(timezone.utc).isoformat(),
                    "total_synced": total_synced,
                    "next_cursor": pagination_token if has_more else None,
                }
            },
        )

        return {
            "total_fetched": len(all_tweets),
            "new_bookmarks": len(new_bookmarks),
            "duplicates_skipped": duplicates_skipped,
            "sync_status": "idle",
            "has_more": has_more,
        }

    except HTTPException as exc:
        await db.x_connections.update_one(
            {"user_id": current_user["id"]},
            {"$set": {"sync_status": map_x_sync_error_status(exc.status_code)}},
        )
        raise
    except Exception as e:
        logger.exception(f"Error during X sync for user {current_user['id']}")
        await db.x_connections.update_one(
            {"user_id": current_user["id"]},
            {"$set": {"sync_status": "error"}},
        )
        raise HTTPException(status_code=500, detail="Sync failed unexpectedly")


async def process_x_bookmarks_batch(bookmark_ids: list, user_id: str):
    """Background: process X bookmarks through AI pipeline (content fetch + summaries + embeddings)."""
    for bookmark_id in bookmark_ids:
        try:
            bookmark = await db.bookmarks.find_one({"id": bookmark_id, "user_id": user_id})
            if not bookmark:
                continue

            url = bookmark.get("url", "")
            tweet_url = bookmark.get("x_tweet_url", "")

            # If URL is external (not the tweet itself), fetch its content
            if url != tweet_url and "x.com" not in url and "twitter.com" not in url:
                try:
                    content = await fetch_webpage_content(url)
                    await db.bookmarks.update_one(
                        {"id": bookmark_id},
                        {
                            "$set": {
                                "title": content.get("title") or bookmark.get("title"),
                                "description": content.get("description") or bookmark.get("description"),
                                "favicon": content.get("favicon"),
                                "thumbnail": content.get("thumbnail"),
                                "html_content": content.get("html_content"),
                                "text_content": content.get("text_content") or bookmark.get("text_content"),
                                "domain": content.get("domain") or bookmark.get("domain"),
                                "reading_time": calculate_reading_time(content.get("text_content", "")),
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                            }
                        },
                    )
                    # Use fetched content for AI if available
                    text_content = content.get("text_content") or bookmark.get("text_content", "")
                    title = content.get("title") or bookmark.get("title", "")
                    description = content.get("description") or bookmark.get("description", "")
                except Exception as e:
                    logger.warning(f"Failed to fetch external content for X bookmark {bookmark_id}: {e}")
                    text_content = bookmark.get("text_content", "")
                    title = bookmark.get("title", "")
                    description = bookmark.get("description", "")
            else:
                text_content = bookmark.get("text_content", "")
                title = bookmark.get("title", "")
                description = bookmark.get("description", "")

            # Generate AI summaries (lower threshold for tweets)
            if text_content and len(text_content.strip()) >= 20:
                await generate_ai_summaries(text_content, bookmark_id)

                # Generate embedding for semantic search
                if len(text_content.strip()) >= 50:
                    embedding = await generate_embedding(text_content, title, description)
                    ai_summary = await db.ai_summaries.find_one(
                        {"bookmark_id": bookmark_id}, {"_id": 0}
                    )
                    entities, concepts = await extract_entities_and_concepts(text_content, ai_summary)

                    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
                    if embedding:
                        update_data["embedding"] = embedding
                        update_data["embedding_model"] = "text-embedding-004"
                    if entities:
                        update_data["entities"] = entities
                    if concepts:
                        update_data["concepts"] = concepts
                    await db.bookmarks.update_one({"id": bookmark_id}, {"$set": update_data})
            else:
                # Mark as completed even with insufficient content
                await db.ai_summaries.update_one(
                    {"bookmark_id": bookmark_id},
                    {"$set": {"processing_status": "completed", "one_sentence": text_content[:200]}},
                )

            logger.info(f"Processed X bookmark: {bookmark_id}")
        except Exception as e:
            logger.exception(f"Error processing X bookmark {bookmark_id}")
            await db.ai_summaries.update_one(
                {"bookmark_id": bookmark_id},
                {"$set": {"processing_status": "failed"}},
            )


# Request size limit middleware
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request, call_next):
        # Check Content-Length header if present
        content_length = request.headers.get("content-length")
        if content_length:
            content_length = int(content_length)
            if content_length > self.max_size:
                logger.warning(
                    f"Request rejected: size {content_length} exceeds limit {self.max_size}"
                )
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body too large. Maximum size is {self.max_size / (1024 * 1024):.1f}MB",
                )

        response = await call_next(request)
        return response


# Request ID tracking middleware
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Add to logger context for this request
        logger.info(f"Request {request_id}: {request.method} {request.url.path}")

        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


# --- Admin Pydantic Models ---

class AdminUserInvite(BaseModel):
    email: EmailStr
    name: str


class AdminPasswordReset(BaseModel):
    new_password: str


# --- Admin Auth Dependency ---

async def get_admin_user(request: Request):
    user = await get_current_user(request)
    if user["email"].lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# --- Admin Endpoints ---

@api_router.get("/admin/overview")
async def admin_overview(admin: dict = Depends(get_admin_user)):
    logger.info(f"Admin action: overview requested by {admin['email']}")
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    total_users = await db.users.count_documents({})
    total_bookmarks = await db.bookmarks.count_documents({})
    total_collections = await db.collections.count_documents({})
    total_ai_summaries = await db.ai_summaries.count_documents({})

    bookmarks_today = await db.bookmarks.count_documents({"created_at": {"$gte": today_start}})
    bookmarks_week = await db.bookmarks.count_documents({"created_at": {"$gte": week_start}})
    bookmarks_month = await db.bookmarks.count_documents({"created_at": {"$gte": month_start}})

    users_today = await db.users.count_documents({"created_at": {"$gte": today_start}})
    users_week = await db.users.count_documents({"created_at": {"$gte": week_start}})
    users_month = await db.users.count_documents({"created_at": {"$gte": month_start}})

    avg_bookmarks = total_bookmarks / total_users if total_users > 0 else 0

    try:
        db_stats = await db.command("dbStats")
        mongo_stats = {
            "data_size": db_stats.get("dataSize", 0),
            "storage_size": db_stats.get("storageSize", 0),
            "index_size": db_stats.get("indexSize", 0),
            "collections": db_stats.get("collections", 0),
            "objects": db_stats.get("objects", 0),
        }
    except Exception as e:
        logger.exception("Failed to get dbStats")
        mongo_stats = {"error": str(e)}

    uptime_seconds = (now - SERVER_START_TIME).total_seconds()

    return {
        "users": {
            "total": total_users,
            "today": users_today,
            "this_week": users_week,
            "this_month": users_month,
        },
        "bookmarks": {
            "total": total_bookmarks,
            "today": bookmarks_today,
            "this_week": bookmarks_week,
            "this_month": bookmarks_month,
            "avg_per_user": round(avg_bookmarks, 2),
        },
        "collections": {"total": total_collections},
        "ai_summaries": {"total": total_ai_summaries},
        "mongodb": mongo_stats,
        "server": {
            "uptime_seconds": round(uptime_seconds),
            "started_at": SERVER_START_TIME.isoformat(),
        },
    }


@api_router.get("/admin/api-usage")
async def admin_api_usage(admin: dict = Depends(get_admin_user)):
    logger.info(f"Admin action: api-usage requested by {admin['email']}")
    current_rpm = len(gemini_rate_limiter.rpm_bucket)
    current_tpm = sum(t for _, t in gemini_rate_limiter.tpm_bucket)
    rpm_util = (current_rpm / gemini_rate_limiter.max_rpm * 100) if gemini_rate_limiter.max_rpm else 0
    tpm_util = (current_tpm / gemini_rate_limiter.max_tpm * 100) if gemini_rate_limiter.max_tpm else 0
    daily_util = (gemini_rate_limiter.total_requests_today / gemini_rate_limiter.max_daily * 100) if gemini_rate_limiter.max_daily else 0

    return {
        "requests_today": gemini_rate_limiter.total_requests_today,
        "tokens_today": gemini_rate_limiter.total_tokens_today,
        "current_rpm": current_rpm,
        "current_tpm": current_tpm,
        "rpm_utilization_pct": round(rpm_util, 2),
        "tpm_utilization_pct": round(tpm_util, 2),
        "daily_utilization_pct": round(daily_util, 2),
        "limits": {
            "max_rpm": gemini_rate_limiter.max_rpm,
            "max_tpm": gemini_rate_limiter.max_tpm,
            "max_daily": gemini_rate_limiter.max_daily,
        },
        "current_date": gemini_rate_limiter.current_date,
    }


@api_router.get("/admin/users")
async def admin_list_users(
    sort: str = "created_at",
    order: str = "desc",
    admin: dict = Depends(get_admin_user),
):
    logger.info(f"Admin action: list users by {admin['email']}")
    users = await db.users.find(
        {}, {"_id": 0, "password_hash": 0}
    ).to_list(None)

    user_ids = [u["id"] for u in users]

    bookmark_pipeline = [
        {"$match": {"user_id": {"$in": user_ids}}},
        {"$group": {
            "_id": "$user_id",
            "count": {"$sum": 1},
            "last_created": {"$max": "$created_at"},
        }},
    ]
    bookmark_stats = {
        doc["_id"]: doc
        async for doc in db.bookmarks.aggregate(bookmark_pipeline)
    }

    collection_pipeline = [
        {"$match": {"user_id": {"$in": user_ids}}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
    ]
    collection_stats = {
        doc["_id"]: doc["count"]
        async for doc in db.collections.aggregate(collection_pipeline)
    }

    enriched = []
    for u in users:
        uid = u["id"]
        bstats = bookmark_stats.get(uid, {})
        u["bookmark_count"] = bstats.get("count", 0)
        u["collection_count"] = collection_stats.get(uid, 0)
        u["last_bookmark_at"] = bstats.get("last_created")
        u["banned"] = u.get("banned", False)
        u["is_admin"] = u["email"].lower() in ADMIN_EMAILS
        enriched.append(u)

    sort_key_map = {
        "bookmarks": "bookmark_count",
        "created_at": "created_at",
        "name": "name",
        "email": "email",
    }
    key = sort_key_map.get(sort, "created_at")
    reverse = order != "asc"
    enriched.sort(key=lambda x: (x.get(key) or ""), reverse=reverse)

    return enriched


@api_router.get("/admin/users/{user_id}")
async def admin_get_user(user_id: str, admin: dict = Depends(get_admin_user)):
    logger.info(f"Admin action: get user {user_id} by {admin['email']}")
    user = await db.users.find_one(
        {"id": user_id}, {"_id": 0, "password_hash": 0}
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    bookmark_count = await db.bookmarks.count_documents({"user_id": user_id})
    collection_count = await db.collections.count_documents({"user_id": user_id})
    recent_bookmarks = await db.bookmarks.find(
        {"user_id": user_id},
        {"_id": 0, "id": 1, "title": 1, "url": 1, "domain": 1, "created_at": 1},
    ).sort("created_at", -1).limit(10).to_list(10)

    user["bookmark_count"] = bookmark_count
    user["collection_count"] = collection_count
    user["recent_bookmarks"] = recent_bookmarks
    user["banned"] = user.get("banned", False)
    user["is_admin"] = user["email"].lower() in ADMIN_EMAILS

    return user


@api_router.post("/admin/users/invite")
async def admin_invite_user(
    invite: AdminUserInvite, admin: dict = Depends(get_admin_user)
):
    logger.info(f"Admin action: invite user {invite.email} by {admin['email']}")

    existing = await db.users.find_one(
        {"email": invite.email}, {"_id": 0, "id": 1}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": invite.email,
        "name": invite.name,
        "password_hash": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "invite_pending": True,
    }
    await db.users.insert_one(user)

    invite_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.invite_tokens.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "token": invite_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    await send_invite_email(invite.email, invite.name, invite_token)

    logger.info(f"Admin invited new user: {user_id} ({invite.email})")

    return {
        "id": user_id,
        "email": invite.email,
        "name": invite.name,
        "created_at": user["created_at"],
        "invite_sent": True,
    }


@api_router.post("/admin/users/{user_id}/ban")
async def admin_ban_user(user_id: str, admin: dict = Depends(get_admin_user)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot ban yourself")

    user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.users.update_one(
        {"id": user_id},
        {"$set": {"banned": True, "banned_at": datetime.now(timezone.utc).isoformat()}},
    )
    logger.info(f"Admin action: user {user_id} banned by {admin['email']}")
    return {"status": "banned", "user_id": user_id}


@api_router.post("/admin/users/{user_id}/unban")
async def admin_unban_user(user_id: str, admin: dict = Depends(get_admin_user)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.users.update_one(
        {"id": user_id},
        {"$set": {"banned": False, "unbanned_at": datetime.now(timezone.utc).isoformat()}},
    )
    logger.info(f"Admin action: user {user_id} unbanned by {admin['email']}")
    return {"status": "unbanned", "user_id": user_id}


@api_router.post("/admin/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    body: AdminPasswordReset,
    admin: dict = Depends(get_admin_user),
):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    hashed = pwd_context.hash(body.new_password)
    await db.users.update_one({"id": user_id}, {"$set": {"password_hash": hashed}})
    logger.info(f"Admin action: password reset for user {user_id} by {admin['email']}")
    return {"status": "password_reset", "user_id": user_id}


@api_router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin: dict = Depends(get_admin_user)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    del_user = await db.users.delete_one({"id": user_id})
    del_bookmarks = await db.bookmarks.delete_many({"user_id": user_id})
    del_summaries = await db.ai_summaries.delete_many({"user_id": user_id})
    del_collections = await db.collections.delete_many({"user_id": user_id})

    logger.info(
        f"Admin action: deleted user {user_id} and all data by {admin['email']}"
    )
    return {
        "status": "deleted",
        "user_id": user_id,
        "deleted_counts": {
            "users": del_user.deleted_count,
            "bookmarks": del_bookmarks.deleted_count,
            "ai_summaries": del_summaries.deleted_count,
            "collections": del_collections.deleted_count,
        },
    }


@api_router.get("/admin/system")
async def admin_system_health(admin: dict = Depends(get_admin_user)):
    logger.info(f"Admin action: system health by {admin['email']}")

    try:
        server_status = await db.command("serverStatus")
        mongo_info = {
            "connections": {
                "current": server_status.get("connections", {}).get("current"),
                "available": server_status.get("connections", {}).get("available"),
            },
            "opcounters": server_status.get("opcounters", {}),
            "mem": server_status.get("mem", {}),
            "uptime": server_status.get("uptime"),
        }
    except Exception as e:
        logger.exception("Failed to get serverStatus")
        mongo_info = {"error": str(e)}

    try:
        db_stats = await db.command("dbStats")
    except Exception as e:
        db_stats = {"error": str(e)}

    redis_info = None
    try:
        if redis_client is not None:
            info = await redis_client.info()
            redis_info = {
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
            }
    except Exception as e:
        redis_info = {"error": str(e)}

    collection_stats = {}
    for coll_name in ["users", "bookmarks", "ai_summaries", "collections"]:
        try:
            stats = await db.command("collStats", coll_name)
            collection_stats[coll_name] = {
                "count": stats.get("count", 0),
                "size": stats.get("size", 0),
                "storage_size": stats.get("storageSize", 0),
            }
        except Exception:
            count = await db[coll_name].count_documents({})
            collection_stats[coll_name] = {"count": count}

    try:
        import psutil
        process = psutil.Process()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        proc_mem = process.memory_info()
        system_stats = {
            "cpu_percent": cpu_percent,
            "memory_total": mem.total,
            "memory_available": mem.available,
            "memory_percent": mem.percent,
            "process_rss": proc_mem.rss,
        }
    except ImportError:
        system_stats = {
            "cpu_percent": None,
            "memory_total": None,
            "memory_available": None,
            "memory_percent": None,
            "process_rss": None,
        }

    return {
        "mongodb": {
            "connections_current": mongo_info.get("connections", {}).get("current") if isinstance(mongo_info, dict) and "error" not in mongo_info else None,
            "connections_available": mongo_info.get("connections", {}).get("available") if isinstance(mongo_info, dict) and "error" not in mongo_info else None,
            "uptime_seconds": mongo_info.get("uptime") if isinstance(mongo_info, dict) and "error" not in mongo_info else None,
            "opcounters": mongo_info.get("opcounters") if isinstance(mongo_info, dict) and "error" not in mongo_info else None,
            "mem": mongo_info.get("mem") if isinstance(mongo_info, dict) and "error" not in mongo_info else None,
        },
        "redis": redis_info,
        "python_version": sys.version.split()[0],
        "environment": "production" if IS_PRODUCTION else "development",
        "collections": collection_stats,
        "db_stats": {
            "dataSize": db_stats.get("dataSize", 0) if isinstance(db_stats, dict) and "error" not in db_stats else 0,
            "storageSize": db_stats.get("storageSize", 0) if isinstance(db_stats, dict) and "error" not in db_stats else 0,
            "indexSize": db_stats.get("indexSize", 0) if isinstance(db_stats, dict) and "error" not in db_stats else 0,
        },
        "system": system_stats,
    }


@api_router.get("/admin/activity")
async def admin_activity(admin: dict = Depends(get_admin_user)):
    logger.info(f"Admin action: activity feed by {admin['email']}")

    recent_bookmarks = await db.bookmarks.find(
        {},
        {"_id": 0, "user_id": 1, "title": 1, "url": 1, "domain": 1, "created_at": 1},
    ).sort("created_at", -1).limit(50).to_list(50)

    bm_user_ids = list({b["user_id"] for b in recent_bookmarks})
    user_emails = {}
    if bm_user_ids:
        users = await db.users.find(
            {"id": {"$in": bm_user_ids}},
            {"_id": 0, "id": 1, "email": 1},
        ).to_list(None)
        user_emails = {u["id"]: u["email"] for u in users}

    for b in recent_bookmarks:
        b["user_email"] = user_emails.get(b.get("user_id"), "unknown")

    recent_users = await db.users.find(
        {},
        {"_id": 0, "id": 1, "email": 1, "name": 1, "created_at": 1},
    ).sort("created_at", -1).limit(10).to_list(10)

    return {
        "recent_bookmarks": recent_bookmarks,
        "recent_registrations": recent_users,
    }


@api_router.get("/admin/collections-stats")
async def admin_collections_stats(admin: dict = Depends(get_admin_user)):
    logger.info(f"Admin action: collections-stats by {admin['email']}")
    collection_names = await db.list_collection_names()
    stats = {}
    for name in collection_names:
        try:
            coll_stats = await db.command("collStats", name)
            stats[name] = {
                "count": coll_stats.get("count", 0),
                "size": coll_stats.get("size", 0),
                "storage_size": coll_stats.get("storageSize", 0),
                "index_size": coll_stats.get("totalIndexSize", 0),
                "avg_obj_size": coll_stats.get("avgObjSize", 0),
            }
        except Exception as e:
            count = await db[name].count_documents({})
            stats[name] = {"count": count, "error": str(e)}
    return stats


app.include_router(api_router)

# Add middleware (order matters - applied in reverse order)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)  # 10MB limit

# Validate CORS origins
cors_origins_env = os.environ.get("CORS_ORIGINS", "*")
if cors_origins_env == "*":
    logger.warning(
        "CORS_ORIGINS set to '*' - allowing all origins (not recommended for production)"
    )
    cors_origins = ["*"]
else:
    cors_origins = [
        origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
    ]
    if not cors_origins:
        logger.warning(
            "CORS_ORIGINS configured but empty - defaulting to allow all origins"
        )
        cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def create_x_indexes():
    """Create indexes for X bookmarks integration."""
    try:
        await db.bookmarks.create_index(
            [("user_id", 1), ("x_tweet_id", 1)],
            unique=True,
            partialFilterExpression={"x_tweet_id": {"$type": "string"}},
            name="idx_user_x_tweet_dedup",
        )
        await db.bookmarks.create_index(
            [("user_id", 1), ("source", 1), ("created_at", -1)],
            name="idx_user_source_date",
        )
        await db.x_connections.create_index(
            "user_id",
            unique=True,
            name="idx_x_connections_user",
        )
        logger.info("X integration indexes created successfully")
    except Exception as e:
        logger.warning(f"Index creation skipped (may already exist): {e}")


@app.on_event("startup")
async def migrate_bookmark_version_field():
    """Migrate existing bookmarks to include version field (REL-03)."""
    try:
        migrated = await db.bookmarks.update_many(
            {"version": {"$exists": False}},
            {"$set": {"version": 1}},
        )
        if migrated.modified_count > 0:
            logger.info(
                f"Migrated {migrated.modified_count} bookmarks to include version field"
            )
    except Exception as e:
        logger.warning(f"Version field migration skipped: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    close_core_db()
    client.close()
