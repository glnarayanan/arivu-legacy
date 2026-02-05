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
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr, HttpUrl, validator
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import asyncio
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from readability import Document
import html2text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import google.generativeai as genai
import ipaddress
import socket
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from collections import deque
import time
import random
from resurfacing import (
    calculate_resurfacing_score,
    get_resurfacing_reason,
    should_resurface,
)
from content_intelligence import (
    calculate_credibility_score,
    get_quality_label,
    get_quality_badges,
    check_duplicate_url,
)
from analytics import (
    calculate_reading_stats,
    get_topic_breakdown,
    get_reading_patterns,
    get_learning_insights,
)
import resend
import secrets

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")


# Enhanced Rate limiter for Gemini API with multi-dimensional tracking
class EnhancedGeminiRateLimiter:
    def __init__(
        self,
        max_rpm=500,  # 50% of 1000 RPM limit (conservative)
        max_tpm=500000,  # 50% of 1M tokens/minute
        max_daily=5000,  # 50% of 10K requests/day
    ):
        # Limits
        self.max_rpm = max_rpm
        self.max_tpm = max_tpm
        self.max_daily = max_daily

        # Current usage tracking (sliding windows)
        self.rpm_bucket = deque()  # (timestamp, 1)
        self.tpm_bucket = deque()  # (timestamp, token_count)

        # Daily tracking
        self.total_requests_today = 0
        self.total_tokens_today = 0
        self.current_date = datetime.now(timezone.utc).date().isoformat()

        # Thread safety
        self.lock = asyncio.Lock()

    async def acquire(self, estimated_tokens=1000):
        """
        Acquire permission to make API call with rate limiting

        Args:
            estimated_tokens: Estimated tokens for this request (default 1000)

        Returns:
            wait_time: How long we waited (for logging)
        """
        async with self.lock:
            now = time.time()
            today = datetime.now(timezone.utc).date().isoformat()

            # Reset daily counters if date changed
            if today != self.current_date:
                self.total_requests_today = 0
                self.total_tokens_today = 0
                self.current_date = today
                logger.info(f"Daily quota reset: new date {today}")

            # 1. Clean old entries (older than 1 minute)
            self._cleanup_buckets(now)

            # 2. Check current usage
            current_rpm = len(self.rpm_bucket)
            current_tpm = sum(tokens for _, tokens in self.tpm_bucket)
            current_daily = self.total_requests_today

            # 3. Calculate utilization percentages
            rpm_utilization = current_rpm / self.max_rpm if self.max_rpm > 0 else 0
            tpm_utilization = current_tpm / self.max_tpm if self.max_tpm > 0 else 0

            # 4. Determine wait time
            wait_time = 0

            # Dynamic throttling: slow down at 80% capacity
            if rpm_utilization >= 0.80 or tpm_utilization >= 0.80:
                # Wait a bit to smooth out traffic
                wait_time = 0.5
                logger.debug(
                    f"Dynamic throttling: RPM={rpm_utilization:.0%}, TPM={tpm_utilization:.0%}"
                )

            # Hard limit: must wait if at capacity
            if current_rpm >= self.max_rpm:
                oldest_request = self.rpm_bucket[0][0]
                wait_time = max(wait_time, 60 - (now - oldest_request) + 0.1)

            if current_tpm + estimated_tokens >= self.max_tpm:
                oldest_tokens = self.tpm_bucket[0][0]
                wait_time = max(wait_time, 60 - (now - oldest_tokens) + 0.1)

            # Check daily limit (hard stop)
            if current_daily >= self.max_daily:
                logger.error(
                    f"Daily Gemini API quota exceeded: {current_daily}/{self.max_daily}"
                )
                raise Exception(
                    "Daily Gemini API quota exceeded. Please try again tomorrow."
                )

            # 5. Wait if needed
            if wait_time > 0:
                logger.info(
                    f"Rate limiting: waiting {wait_time:.1f}s (RPM: {rpm_utilization:.0%}, TPM: {tpm_utilization:.0%}, Daily: {current_daily}/{self.max_daily})"
                )
                await asyncio.sleep(wait_time)
                return await self.acquire(estimated_tokens)  # Retry

            # 6. Record this request
            self.rpm_bucket.append((now, 1))
            self.tpm_bucket.append((now, estimated_tokens))
            self.total_requests_today += 1
            self.total_tokens_today += estimated_tokens

            return wait_time

    def _cleanup_buckets(self, now):
        """Remove entries older than 60 seconds"""
        cutoff = now - 60

        while self.rpm_bucket and self.rpm_bucket[0][0] < cutoff:
            self.rpm_bucket.popleft()

        while self.tpm_bucket and self.tpm_bucket[0][0] < cutoff:
            self.tpm_bucket.popleft()

    async def record_actual_tokens(self, actual_tokens):
        """Update token count with actual usage from API response"""
        async with self.lock:
            # Adjust token tracking based on actual response
            if self.tpm_bucket:
                last_timestamp, estimated = self.tpm_bucket[-1]
                self.tpm_bucket[-1] = (last_timestamp, actual_tokens)
                self.total_tokens_today += actual_tokens - estimated


gemini_rate_limiter = EnhancedGeminiRateLimiter(
    max_rpm=500,  # 50% of 1000 RPM (conservative buffer)
    max_tpm=500000,  # 50% of 1M tokens/min
    max_daily=5000,  # 50% of 10K requests/day
)

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
    maxIdleTimeMS=45000,  # Close idle connections after 45 seconds
    waitQueueTimeoutMS=10000,  # 10 second timeout waiting for connection from pool
    retryWrites=True,  # Enable retry for write operations
    retryReads=True,  # Enable retry for read operations
)
db_name = os.environ.get("DB_NAME", "arivu_db")
db = client[db_name]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Custom key function for user-based rate limiting
def get_user_identifier(request: Request) -> str:
    """Get user ID from auth token, fallback to IP if not authenticated"""
    try:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
    except Exception:
        pass
    # Fallback to IP-based rate limiting
    return f"ip:{get_remote_address(request)}"


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

# Resend email configuration
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "noreply@arivu.app")
APP_URL = os.environ.get("APP_URL", "https://arivu.app")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    logger.info("Resend email configured successfully")
else:
    logger.warning("RESEND_API_KEY not set - password reset emails will not work")


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


class UserSignup(BaseModel):
    email: EmailStr
    password: str
    name: str

    @validator("name")
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Name cannot be empty")
        if len(v) > 100:
            raise ValueError("Name too long (max 100 characters)")
        if not re.match(r"^[\w\s\-\.]+$", v):
            raise ValueError("Name contains invalid characters")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: Optional[str] = None  # Optional for cookie-based auth
    refresh_token: Optional[str] = None  # Optional for cookie-based auth
    token_type: str = "bearer"
    user: Optional[dict] = None  # Optional for cookie-based auth


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

    @validator("name")
    def validate_name(cls, v):
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("Name cannot be empty")
            if len(v) > 100:
                raise ValueError("Name too long (max 100 characters)")
            if not re.match(r"^[\w\s\-\.]+$", v):
                raise ValueError("Name contains invalid characters")
            return v.strip()
        return v


class AvatarUpload(BaseModel):
    avatar_data: str  # Base64 encoded image data


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


class Collection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    bookmark_ids: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CollectionCreate(BaseModel):
    name: str

    @validator("name")
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Collection name cannot be empty")
        if len(v) > 100:
            raise ValueError("Collection name too long (max 100 characters)")
        if not re.match(r"^[\w\s\-\.]+$", v):
            raise ValueError("Collection name contains invalid characters")
        return v.strip()


class AddToCollection(BaseModel):
    bookmark_id: str


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


# Removed old get_current_user - using get_current_user_info which reads from cookies


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


@api_router.post("/auth/signup", response_model=TokenResponse)
@limiter.limit("3/hour")  # Limit signups to prevent abuse
async def signup(request: Request, user_data: UserSignup):
    """Register a new user with password validation"""
    # SIGNUPS DISABLED: Only existing users can login
    # To re-enable signups, remove or comment out the following block
    logger.info(f"Signup attempt blocked (signups disabled): {user_data.email}")
    raise HTTPException(
        status_code=403,
        detail="Signups are currently disabled. Only existing users can log in.",
    )

    # Validate password strength
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        logger.info(f"Signup failed: weak password for email {user_data.email}")
        raise HTTPException(status_code=400, detail=error_msg)

    # Check if email already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        logger.info(f"Signup failed: email already registered {user_data.email}")
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    user = {
        "id": str(uuid.uuid4()),
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": pwd_context.hash(user_data.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)

    # Create tokens
    access_token = create_access_token(data={"sub": user["id"]})
    refresh_token = create_refresh_token(data={"sub": user["id"]})

    user_response = {"id": user["id"], "email": user["email"], "name": user["name"]}
    logger.info(f"User registered successfully: {user['id']}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_response,
    }


@api_router.post("/auth/login")
@limiter.limit("5/minute")  # Prevent brute force attacks
async def login(request: Request, login_data: UserLogin, response: Response):
    """Authenticate user and return tokens as HTTP-only cookies"""
    user = await db.users.find_one({"email": login_data.email})
    if not user or not pwd_context.verify(login_data.password, user["password_hash"]):
        logger.warning(f"Login failed: invalid credentials for {login_data.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create tokens
    access_token = create_access_token(data={"sub": user["id"]})
    refresh_token = create_refresh_token(data={"sub": user["id"]})

    user_response = {"id": user["id"], "email": user["email"], "name": user["name"]}
    logger.info(f"User logged in successfully: {user['id']}")

    # Set HTTP-only cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

    return {"token_type": "bearer", "user": user_response}


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
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@api_router.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info from cookies"""
    return current_user


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user by clearing cookies"""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")

    return {"message": "Logged out successfully"}


@api_router.post("/auth/refresh")
async def refresh_token_endpoint(request: Request):
    """Simple refresh endpoint - client's axios interceptor handles rotation"""
    # This endpoint is kept for backwards compatibility
    # The actual refresh logic is handled by client-side axios interceptor
    pass


# ============================================
# Password Reset Endpoints
# ============================================


async def send_password_reset_email(email: str, reset_token: str):
    """Send password reset email via Resend"""
    if not RESEND_API_KEY:
        logger.error("Cannot send password reset email - RESEND_API_KEY not configured")
        return False

    reset_url = f"{APP_URL}/reset-password?token={reset_token}"

    # Minimal brutalist email template
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
            <h1>RESET YOUR PASSWORD</h1>
            <p>You requested a password reset for your Arivu account. Click the button below to set a new password.</p>
            <p><a href="{reset_url}" class="button">RESET PASSWORD</a></p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this, you can safely ignore this email.</p>
            <div class="footer">ARIVU — YOUR AI-POWERED SECOND BRAIN</div>
        </div>
    </body>
    </html>
    """

    try:
        params = {
            "from": RESEND_FROM_EMAIL,
            "to": [email],
            "subject": "Reset Your Arivu Password",
            "html": html_content,
        }
        resend.Emails.send(params)
        logger.info(f"Password reset email sent to {email}")
        return True
    except Exception as e:
        logger.exception(f"Failed to send password reset email")
        return False


@api_router.post("/auth/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(request: Request, reset_request: PasswordResetRequest):
    """Request a password reset email"""
    email = reset_request.email.lower()

    # Always return success to prevent email enumeration attacks
    user = await db.users.find_one({"email": email})
    if not user:
        logger.info(f"Password reset requested for non-existent email: {email}")
        return {"message": "If an account exists with this email, you will receive a reset link."}

    # Generate secure reset token
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRE_HOURS)

    # Store token in database
    await db.password_reset_tokens.delete_many({"user_id": user["id"]})  # Remove old tokens
    await db.password_reset_tokens.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "token": reset_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Send email
    await send_password_reset_email(email, reset_token)

    logger.info(f"Password reset token generated for user: {user['id']}")
    return {"message": "If an account exists with this email, you will receive a reset link."}


@api_router.post("/auth/reset-password")
@limiter.limit("5/hour")
async def reset_password(request: Request, reset_confirm: PasswordResetConfirm):
    """Reset password using token from email"""
    # Find valid token
    token_doc = await db.password_reset_tokens.find_one({"token": reset_confirm.token})
    if not token_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # Check expiry
    expires_at = datetime.fromisoformat(token_doc["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await db.password_reset_tokens.delete_one({"token": reset_confirm.token})
        raise HTTPException(status_code=400, detail="Reset token has expired")

    # Validate new password strength
    is_valid, error_msg = validate_password_strength(reset_confirm.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Update password
    new_hash = pwd_context.hash(reset_confirm.new_password)
    await db.users.update_one(
        {"id": token_doc["user_id"]},
        {"$set": {"password_hash": new_hash, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    # Delete used token
    await db.password_reset_tokens.delete_one({"token": reset_confirm.token})

    logger.info(f"Password reset completed for user: {token_doc['user_id']}")
    return {"message": "Password reset successfully. You can now log in with your new password."}


@api_router.post("/auth/change-password")
async def change_password(
    change_request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Change password while logged in (requires current password)"""
    # Verify current password
    user = await db.users.find_one({"id": current_user["id"]})
    if not user or not pwd_context.verify(change_request.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Validate new password strength
    is_valid, error_msg = validate_password_strength(change_request.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Update password
    new_hash = pwd_context.hash(change_request.new_password)
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"password_hash": new_hash, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    logger.info(f"Password changed for user: {current_user['id']}")
    return {"message": "Password changed successfully"}


# ============================================
# User Profile Endpoints
# ============================================


@api_router.get("/user/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    user = await db.users.find_one(
        {"id": current_user["id"]},
        {"_id": 0, "password_hash": 0}
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@api_router.put("/user/profile")
async def update_profile(
    profile_update: ProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user profile (name, email)"""
    update_data = {}

    if profile_update.name is not None:
        update_data["name"] = profile_update.name

    if profile_update.email is not None:
        # Check if email is already taken by another user
        new_email = profile_update.email.lower()
        existing = await db.users.find_one({"email": new_email, "id": {"$ne": current_user["id"]}})
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        update_data["email"] = new_email

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": update_data}
    )

    logger.info(f"Profile updated for user: {current_user['id']}")

    # Return updated user
    user = await db.users.find_one(
        {"id": current_user["id"]},
        {"_id": 0, "password_hash": 0}
    )
    return user


@api_router.post("/user/avatar")
async def upload_avatar(
    avatar_upload: AvatarUpload,
    current_user: dict = Depends(get_current_user)
):
    """Upload user avatar (base64 encoded, max 1.5MB)"""
    import base64

    avatar_data = avatar_upload.avatar_data

    # Remove data URL prefix if present
    if avatar_data.startswith("data:"):
        # Extract base64 part after the comma
        if "," in avatar_data:
            avatar_data = avatar_data.split(",", 1)[1]

    # Validate size (1.5MB limit after base64 encoding ~= 2MB base64 string)
    try:
        decoded = base64.b64decode(avatar_data)
        if len(decoded) > 1.5 * 1024 * 1024:  # 1.5MB
            raise HTTPException(status_code=400, detail="Avatar image too large (max 1.5MB)")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=400, detail="Invalid image data")

    # Store as data URL
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "avatar_url": avatar_upload.avatar_data,  # Store original with data URL prefix
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    logger.info(f"Avatar uploaded for user: {current_user['id']}")
    return {"message": "Avatar uploaded successfully"}


@api_router.delete("/user/avatar")
async def delete_avatar(current_user: dict = Depends(get_current_user)):
    """Remove user avatar"""
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$unset": {"avatar_url": ""}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    logger.info(f"Avatar removed for user: {current_user['id']}")
    return {"message": "Avatar removed successfully"}


async def fetch_webpage_content(url: str):
    """Fetch and parse webpage content with security validation"""
    try:
        # Validate URL is safe before fetching
        is_safe, error_msg = is_safe_url(url)
        if not is_safe:
            logger.warning(f"Unsafe URL blocked: {error_msg}")
            raise ValueError(f"Unsafe URL: {error_msg}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()

        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")

        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        doc = Document(html_content)
        summary_html = doc.summary()

        title = doc.title()
        if not title or len(title.strip()) < 3:
            if soup.title:
                title = soup.title.string
            else:
                title = urlparse(url).netloc

        description = None
        meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find(
            "meta", attrs={"property": "og:description"}
        )
        if meta_desc and meta_desc.get("content"):
            description = meta_desc.get("content")

        favicon = None
        favicon_tag = soup.find("link", rel="icon") or soup.find(
            "link", rel="shortcut icon"
        )
        if favicon_tag and favicon_tag.get("href"):
            favicon_url = favicon_tag.get("href")
            if favicon_url.startswith("//"):
                favicon = "https:" + favicon_url
            elif favicon_url.startswith("/"):
                parsed = urlparse(url)
                favicon = f"{parsed.scheme}://{parsed.netloc}{favicon_url}"
            elif not favicon_url.startswith("http"):
                parsed = urlparse(url)
                favicon = f"{parsed.scheme}://{parsed.netloc}/{favicon_url}"
            else:
                favicon = favicon_url

        thumbnail = None
        og_image = soup.find("meta", attrs={"property": "og:image"})
        if og_image and og_image.get("content"):
            thumbnail = og_image.get("content")

        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0
        text_content = h.handle(summary_html)
        text_content = text_content.strip() if text_content else ""

        if not text_content or len(text_content) < 100:
            cleaned_soup = BeautifulSoup(summary_html, "html.parser")
            paragraphs = cleaned_soup.find_all(["p", "article", "section"])
            text_parts = []
            for p in paragraphs:
                text = p.get_text(separator=" ", strip=True)
                if len(text) > 50:
                    text_parts.append(text)
            if text_parts:
                text_content = "\n\n".join(text_parts)

        if not text_content or len(text_content) < 50:
            text_content = soup.get_text(separator="\n", strip=True)
            text_content = text_content if text_content else ""

        # Store full content for offline reading (AI processing applies its own adaptive limits)
        text_content = " ".join(text_content.split())

        logger.info(f"Successfully fetched content from {urlparse(url).netloc}")
        return {
            "title": title.strip() if title else urlparse(url).netloc,
            "description": description,
            "favicon": favicon,
            "thumbnail": thumbnail,
            "html_content": summary_html,
            "text_content": text_content,
            "domain": urlparse(url).netloc,
        }
    except Exception as e:
        # Sanitize URL in logs - remove query params and fragments
        safe_url = urlparse(url)._replace(query="", fragment="").geturl()
        logger.exception(
            f"Error fetching webpage from domain {urlparse(url).netloc}"
        )
        return {
            "title": urlparse(url).netloc,
            "domain": urlparse(url).netloc,
            "text_content": f"Failed to fetch content",
            "html_content": "",
        }


async def generate_ai_summaries(text_content: str, bookmark_id: str):
    """Generate AI summaries for bookmark content with timeout protection"""
    try:
        # Wrap AI processing with 60-second timeout to prevent hanging
        return await asyncio.wait_for(
            _generate_ai_summaries_impl(text_content, bookmark_id), timeout=60.0
        )
    except asyncio.TimeoutError:
        logger.error(f"AI summary generation timed out for bookmark {bookmark_id}")
        await db.ai_summaries.update_one(
            {"bookmark_id": bookmark_id},
            {
                "$set": {
                    "processing_status": "failed",
                    "one_sentence": "AI processing timed out",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        return {"processing_status": "failed"}
    except Exception as e:
        logger.exception(
            f"Error in AI summary wrapper for bookmark {bookmark_id}"
        )
        return {"processing_status": "failed"}


async def _generate_ai_summaries_impl(text_content: str, bookmark_id: str):
    """Internal implementation of AI summary generation"""
    try:
        if not text_content or len(text_content.strip()) < 50:
            logger.info(
                f"Insufficient content for AI processing: bookmark {bookmark_id}"
            )
            raise ValueError("Insufficient content for AI processing")

        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY not configured")
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        # Use generous content for AI processing (Gemini 2.5 Flash has 1M token context)
        # Full text stored in DB; this limit is just for AI summarization cost efficiency
        content_for_summary = text_content[:50000].strip()  # ~10K tokens

        # Shorter snippet for tags (topic detection doesn't need full article)
        content_for_tags = text_content[:5000].strip()

        # Define all prompts with improved quality guidance
        prompts = {
            "one_sentence": f"""You are an expert content analyst. Your task is to distill the core message of this article into a single, precise sentence.

REQUIREMENTS:
- Maximum 25 words
- Capture the PRIMARY insight, finding, or argument
- Be specific—avoid generic statements like "this article discusses..."
- Use active voice and strong verbs
- Include the most newsworthy or unique element

ARTICLE:
{content_for_summary}

ONE-SENTENCE SUMMARY:""",
            "exec_summary": f"""You are a senior analyst creating an executive briefing. Summarize this content for a busy professional who needs to quickly understand the key points.

REQUIREMENTS:
- Write 2-3 paragraphs (100-150 words total)
- First paragraph: The core argument or main finding
- Second paragraph: Key supporting evidence or examples
- Third paragraph (if needed): Implications or takeaways
- Use clear, direct language—no filler phrases
- Be specific with numbers, names, and facts when available
- Avoid meta-commentary like "this article shows..."

ARTICLE:
{content_for_summary}

EXECUTIVE SUMMARY:""",
            "highlights": f"""You are extracting the most valuable insights from this content. Identify 4-6 key highlights that a reader would want to remember.

REQUIREMENTS:
- Each highlight should be a complete, standalone insight
- Include specific facts, statistics, quotes, or findings
- Focus on actionable or memorable information
- Write each highlight as 1-2 sentences
- Format: One highlight per line, no bullets or numbers

ARTICLE:
{content_for_summary}

KEY HIGHLIGHTS:""",
            "tags": f"""Generate precise, useful tags for categorizing and searching this content.

REQUIREMENTS:
- 4-6 tags total
- Mix of: topic tags, format tags (e.g., tutorial, opinion, research), and domain tags
- Use lowercase, hyphenate multi-word tags (e.g., machine-learning)
- Be specific (prefer "react-hooks" over "javascript")
- Return as comma-separated list

ARTICLE:
{content_for_tags}

TAGS:""",
        }

        # Estimated tokens per prompt - higher for longer content
        estimated_tokens_per_call = 1500

        # Parallel API call function
        async def call_gemini(prompt_type, prompt_text):
            await gemini_rate_limiter.acquire(
                estimated_tokens=estimated_tokens_per_call
            )
            response = await asyncio.to_thread(model.generate_content, prompt_text)
            # Record actual tokens if available
            if hasattr(response, "usage_metadata") and hasattr(
                response.usage_metadata, "total_token_count"
            ):
                actual_tokens = response.usage_metadata.total_token_count
                await gemini_rate_limiter.record_actual_tokens(actual_tokens)

            return prompt_type, response

        # Execute all 4 calls in parallel (removed bullets and long_form, added exec_summary)
        results = await asyncio.gather(
            *[
                call_gemini("one_sentence", prompts["one_sentence"]),
                call_gemini("exec_summary", prompts["exec_summary"]),
                call_gemini("highlights", prompts["highlights"]),
                call_gemini("tags", prompts["tags"]),
            ]
        )

        # Parse results into dictionary
        results_dict = dict(results)

        # Parse one-sentence summary
        one_sentence = (
            results_dict["one_sentence"].text.strip()
            if results_dict["one_sentence"].text
            else "Summary unavailable"
        )

        # Parse executive summary (replaces both bullets and long_form)
        exec_summary = (
            results_dict["exec_summary"].text.strip()
            if results_dict["exec_summary"].text
            else "Executive summary unavailable"
        )

        # Parse highlights (improved parsing for 4-6 highlights)
        highlights = []
        if results_dict["highlights"].text:
            for line in results_dict["highlights"].text.split("\n"):
                # Clean up the line - remove bullets, numbers, quotes
                line = line.strip()
                line = line.lstrip("-•*0123456789.)")
                line = line.strip().strip('"').strip()
                if len(line) > 20:  # Require more substantial highlights
                    highlights.append(line)
            highlights = highlights[:6]

        # Parse tags (improved to handle hyphenated multi-word tags)
        suggested_tags = []
        if results_dict["tags"].text:
            # Split by comma first, then clean each tag
            raw_tags = results_dict["tags"].text.replace("\n", ",").split(",")
            for tag in raw_tags:
                tag = tag.strip().strip(".,;:").lower()
                # Remove any remaining bullets or numbers
                tag = tag.lstrip("-•*0123456789.) ")
                if tag and len(tag) > 2 and len(tag) < 30:
                    suggested_tags.append(tag)
            suggested_tags = list(dict.fromkeys(suggested_tags))[:6]  # Preserve order, remove dupes

        await db.ai_summaries.update_one(
            {"bookmark_id": bookmark_id},
            {
                "$set": {
                    "one_sentence": one_sentence,
                    "exec_summary": exec_summary,
                    "highlights": highlights,
                    "suggested_tags": suggested_tags,
                    "processing_status": "completed",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    # Keep legacy fields for backward compatibility
                    "bullet_points": [],  # Deprecated
                    "long_form": exec_summary,  # Map to exec_summary for backward compat
                }
            },
        )
        logger.info(f"AI summaries generated successfully for bookmark {bookmark_id}")
        return {"processing_status": "completed"}
    except Exception as e:
        logger.exception(
            f"Error generating AI summaries for bookmark {bookmark_id}"
        )
        await db.ai_summaries.update_one(
            {"bookmark_id": bookmark_id},
            {
                "$set": {
                    "processing_status": "failed",
                    "one_sentence": "AI processing failed",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        return {"processing_status": "failed"}


def calculate_reading_time(text_content: str) -> int:
    """Calculate estimated reading time in minutes (avg 200 words/min)"""
    if not text_content:
        return 0
    word_count = len(text_content.split())
    return max(1, round(word_count / 200))


def normalize_embedding(embedding: List[float]) -> List[float]:
    """L2-normalize an embedding vector for consistent cosine similarity."""
    import numpy as np
    vec = np.array(embedding)
    norm = np.linalg.norm(vec)
    if norm > 0:
        return (vec / norm).tolist()
    return embedding


async def generate_embedding(
    text_content: str,
    title: str = "",
    description: str = "",
    min_length: int = 50,
    task_type: str = "retrieval_document",
) -> Optional[List[float]]:
    """
    Generate embedding vector for semantic search using Google's embedding model

    Args:
        text_content: Main text content of the bookmark
        title: Bookmark title (optional)
        description: Bookmark description (optional)
        min_length: Minimum character length required (default 50 for content, use 3 for queries)
        task_type: "retrieval_document" for indexing, "retrieval_query" for searching

    Returns:
        List of floats representing the L2-normalized embedding vector, or None if generation fails
    """
    try:
        if not text_content or len(text_content.strip()) < min_length:
            logger.info(
                f"Insufficient content for embedding generation (need {min_length}+ chars, got {len(text_content.strip()) if text_content else 0})"
            )
            return None

        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY not configured")
            return None

        # Combine title, description, and content for richer embeddings
        combined_text = ""
        if title:
            combined_text += f"Title: {title}\n\n"
        if description:
            combined_text += f"Description: {description}\n\n"

        # Use first 10,000 characters of content to avoid token limits
        combined_text += text_content[:10000].strip()

        # Use Google's embedding model with correct task type
        await gemini_rate_limiter.acquire(estimated_tokens=500)
        result = await asyncio.to_thread(
            genai.embed_content,
            model="models/text-embedding-004",
            content=combined_text,
            task_type=task_type,
        )

        embedding = result["embedding"]
        # L2-normalize for consistent cosine similarity (dot product after normalization)
        normalized_embedding = normalize_embedding(embedding)
        logger.info(f"Generated {task_type} embedding vector with {len(normalized_embedding)} dimensions")
        return normalized_embedding

    except Exception as e:
        logger.exception(f"Error generating embedding")
        return None


# Denylist for common false positive entities
ENTITY_DENYLIST = {
    "the", "this", "that", "these", "those", "what", "which", "where", "when",
    "how", "why", "who", "will", "would", "could", "should", "may", "might",
    "must", "can", "read", "more", "here", "click", "view", "see", "also",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "monday", "tuesday",
    "wednesday", "thursday", "friday", "saturday", "sunday", "today", "yesterday",
    "tomorrow", "new", "update", "updated", "latest", "recent", "best", "top",
    "home", "about", "contact", "privacy", "terms", "copyright", "share",
}

# Minimum confidence threshold for entities
MIN_ENTITY_CONFIDENCE = 0.6


def normalize_entity_name(name: str) -> str:
    """Normalize entity name: lowercase, trim, collapse whitespace."""
    return " ".join(name.lower().strip().split())


async def extract_entities_with_gemini(text_content: str) -> List[dict]:
    """
    Extract named entities using Gemini structured extraction.
    
    Returns list of: {"name": str, "type": str, "confidence": float}
    """
    try:
        if not text_content or len(text_content.strip()) < 100:
            return []
        
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            return []
        
        # Use first 5000 chars to limit token usage
        content_sample = text_content[:5000].strip()
        
        extraction_prompt = f"""Extract named entities from this content. Return ONLY valid JSON, no markdown.

Content:
{content_sample}

Return this exact JSON structure:
{{"entities": [{{"name": "Entity Name", "type": "person|organization|technology|concept|topic", "confidence": 0.9}}]}}

Rules:
- Extract only explicitly mentioned entities (not inferred)
- Maximum 15 entities
- Confidence 0-1 scale based on clarity of mention
- Types: person, organization, technology, concept, topic
- Ignore common words, months, days, navigation terms
- Use canonical/full names when possible
- No duplicates"""

        await gemini_rate_limiter.acquire(estimated_tokens=800)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await asyncio.to_thread(
            model.generate_content,
            extraction_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,  # Low temperature for consistent extraction
                max_output_tokens=1000,
            ),
        )
        
        if not response or not response.text:
            return []
        
        # Parse JSON response
        import json
        response_text = response.text.strip()
        # Handle markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        data = json.loads(response_text)
        entities = data.get("entities", [])
        
        # Filter and normalize entities
        valid_entities = []
        seen_names = set()
        
        for entity in entities:
            name = entity.get("name", "").strip()
            normalized = normalize_entity_name(name)
            confidence = entity.get("confidence", 0.5)
            entity_type = entity.get("type", "concept")
            
            # Skip if in denylist, too short, or duplicate
            if (
                normalized in ENTITY_DENYLIST
                or len(normalized) < 2
                or normalized in seen_names
                or confidence < MIN_ENTITY_CONFIDENCE
            ):
                continue
            
            seen_names.add(normalized)
            valid_entities.append({
                "name": name,  # Keep original casing
                "type": entity_type,
                "confidence": confidence,
            })
        
        logger.info(f"Extracted {len(valid_entities)} entities via Gemini")
        return valid_entities[:15]
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse entity extraction JSON: {e}")
        return []
    except Exception as e:
        logger.exception(f"Error in Gemini entity extraction")
        return []


async def extract_entities_and_concepts(
    text_content: str, summary_data: dict
) -> tuple[List[str], List[str]]:
    """
    Extract named entities and key concepts from content using Gemini AI.

    Args:
        text_content: Main text content
        summary_data: AI summary data containing tags and other metadata

    Returns:
        Tuple of (entities list, concepts list)
    """
    try:
        concepts = []

        # Use suggested tags from AI summary as initial concepts
        if summary_data and "suggested_tags" in summary_data:
            concepts = summary_data["suggested_tags"][:10]

        # Use Gemini for high-quality entity extraction
        extracted = await extract_entities_with_gemini(text_content)
        
        # Convert to simple list of entity names for backward compatibility
        entities = [e["name"] for e in extracted]

        return entities, concepts

    except Exception as e:
        logger.exception(f"Error extracting entities and concepts")
        return [], []


async def process_bookmark_content(
    bookmark_id: str, url: str, collection_id: Optional[str] = None, user_id: str = None
):
    """Background task to fetch content, generate AI summaries, and create embeddings for semantic search"""
    try:
        logger.info(f"Processing bookmark content: {bookmark_id}")
        content = await fetch_webpage_content(url)
        reading_time = calculate_reading_time(content.get("text_content", ""))

        await db.bookmarks.update_one(
            {"id": bookmark_id},
            {
                "$set": {
                    "title": content.get("title"),
                    "description": content.get("description"),
                    "favicon": content.get("favicon"),
                    "thumbnail": content.get("thumbnail"),
                    "html_content": content.get("html_content"),
                    "text_content": content.get("text_content"),
                    "domain": content.get("domain"),
                    "reading_time": reading_time,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

        # Generate AI summaries
        await generate_ai_summaries(content.get("text_content", ""), bookmark_id)

        # Generate embedding for semantic search (Phase 1: Semantic Knowledge Graph)
        text_content = content.get("text_content", "")
        title = content.get("title", "")
        description = content.get("description", "")

        if text_content and len(text_content.strip()) >= 50:
            embedding = await generate_embedding(text_content, title, description)

            # Get AI summary data for entity/concept extraction
            ai_summary = await db.ai_summaries.find_one(
                {"bookmark_id": bookmark_id}, {"_id": 0}
            )
            entities, concepts = await extract_entities_and_concepts(
                text_content, ai_summary
            )

            # Update bookmark with embedding and semantic data
            update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}

            if embedding:
                update_data["embedding"] = embedding
                update_data["embedding_model"] = "text-embedding-004"

            if entities:
                update_data["entities"] = entities

            if concepts:
                update_data["concepts"] = concepts

            await db.bookmarks.update_one({"id": bookmark_id}, {"$set": update_data})
            logger.info(
                f"Generated embedding and semantic data for bookmark {bookmark_id}"
            )

        logger.info(f"Successfully processed bookmark: {bookmark_id}")
    except Exception as e:
        logger.exception(f"Error processing bookmark {bookmark_id}")


async def process_bulk_import(
    import_job_id: str, bookmark_ids: List[str], user_id: str
):
    """Background task to process bulk import in two phases"""
    try:
        total = len(bookmark_ids)
        logger.info(
            f"Starting bulk import processing for job {import_job_id}: {total} bookmarks"
        )

        # Phase 1: Fast content fetching (no rate limit)
        content_fetched = 0
        failed = 0

        for bookmark_id in bookmark_ids:
            try:
                bookmark = await db.bookmarks.find_one({"id": bookmark_id})
                if not bookmark:
                    continue

                content = await fetch_webpage_content(bookmark["url"])
                reading_time = calculate_reading_time(content.get("text_content", ""))

                await db.bookmarks.update_one(
                    {"id": bookmark_id},
                    {
                        "$set": {
                            "title": content.get("title"),
                            "description": content.get("description"),
                            "favicon": content.get("favicon"),
                            "thumbnail": content.get("thumbnail"),
                            "html_content": content.get("html_content"),
                            "text_content": content.get("text_content"),
                            "domain": content.get("domain"),
                            "reading_time": reading_time,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    },
                )
                content_fetched += 1

                # Update progress every 10 bookmarks
                if content_fetched % 10 == 0:
                    await db.import_jobs.update_one(
                        {"id": import_job_id},
                        {
                            "$set": {
                                "content_fetched": content_fetched,
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                            }
                        },
                    )
            except Exception as e:
                failed += 1
                logger.exception(
                    f"Error fetching content for bookmark {bookmark_id}"
                )

        # Update after Phase 1 completion
        await db.import_jobs.update_one(
            {"id": import_job_id},
            {
                "$set": {
                    "content_fetched": content_fetched,
                    "failed": failed,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

        logger.info(
            f"Phase 1 complete for job {import_job_id}: {content_fetched}/{total} fetched, {failed} failed"
        )

        # Phase 2: Rate-limited AI processing
        ai_processed = 0

        for bookmark_id in bookmark_ids:
            try:
                bookmark = await db.bookmarks.find_one({"id": bookmark_id})
                if not bookmark or not bookmark.get("text_content"):
                    continue

                result = await generate_ai_summaries(
                    bookmark["text_content"], bookmark_id
                )
                if result.get("processing_status") == "completed":
                    ai_processed += 1
                else:
                    failed += 1

                # Update progress every 5 AI processes
                if ai_processed % 5 == 0:
                    # Calculate ETA
                    elapsed = (
                        datetime.now(timezone.utc)
                        - datetime.fromisoformat(
                            (await db.import_jobs.find_one({"id": import_job_id}))[
                                "created_at"
                            ]
                        )
                    ).total_seconds()
                    remaining = total - ai_processed
                    eta = datetime.now(timezone.utc) + timedelta(
                        seconds=(elapsed / ai_processed) * remaining
                        if ai_processed > 0
                        else 0
                    )

                    await db.import_jobs.update_one(
                        {"id": import_job_id},
                        {
                            "$set": {
                                "ai_processed": ai_processed,
                                "failed": failed,
                                "estimated_completion_time": eta.isoformat(),
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                            }
                        },
                    )
            except Exception as e:
                failed += 1
                logger.exception(
                    f"Error processing AI for bookmark {bookmark_id}"
                )

        # Mark job as completed
        await db.import_jobs.update_one(
            {"id": import_job_id},
            {
                "$set": {
                    "ai_processed": ai_processed,
                    "failed": failed,
                    "status": "completed",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

        logger.info(
            f"Bulk import completed for job {import_job_id}: {ai_processed}/{total} AI processed"
        )

    except Exception as e:
        logger.exception(f"Error in bulk import job {import_job_id}")
        await db.import_jobs.update_one(
            {"id": import_job_id},
            {
                "$set": {
                    "status": "failed",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )


async def find_quick_connections(
    bookmark_id: str,
    url: str,
    domain: str,
    title: str,
    user_id: str,
    limit: int = 5
) -> List[QuickConnection]:
    """
    Find related bookmarks quickly (before embeddings are generated).
    
    Strategy (fast, no embedding needed):
    1. Domain match: Other bookmarks from same domain
    """
    connections = []
    
    if not domain:
        return connections
    
    domain_matches = await db.bookmarks.find(
        {
            "user_id": user_id,
            "domain": domain,
            "id": {"$ne": bookmark_id},
        },
        {
            "_id": 0, "id": 1, "title": 1, "domain": 1, "favicon": 1
        }
    ).sort("created_at", -1).limit(limit).to_list(None)
    
    for bm in domain_matches:
        connections.append(QuickConnection(
            id=bm["id"],
            title=bm.get("title"),
            domain=bm.get("domain"),
            favicon=bm.get("favicon"),
            connection_type="same_domain",
            connection_reason=f"Also from {domain}"
        ))
    
    return connections[:limit]


@api_router.get("/bookmarks/{bookmark_id}/related")
async def get_related_bookmarks(
    bookmark_id: str,
    limit: int = 5,
    current_user: dict = Depends(get_current_user_info),
):
    bookmark = await db.bookmarks.find_one(
        {"id": bookmark_id, "user_id": current_user["id"]},
        {"_id": 0, "id": 1, "url": 1, "domain": 1, "title": 1}
    )
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    ai_summary = await db.ai_summaries.find_one(
        {"bookmark_id": bookmark_id},
        {"_id": 0, "processing_status": 1}
    )

    related = await find_quick_connections(
        bookmark_id=bookmark["id"],
        url=bookmark.get("url", ""),
        domain=bookmark.get("domain", ""),
        title=bookmark.get("title", ""),
        user_id=current_user["id"],
        limit=limit
    )

    return {
        "related": related,
        "processing_status": ai_summary.get("processing_status") if ai_summary else None
    }


@api_router.post("/bookmarks", response_model=BookmarkWithConnections)
@limiter.limit("20/minute")  # IP-based rate limiting
@limiter.limit("100/hour", key_func=get_user_identifier)  # User-based rate limiting
async def create_bookmark(
    request: Request,
    bookmark_data: BookmarkCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_info),
):
    parsed_url = urlparse(bookmark_data.url)

    bookmark = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "url": bookmark_data.url,
        "title": parsed_url.netloc or "Loading...",
        "description": None,
        "favicon": None,
        "thumbnail": None,
        "html_content": None,
        "text_content": None,
        "domain": parsed_url.netloc,
        "reading_time": None,
        "read_status": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.bookmarks.insert_one(bookmark)

    ai_summary = {
        "id": str(uuid.uuid4()),
        "bookmark_id": bookmark["id"],
        "processing_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.ai_summaries.insert_one(ai_summary)

    background_tasks.add_task(
        process_bookmark_content,
        bookmark["id"],
        bookmark_data.url,
        bookmark_data.collection_id,
        current_user["id"],
    )

    if bookmark_data.collection_id:
        await db.collections.update_one(
            {"id": bookmark_data.collection_id, "user_id": current_user["id"]},
            {"$addToSet": {"bookmark_ids": bookmark["id"]}},
        )

    connections = await find_quick_connections(
        bookmark_id=bookmark["id"],
        url=bookmark_data.url,
        domain=parsed_url.netloc,
        title=bookmark.get("title", ""),
        user_id=current_user["id"],
        limit=5
    )

    return BookmarkWithConnections(
        bookmark=Bookmark(**bookmark),
        connections=connections,
        connections_count=len(connections)
    )


@api_router.get("/bookmarks", response_model=List[dict])
async def get_bookmarks(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    domain: Optional[str] = None,
    collection_id: Optional[str] = None,
    read_status: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    limit: Optional[int] = 100,
    current_user: dict = Depends(get_current_user_info),
):
    query = {"user_id": current_user["id"]}

    if domain:
        query["domain"] = domain

    if read_status == "read":
        query["read_status"] = True
    elif read_status == "unread":
        query["read_status"] = False

    if collection_id:
        collection = await db.collections.find_one(
            {"id": collection_id}, {"_id": 0, "bookmark_ids": 1}
        )
        if collection:
            query["id"] = {"$in": collection.get("bookmark_ids", [])}

    sort_field = "created_at"
    sort_order = -1
    if sort_by == "reading_time":
        sort_field = "reading_time"
        sort_order = 1
    elif sort_by == "title":
        sort_field = "title"
        sort_order = 1

    projection = {
        "_id": 0,
        "id": 1,
        "url": 1,
        "title": 1,
        "description": 1,
        "domain": 1,
        "thumbnail": 1,
        "favicon": 1,
        "reading_time": 1,
        "read_status": 1,
        "created_at": 1,
        "updated_at": 1,
        "last_accessed": 1,  # Phase 1: For aging indicators
        "view_count": 1,  # Phase 1: For usage tracking
    }

    bookmarks = (
        await db.bookmarks.find(query, projection)
        .sort(sort_field, sort_order)
        .limit(min(limit, 1000))
        .to_list(None)
    )

    # Improved search: use keyword matching across multiple fields
    # For full hybrid search with semantic, use the /api/search endpoint
    if search:
        search_lower = search.lower()
        
        def matches_search(b: dict) -> bool:
            """Check if bookmark matches search query."""
            title = (b.get("title") or "").lower()
            description = (b.get("description") or "").lower()
            url = (b.get("url") or "").lower()
            domain = (b.get("domain") or "").lower()
            return (
                search_lower in title
                or search_lower in description
                or search_lower in url
                or search_lower in domain
            )
        
        bookmarks = [b for b in bookmarks if matches_search(b)]

    bookmark_ids = [b["id"] for b in bookmarks]
    summaries = await db.ai_summaries.find(
        {"bookmark_id": {"$in": bookmark_ids}}, {"_id": 0}
    ).to_list(None)

    summary_map = {s["bookmark_id"]: s for s in summaries}

    result = []
    for bookmark in bookmarks:
        summary = summary_map.get(bookmark["id"])

        if tag and summary:
            if tag.lower() not in [
                t.lower() for t in summary.get("suggested_tags", [])
            ]:
                continue

        bookmark_with_summary = {**bookmark}
        if summary:
            bookmark_with_summary["ai_summary"] = summary
        result.append(bookmark_with_summary)

    return result


# Phase 1: Aged Bookmarks Endpoint (MUST be before /{bookmark_id} to avoid route collision)
@api_router.get("/bookmarks/aged")
async def get_aged_bookmarks(
    min_days: int = 30,
    limit: int = 100,
    current_user: dict = Depends(get_current_user_info),
):
    """
    Get count and list of bookmarks not accessed in min_days.
    Used for aged bookmarks banner.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=min_days)

    query = {
        "user_id": current_user["id"],
        "$or": [
            {"last_accessed": {"$lt": cutoff_date.isoformat()}},
            {"last_accessed": {"$exists": False}},  # Unmigrated bookmarks
        ],
    }

    projection = {
        "_id": 0,
        "id": 1,
        "title": 1,
        "url": 1,
        "domain": 1,
        "thumbnail": 1,
        "created_at": 1,
        "last_accessed": 1,
        "view_count": 1,
    }

    bookmarks = (
        await db.bookmarks.find(query, projection)
        .sort("last_accessed", 1)
        .limit(limit)
        .to_list(None)
    )

    return {"count": len(bookmarks), "bookmarks": bookmarks}


# ============================================
# Intelligent Resurfacing Engine (Phase 1)
# ============================================


@api_router.get("/resurfacing")
async def get_resurfacing_suggestions(
    limit: int = 5, current_user: dict = Depends(get_current_user_info)
):
    """
    Get top resurfacing suggestions for the user.
    Returns bookmarks scored by age, engagement, content quality, and spaced repetition.
    """
    # Get all user bookmarks with necessary fields
    projection = {
        "_id": 0,
        "id": 1,
        "title": 1,
        "url": 1,
        "domain": 1,
        "thumbnail": 1,
        "favicon": 1,
        "description": 1,
        "reading_time": 1,
        "created_at": 1,
        "last_accessed": 1,
        "view_count": 1,
        "resurfacing_snoozed_until": 1,
        "resurfacing_archived": 1,
    }

    bookmarks = await db.bookmarks.find(
        {"user_id": current_user["id"]}, projection
    ).to_list(500)  # Cap at 500 for performance

    # Get AI summaries for all bookmarks
    bookmark_ids = [b["id"] for b in bookmarks]
    summaries = await db.ai_summaries.find(
        {"bookmark_id": {"$in": bookmark_ids}}, {"_id": 0}
    ).to_list(None)
    summary_map = {s["bookmark_id"]: s for s in summaries}

    # Score each bookmark
    scored_bookmarks = []
    current_time = datetime.now(timezone.utc)

    for bookmark in bookmarks:
        if not should_resurface(bookmark):
            continue

        ai_summary = summary_map.get(bookmark["id"])
        score, breakdown = calculate_resurfacing_score(
            bookmark, ai_summary, current_time
        )

        # Calculate days since access for reason generation
        last_accessed = bookmark.get("last_accessed")
        if isinstance(last_accessed, str):
            try:
                last_accessed = datetime.fromisoformat(
                    last_accessed.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                last_accessed = None

        if last_accessed:
            if last_accessed.tzinfo is None:
                last_accessed = last_accessed.replace(tzinfo=timezone.utc)
            days_since = (current_time - last_accessed).days
        else:
            days_since = 30  # Default

        reason = get_resurfacing_reason(bookmark, breakdown, days_since)

        # Build response object
        scored_bookmarks.append(
            {
                **bookmark,
                "resurfacing_score": score,
                "resurfacing_reason": reason,
                "days_since_access": days_since,
                "ai_summary": ai_summary,
            }
        )

    # Sort by score descending and take top N
    scored_bookmarks.sort(key=lambda x: x["resurfacing_score"], reverse=True)
    top_suggestions = scored_bookmarks[:limit]

    # Remove internal fields before returning
    for bm in top_suggestions:
        bm.pop("resurfacing_snoozed_until", None)
        bm.pop("resurfacing_archived", None)

    return {"suggestions": top_suggestions, "total_candidates": len(scored_bookmarks)}


class SnoozeRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=90, description="Number of days to snooze")


@api_router.post("/resurfacing/{bookmark_id}/snooze")
async def snooze_resurfacing(
    bookmark_id: str,
    snooze_data: SnoozeRequest,
    current_user: dict = Depends(get_current_user_info),
):
    """
    Snooze a bookmark from resurfacing suggestions for N days.
    """
    # Verify ownership
    bookmark = await db.bookmarks.find_one(
        {"id": bookmark_id, "user_id": current_user["id"]}
    )
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    snooze_until = datetime.now(timezone.utc) + timedelta(days=snooze_data.days)

    await db.bookmarks.update_one(
        {"id": bookmark_id},
        {
            "$set": {
                "resurfacing_snoozed_until": snooze_until.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )

    return {
        "message": f"Bookmark snoozed for {snooze_data.days} days",
        "snoozed_until": snooze_until.isoformat(),
    }


@api_router.post("/resurfacing/{bookmark_id}/archive")
async def archive_from_resurfacing(
    bookmark_id: str, current_user: dict = Depends(get_current_user_info)
):
    """
    Archive a bookmark from resurfacing suggestions (never show again).
    """
    # Verify ownership
    bookmark = await db.bookmarks.find_one(
        {"id": bookmark_id, "user_id": current_user["id"]}
    )
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.bookmarks.update_one(
        {"id": bookmark_id},
        {
            "$set": {
                "resurfacing_archived": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )

    return {"message": "Bookmark archived from resurfacing"}


@api_router.post("/resurfacing/{bookmark_id}/unarchive")
async def unarchive_from_resurfacing(
    bookmark_id: str, current_user: dict = Depends(get_current_user_info)
):
    """
    Unarchive a bookmark to allow it back in resurfacing suggestions.
    """
    # Verify ownership
    bookmark = await db.bookmarks.find_one(
        {"id": bookmark_id, "user_id": current_user["id"]}
    )
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.bookmarks.update_one(
        {"id": bookmark_id},
        {
            "$set": {
                "resurfacing_archived": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )

    return {"message": "Bookmark unarchived from resurfacing"}


# ============================================
# Memory Jogger API (Daily Featured Bookmark)
# ============================================


async def get_recent_connections(
    user_id: str, bookmark_embedding: list, days: int = 7, threshold: float = 0.6
) -> dict:
    """
    Find bookmarks saved in last N days that are semantically related.
    Returns connection count and topics.
    """
    import numpy as np

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    recent_bookmarks = await db.bookmarks.find(
        {
            "user_id": user_id,
            "created_at": {"$gte": cutoff_date.isoformat()},
            "embedding": {"$exists": True, "$ne": None},
        },
        {"_id": 0, "id": 1, "embedding": 1, "title": 1},
    ).to_list(100)

    if not recent_bookmarks or not bookmark_embedding:
        return {"count": 0, "topics": []}

    def cosine_similarity_score(vec1, vec2):
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    connected_titles = []
    for bm in recent_bookmarks:
        if bm.get("embedding"):
            similarity = cosine_similarity_score(bookmark_embedding, bm["embedding"])
            if similarity >= threshold:
                connected_titles.append(bm.get("title", ""))

    topics = []
    for title in connected_titles[:5]:
        words = title.split()[:3] if title else []
        if words:
            topics.append(" ".join(words))

    return {"count": len(connected_titles), "topics": topics[:3]}


class MemoryJoggerDismissRequest(BaseModel):
    bookmark_id: str = Field(..., description="The bookmark ID to dismiss")


@api_router.get("/memory-jogger")
async def get_memory_jogger(current_user: dict = Depends(get_current_user_info)):
    """
    Get a single featured bookmark for today's memory jogger.
    Uses scoring algorithm to surface forgotten but relevant bookmarks.
    """
    current_time = datetime.now(timezone.utc)
    seven_days_ago = current_time - timedelta(days=7)
    thirty_days_ago = current_time - timedelta(days=30)

    query = {
        "user_id": current_user["id"],
        "$or": [
            {"last_accessed": {"$lt": seven_days_ago.isoformat()}},
            {"last_accessed": {"$exists": False}},
        ],
        "$and": [
            {
                "$or": [
                    {"resurfacing_snoozed_until": {"$exists": False}},
                    {"resurfacing_snoozed_until": None},
                    {"resurfacing_snoozed_until": {"$lt": current_time.isoformat()}},
                ]
            },
            {
                "$or": [
                    {"resurfacing_archived": {"$exists": False}},
                    {"resurfacing_archived": False},
                ]
            },
        ],
    }

    projection = {
        "_id": 0,
        "id": 1,
        "title": 1,
        "url": 1,
        "domain": 1,
        "favicon": 1,
        "thumbnail": 1,
        "description": 1,
        "created_at": 1,
        "last_accessed": 1,
        "embedding": 1,
    }

    bookmarks = await db.bookmarks.find(query, projection).limit(200).to_list(None)

    if not bookmarks:
        return {
            "bookmark": None,
            "context": None,
            "has_memory": False,
            "message": "Save more bookmarks to unlock daily memories",
        }

    bookmark_ids = [b["id"] for b in bookmarks]
    summaries = await db.ai_summaries.find(
        {"bookmark_id": {"$in": bookmark_ids}, "processing_status": "completed"},
        {"_id": 0, "bookmark_id": 1},
    ).to_list(None)
    summary_set = {s["bookmark_id"] for s in summaries}

    related_counts = {}
    for bm in bookmarks:
        if bm.get("embedding"):
            conn_data = await get_recent_connections(
                current_user["id"], bm["embedding"], days=7, threshold=0.6
            )
            related_counts[bm["id"]] = conn_data

    scored_bookmarks = []
    for bm in bookmarks:
        score = 0

        conn_data = related_counts.get(bm["id"], {"count": 0, "topics": []})
        if conn_data["count"] > 0:
            score += 30

        last_accessed = bm.get("last_accessed")
        days_since_accessed = 30
        if last_accessed:
            try:
                if isinstance(last_accessed, str):
                    last_accessed_dt = datetime.fromisoformat(
                        last_accessed.replace("Z", "+00:00")
                    )
                else:
                    last_accessed_dt = last_accessed
                if last_accessed_dt.tzinfo is None:
                    last_accessed_dt = last_accessed_dt.replace(tzinfo=timezone.utc)
                days_since_accessed = (current_time - last_accessed_dt).days
            except (ValueError, TypeError):
                days_since_accessed = 30

        if days_since_accessed >= 30:
            score += 20

        if bm["id"] in summary_set:
            score += 10

        all_user_related = await db.bookmarks.find(
            {
                "user_id": current_user["id"],
                "id": {"$ne": bm["id"]},
                "embedding": {"$exists": True, "$ne": None},
            },
            {"_id": 0, "id": 1},
        ).to_list(10)
        if len(all_user_related) >= 3:
            score += 5

        score += random.randint(0, 15)

        scored_bookmarks.append(
            {
                "bookmark": bm,
                "score": score,
                "days_since_accessed": days_since_accessed,
                "conn_data": conn_data,
            }
        )

    scored_bookmarks.sort(key=lambda x: x["score"], reverse=True)
    top = scored_bookmarks[0]
    selected_bookmark = top["bookmark"]

    created_at = selected_bookmark.get("created_at")
    days_since_saved = 0
    if created_at:
        try:
            if isinstance(created_at, str):
                created_at_dt = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            else:
                created_at_dt = created_at
            if created_at_dt.tzinfo is None:
                created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)
            days_since_saved = (current_time - created_at_dt).days
        except (ValueError, TypeError):
            days_since_saved = 0

    conn_data = top["conn_data"]
    connection_count = conn_data["count"]
    connected_topics = conn_data["topics"]

    if connection_count > 0:
        reason = f"Connects to {connection_count} bookmark{'s' if connection_count > 1 else ''} you saved this week"
        if connected_topics:
            reason += f" about {', '.join(connected_topics[:2])}"
    elif top["days_since_accessed"] >= 30:
        reason = f"You haven't visited this in {top['days_since_accessed']} days"
    else:
        reason = "A forgotten gem from your collection"

    ai_summary = await db.ai_summaries.find_one(
        {"bookmark_id": selected_bookmark["id"]}, {"_id": 0}
    )

    selected_bookmark.pop("embedding", None)

    return {
        "bookmark": {
            **selected_bookmark,
            "ai_summary": ai_summary,
        },
        "context": {
            "days_since_saved": days_since_saved,
            "days_since_accessed": top["days_since_accessed"],
            "connection_count": connection_count,
            "connected_topics": connected_topics,
            "reason": reason,
        },
        "has_memory": True,
    }


@api_router.post("/memory-jogger/dismiss")
async def dismiss_memory_jogger(
    request: MemoryJoggerDismissRequest,
    current_user: dict = Depends(get_current_user_info),
):
    """
    Dismiss today's memory jogger. Records dismissal for analytics.
    """
    bookmark = await db.bookmarks.find_one(
        {"id": request.bookmark_id, "user_id": current_user["id"]}
    )
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.bookmarks.update_one(
        {"id": request.bookmark_id},
        {
            "$set": {
                "memory_jogger_dismissed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )

    return {"message": "Memory jogger dismissed", "bookmark_id": request.bookmark_id}


@api_router.get("/bookmarks/{bookmark_id}")
async def get_bookmark(
    bookmark_id: str, current_user: dict = Depends(get_current_user_info)
):
    bookmark = await db.bookmarks.find_one(
        {"id": bookmark_id, "user_id": current_user["id"]}, {"_id": 0}
    )
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    summary = await db.ai_summaries.find_one({"bookmark_id": bookmark_id}, {"_id": 0})

    result = {**bookmark}
    if summary:
        result["ai_summary"] = summary

    # Phase 1: Auto-track detail page view
    await track_bookmark_access(bookmark_id, "detail", current_user)

    return result


@api_router.get("/bookmarks/{bookmark_id}/related")
async def get_related_bookmarks(
    bookmark_id: str,
    limit: int = 5,
    current_user: dict = Depends(get_current_user_info),
):
    """
    Get semantically related bookmarks using embedding similarity
    Part of Semantic Knowledge Graph feature (Phase 1)
    """
    # Get the source bookmark with its embedding
    source_bookmark = await db.bookmarks.find_one(
        {"id": bookmark_id, "user_id": current_user["id"]},
        {"_id": 0, "embedding": 1, "title": 1},
    )

    if not source_bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    if not source_bookmark.get("embedding"):
        # No embedding available yet - return empty result
        return {
            "related": [],
            "message": "Semantic analysis not yet available for this bookmark",
        }

    source_embedding = source_bookmark["embedding"]

    # Get all user's bookmarks that have embeddings (excluding the source bookmark)
    all_bookmarks = await db.bookmarks.find(
        {
            "user_id": current_user["id"],
            "id": {"$ne": bookmark_id},
            "embedding": {"$exists": True, "$ne": None},
        },
        {
            "_id": 0,
            "id": 1,
            "title": 1,
            "description": 1,
            "url": 1,
            "favicon": 1,
            "domain": 1,
            "thumbnail": 1,
            "created_at": 1,
            "embedding": 1,
            "entities": 1,
            "concepts": 1,
        },
    ).to_list(None)

    if not all_bookmarks:
        return {
            "related": [],
            "message": "No other bookmarks with semantic data available",
        }

    # Calculate similarity using dot product (vectors are L2-normalized)
    import numpy as np

    def dot_product_similarity(vec1, vec2):
        """Dot product of L2-normalized vectors equals cosine similarity."""
        return float(np.dot(vec1, vec2))

    # Calculate similarity scores and filter by threshold
    similarities = []
    for bookmark in all_bookmarks:
        if bookmark.get("embedding"):
            similarity = dot_product_similarity(
                source_embedding, bookmark["embedding"]
            )
            # Only include results above minimum threshold
            if similarity >= MIN_SEMANTIC_SCORE:
                bookmark.pop("embedding", None)
                bookmark["similarity_score"] = similarity
                similarities.append(bookmark)

    # Sort by similarity score and take top N
    similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
    top_related = similarities[:limit]

    return {"related": top_related}


@api_router.get("/knowledge-graph/explore")
async def explore_knowledge_graph(
    limit: int = 50, current_user: dict = Depends(get_current_user_info)
):
    """
    Explore the user's knowledge graph with enhanced graph metrics.
    
    Features:
    - Entity/concept importance ranking (by connection count)
    - Bookmark similarity clusters
    - Co-occurrence relationships
    """
    import numpy as np
    
    # Get all bookmarks with embeddings
    bookmarks = (
        await db.bookmarks.find(
            {
                "user_id": current_user["id"],
                "embedding": {"$exists": True, "$ne": None},
            },
            {
                "_id": 0,
                "id": 1,
                "title": 1,
                "description": 1,
                "url": 1,
                "domain": 1,
                "favicon": 1,
                "thumbnail": 1,
                "created_at": 1,
                "entities": 1,
                "concepts": 1,
                "embedding": 1,
            },
        )
        .limit(limit)
        .to_list(None)
    )

    if not bookmarks:
        return {
            "bookmarks": [],
            "entities": [],
            "concepts": [],
            "concept_connections": {},
            "entity_connections": {},
            "entity_importance": {},
            "concept_importance": {},
            "related_bookmarks": {},
            "total_bookmarks": 0,
            "total_entities": 0,
            "total_concepts": 0,
        }

    # Extract all unique entities and concepts with counts
    entity_counts = {}
    concept_counts = {}

    for bookmark in bookmarks:
        for entity in bookmark.get("entities", []):
            entity_counts[entity] = entity_counts.get(entity, 0) + 1
        for concept in bookmark.get("concepts", []):
            concept_counts[concept] = concept_counts.get(concept, 0) + 1

    # Build concept/entity connections
    concept_connections = {}
    entity_connections = {}

    for bookmark in bookmarks:
        bookmark_id = bookmark["id"]

        for concept in bookmark.get("concepts", []):
            if concept not in concept_connections:
                concept_connections[concept] = []
            concept_connections[concept].append(bookmark_id)

        for entity in bookmark.get("entities", []):
            if entity not in entity_connections:
                entity_connections[entity] = []
            entity_connections[entity].append(bookmark_id)

    # Calculate entity/concept importance (IDF-weighted connection score)
    total_docs = len(bookmarks)
    
    def calculate_importance(count: int) -> float:
        # Higher count = more connected = more important, but with diminishing returns
        # Also penalize very common terms (like TF-IDF logic)
        if count == 0:
            return 0.0
        idf = math.log((total_docs + 1) / (count + 1)) + 1
        connection_score = math.log(count + 1)
        return round(idf * connection_score, 3)
    
    entity_importance = {
        entity: calculate_importance(count) 
        for entity, count in entity_counts.items()
    }
    concept_importance = {
        concept: calculate_importance(count) 
        for concept, count in concept_counts.items()
    }

    # Find related bookmarks using embedding similarity
    related_bookmarks = {}
    embedding_map = {b["id"]: b.get("embedding") for b in bookmarks if b.get("embedding")}
    
    if len(embedding_map) > 1:
        def dot_product_similarity(vec1, vec2):
            return float(np.dot(vec1, vec2))
        
        # For each bookmark, find top 3 most similar
        for bookmark in bookmarks:
            if not bookmark.get("embedding"):
                continue
            
            similarities = []
            for other in bookmarks:
                if other["id"] == bookmark["id"] or not other.get("embedding"):
                    continue
                sim = dot_product_similarity(bookmark["embedding"], other["embedding"])
                if sim > 0.5:  # Only include reasonably similar
                    similarities.append((other["id"], round(sim, 3)))
            
            # Sort and take top 3
            similarities.sort(key=lambda x: x[1], reverse=True)
            if similarities:
                related_bookmarks[bookmark["id"]] = similarities[:3]

    # Remove embeddings from response to reduce payload
    for bookmark in bookmarks:
        bookmark.pop("embedding", None)

    # Sort entities/concepts by importance for response
    top_entities = sorted(entity_importance.items(), key=lambda x: x[1], reverse=True)[:50]
    top_concepts = sorted(concept_importance.items(), key=lambda x: x[1], reverse=True)[:50]

    return {
        "bookmarks": bookmarks,
        "entities": [e[0] for e in top_entities],
        "concepts": [c[0] for c in top_concepts],
        "concept_connections": concept_connections,
        "entity_connections": entity_connections,
        "entity_importance": dict(top_entities),
        "concept_importance": dict(top_concepts),
        "related_bookmarks": related_bookmarks,
        "total_bookmarks": len(bookmarks),
        "total_entities": len(entity_counts),
        "total_concepts": len(concept_counts),
    }


# Minimum semantic similarity threshold for search results
# ============================================================================
# ENHANCED SEARCH ALGORITHM - BM25 + RRF + Graph-Aware Ranking
# ============================================================================

# BM25 parameters (tuned for bookmark search)
BM25_K1 = 1.2  # Term frequency saturation
BM25_B = 0.75  # Length normalization factor

# RRF fusion constant (typically 20-60, higher = more weight to lower ranks)
RRF_K = 60

# Stopwords for tokenization
SEARCH_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "this",
    "that", "these", "those", "it", "its", "i", "you", "he", "she", "we",
    "they", "what", "which", "who", "whom", "when", "where", "why", "how",
}


def tokenize_text(text: str) -> List[str]:
    """Tokenize text for BM25 scoring."""
    if not text:
        return []
    # Lowercase, split on non-alphanumeric, filter stopwords and short tokens
    tokens = re.findall(r'\b[a-z0-9]+\b', text.lower())
    return [t for t in tokens if t not in SEARCH_STOPWORDS and len(t) > 1]


def calculate_bm25_score(
    query_tokens: List[str],
    doc_tokens: List[str],
    doc_freq: Dict[str, int],
    avg_doc_len: float,
    total_docs: int,
) -> float:
    """
    Calculate BM25 score for a document given a query.
    
    BM25(d, q) = Σ IDF(t) * (tf(t,d) * (k1+1)) / (tf(t,d) + k1 * (1 - b + b * |d|/avgdl))
    """
    if not query_tokens or not doc_tokens:
        return 0.0
    
    doc_len = len(doc_tokens)
    if doc_len == 0 or avg_doc_len == 0:
        return 0.0
    
    # Count term frequencies in document
    doc_tf = {}
    for token in doc_tokens:
        doc_tf[token] = doc_tf.get(token, 0) + 1
    
    score = 0.0
    for term in query_tokens:
        if term not in doc_tf:
            continue
        
        tf = doc_tf[term]
        df = doc_freq.get(term, 1)  # Document frequency of term
        
        # IDF with smoothing: log((N - df + 0.5) / (df + 0.5))
        idf = max(0.0, math.log((total_docs - df + 0.5) / (df + 0.5)))
        
        # BM25 term score
        numerator = tf * (BM25_K1 + 1)
        denominator = tf + BM25_K1 * (1 - BM25_B + BM25_B * (doc_len / avg_doc_len))
        
        score += idf * (numerator / denominator)
    
    return score


def calculate_entity_boost(
    query_entities: List[str],
    doc_entities: List[str],
    entity_idf: Dict[str, float],
) -> float:
    """
    Calculate IDF-weighted entity overlap score.
    Boosts bookmarks that share entities/concepts with the query.
    """
    if not query_entities or not doc_entities:
        return 0.0
    
    query_set = {e.lower() for e in query_entities}
    doc_set = {e.lower() for e in doc_entities}
    
    overlap = query_set & doc_set
    if not overlap:
        return 0.0
    
    # Sum IDF weights for matching entities
    score = sum(entity_idf.get(e, 1.0) for e in overlap)
    return score


def reciprocal_rank_fusion(
    ranked_lists: List[List[tuple]],
    k: int = RRF_K,
) -> Dict[str, float]:
    """
    Combine multiple ranked lists using Reciprocal Rank Fusion.
    
    RRF(d) = Σ 1 / (k + rank_l(d)) for each list l
    
    Args:
        ranked_lists: List of [(doc_id, score), ...] sorted by score descending
        k: Fusion constant (default 60)
    
    Returns:
        Dict of doc_id -> RRF score
    """
    rrf_scores = {}
    
    for ranked_list in ranked_lists:
        for rank, (doc_id, _score) in enumerate(ranked_list, start=1):
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
            rrf_scores[doc_id] += 1.0 / (k + rank)
    
    return rrf_scores


def detect_query_type(query: str) -> str:
    """
    Detect query type to adapt search weighting.
    
    Returns: 'exact', 'technical', or 'semantic'
    """
    # Quoted phrases indicate exact match desire
    if '"' in query or "'" in query:
        return 'exact'
    
    # Technical patterns: URLs, code-like syntax, file paths
    if re.search(r'[/\\._:@#]+', query) or re.search(r'\b\d+\.\d+\b', query):
        return 'technical'
    
    # Short queries (1-2 words) tend to be keyword-focused
    word_count = len(query.split())
    if word_count <= 2:
        return 'exact'
    
    # Longer natural language queries benefit from semantic
    return 'semantic'


def get_adaptive_weights(query_type: str) -> tuple:
    """
    Get adaptive semantic/keyword weights based on query type.
    
    Returns: (semantic_weight, keyword_weight)
    """
    if query_type == 'exact':
        return (0.3, 0.7)  # Favor keyword matching
    elif query_type == 'technical':
        return (0.4, 0.6)  # Balanced with keyword edge
    else:  # semantic
        return (0.75, 0.25)  # Favor semantic understanding


import math


@api_router.get("/knowledge-graph/search")
async def semantic_search(
    query: str, limit: int = 10, current_user: dict = Depends(get_current_user_info)
):
    """
    Enhanced semantic search using adaptive thresholds and entity boosting.
    Uses RRF to combine semantic similarity with entity overlap.
    """
    import numpy as np
    
    if not query or len(query.strip()) < 3:
        raise HTTPException(
            status_code=400, detail="Query must be at least 3 characters"
        )

    # Generate embedding for the search query
    query_embedding = await generate_embedding(
        query, min_length=3, task_type="retrieval_query"
    )

    if not query_embedding:
        raise HTTPException(
            status_code=500, detail="Failed to generate query embedding"
        )

    # Get all user's bookmarks with embeddings
    all_bookmarks = await db.bookmarks.find(
        {"user_id": current_user["id"], "embedding": {"$exists": True, "$ne": None}},
        {
            "_id": 0,
            "id": 1,
            "title": 1,
            "description": 1,
            "url": 1,
            "favicon": 1,
            "domain": 1,
            "thumbnail": 1,
            "created_at": 1,
            "embedding": 1,
            "entities": 1,
            "concepts": 1,
        },
    ).to_list(None)

    if not all_bookmarks:
        return {"results": [], "message": "No bookmarks with semantic data available"}

    def dot_product_similarity(vec1, vec2):
        return float(np.dot(vec1, vec2))

    # Calculate semantic scores for all bookmarks
    semantic_scores = []
    for bookmark in all_bookmarks:
        if bookmark.get("embedding"):
            sim = dot_product_similarity(query_embedding, bookmark["embedding"])
            semantic_scores.append((bookmark["id"], sim, bookmark))
    
    if not semantic_scores:
        return {"results": [], "message": "No bookmarks with embeddings"}

    # Calculate adaptive threshold based on score distribution
    scores_only = [s[1] for s in semantic_scores]
    if scores_only:
        mean_score = sum(scores_only) / len(scores_only)
        std_score = (sum((s - mean_score) ** 2 for s in scores_only) / len(scores_only)) ** 0.5
        # Adaptive threshold: at least 0.10, or mean - 1 std
        adaptive_threshold = max(0.10, mean_score - std_score)
    else:
        adaptive_threshold = 0.15

    # Build entity IDF for boosting
    entity_counts = {}
    for bookmark in all_bookmarks:
        for entity in bookmark.get("entities", []) + bookmark.get("concepts", []):
            entity_lower = entity.lower()
            entity_counts[entity_lower] = entity_counts.get(entity_lower, 0) + 1
    
    total_docs = len(all_bookmarks)
    entity_idf = {
        e: math.log((total_docs + 1) / (count + 1)) 
        for e, count in entity_counts.items()
    }

    # Extract entities from query (simple approach: use query tokens as potential entities)
    query_tokens = tokenize_text(query)
    
    # Build ranked lists for RRF
    # List 1: Semantic similarity
    semantic_ranked = sorted(semantic_scores, key=lambda x: x[1], reverse=True)[:100]
    
    # List 2: Entity/concept overlap (using query tokens as entity proxies)
    entity_scores = []
    for bookmark in all_bookmarks:
        all_doc_entities = bookmark.get("entities", []) + bookmark.get("concepts", [])
        boost = calculate_entity_boost(query_tokens, all_doc_entities, entity_idf)
        if boost > 0:
            entity_scores.append((bookmark["id"], boost, bookmark))
    entity_ranked = sorted(entity_scores, key=lambda x: x[1], reverse=True)[:100]

    # RRF fusion
    rrf_scores = reciprocal_rank_fusion([
        [(item[0], item[1]) for item in semantic_ranked],
        [(item[0], item[1]) for item in entity_ranked],
    ])

    # Build result set
    bookmark_map = {b["id"]: b for b in all_bookmarks}
    semantic_map = {item[0]: item[1] for item in semantic_scores}
    entity_map = {item[0]: item[1] for item in entity_scores}
    
    results = []
    for doc_id, rrf_score in rrf_scores.items():
        sem_score = semantic_map.get(doc_id, 0.0)
        
        # Apply adaptive threshold
        if sem_score < adaptive_threshold:
            continue
        
        bookmark = bookmark_map[doc_id].copy()
        bookmark.pop("embedding", None)
        bookmark["similarity_score"] = round(sem_score, 4)
        bookmark["entity_score"] = round(entity_map.get(doc_id, 0.0), 4)
        bookmark["rrf_score"] = round(rrf_score, 4)
        results.append(bookmark)

    # Sort by RRF score
    results.sort(key=lambda x: x["rrf_score"], reverse=True)
    top_results = results[:limit]

    message = None
    if not top_results:
        message = "No strongly matching bookmarks found. Try different search terms."

    return {
        "results": top_results,
        "query": query,
        "adaptive_threshold": round(adaptive_threshold, 4),
        "message": message,
    }


@api_router.get("/search")
async def hybrid_search(
    query: str,
    limit: int = 20,
    use_semantic: bool = True,
    use_keyword: bool = True,
    domain: Optional[str] = None,
    collection_id: Optional[str] = None,
    read_status: Optional[str] = None,
    current_user: dict = Depends(get_current_user_info),
):
    """
    Enhanced hybrid search using BM25 + Semantic + Entity boosting with RRF fusion.
    
    Improvements over basic hybrid:
    1. BM25 for proper lexical ranking (not just substring matching)
    2. Reciprocal Rank Fusion for robust score combination
    3. Adaptive weighting based on query type
    4. Entity/concept graph boosting
    5. Adaptive semantic thresholds
    """
    import numpy as np
    
    if not query or len(query.strip()) < 2:
        raise HTTPException(
            status_code=400, detail="Query must be at least 2 characters"
        )
    
    query_lower = query.lower().strip()
    query_tokens = tokenize_text(query)
    user_id = current_user["id"]
    
    # Detect query type for adaptive weighting
    query_type = detect_query_type(query)
    semantic_weight, keyword_weight = get_adaptive_weights(query_type)
    
    # Build base query with filters
    base_query = {"user_id": user_id}
    
    if domain:
        base_query["domain"] = domain
    
    if read_status == "read":
        base_query["read_status"] = True
    elif read_status == "unread":
        base_query["read_status"] = False
    
    if collection_id:
        collection = await db.collections.find_one(
            {"id": collection_id}, {"_id": 0, "bookmark_ids": 1}
        )
        if collection:
            base_query["id"] = {"$in": collection.get("bookmark_ids", [])}
    
    # Projection for candidates
    projection = {
        "_id": 0,
        "id": 1,
        "url": 1,
        "title": 1,
        "description": 1,
        "domain": 1,
        "thumbnail": 1,
        "favicon": 1,
        "reading_time": 1,
        "read_status": 1,
        "created_at": 1,
        "embedding": 1,
        "entities": 1,
        "concepts": 1,
        "text_content": 1,  # For BM25 scoring
    }
    
    # Fetch candidates (increased limit for better reranking)
    candidate_limit = min(500, limit * 25)
    all_candidates = await db.bookmarks.find(
        base_query, projection
    ).limit(candidate_limit).to_list(None)
    
    if not all_candidates:
        return {
            "results": [],
            "query": query,
            "total": 0,
            "search_mode": {"semantic": use_semantic, "keyword": use_keyword},
            "message": "No bookmarks found matching filters.",
        }
    
    # ========== BM25 SCORING ==========
    # Build document corpus for BM25
    doc_tokens_map = {}
    all_doc_lengths = []
    doc_freq = {}  # Term -> number of documents containing it
    
    for bookmark in all_candidates:
        # Combine searchable text fields (weighted by importance)
        title = bookmark.get("title") or ""
        description = bookmark.get("description") or ""
        text_content = (bookmark.get("text_content") or "")[:2000]  # Limit content
        entities = " ".join(bookmark.get("entities", []))
        concepts = " ".join(bookmark.get("concepts", []))
        
        # Weight title more by repeating it
        combined = f"{title} {title} {title} {description} {entities} {concepts} {text_content}"
        tokens = tokenize_text(combined)
        
        doc_tokens_map[bookmark["id"]] = tokens
        all_doc_lengths.append(len(tokens))
        
        # Count document frequency for each unique term
        for term in set(tokens):
            doc_freq[term] = doc_freq.get(term, 0) + 1
    
    avg_doc_len = sum(all_doc_lengths) / len(all_doc_lengths) if all_doc_lengths else 1.0
    total_docs = len(all_candidates)
    
    # Calculate BM25 scores
    bm25_scores = []
    for bookmark in all_candidates:
        doc_tokens = doc_tokens_map.get(bookmark["id"], [])
        score = calculate_bm25_score(
            query_tokens, doc_tokens, doc_freq, avg_doc_len, total_docs
        )
        if score > 0:
            bm25_scores.append((bookmark["id"], score))
    
    # Sort for ranking
    bm25_ranked = sorted(bm25_scores, key=lambda x: x[1], reverse=True)
    
    # ========== SEMANTIC SCORING ==========
    semantic_scores = []
    query_embedding = None
    
    if use_semantic and len(query.strip()) >= 3:
        query_embedding = await generate_embedding(
            query, min_length=3, task_type="retrieval_query"
        )
    
    if query_embedding:
        def dot_product_similarity(vec1, vec2):
            return float(np.dot(vec1, vec2))
        
        for bookmark in all_candidates:
            if bookmark.get("embedding"):
                sim = dot_product_similarity(query_embedding, bookmark["embedding"])
                semantic_scores.append((bookmark["id"], sim))
    
    semantic_ranked = sorted(semantic_scores, key=lambda x: x[1], reverse=True)
    
    # Calculate adaptive semantic threshold
    if semantic_scores:
        scores_only = [s[1] for s in semantic_scores]
        mean_score = sum(scores_only) / len(scores_only)
        std_score = (sum((s - mean_score) ** 2 for s in scores_only) / len(scores_only)) ** 0.5
        adaptive_threshold = max(0.10, mean_score - std_score)
    else:
        adaptive_threshold = 0.15
    
    # ========== ENTITY BOOSTING ==========
    # Build entity IDF
    entity_counts = {}
    for bookmark in all_candidates:
        for entity in bookmark.get("entities", []) + bookmark.get("concepts", []):
            entity_lower = entity.lower()
            entity_counts[entity_lower] = entity_counts.get(entity_lower, 0) + 1
    
    entity_idf = {
        e: math.log((total_docs + 1) / (count + 1)) 
        for e, count in entity_counts.items()
    }
    
    entity_scores = []
    for bookmark in all_candidates:
        all_doc_entities = bookmark.get("entities", []) + bookmark.get("concepts", [])
        boost = calculate_entity_boost(query_tokens, all_doc_entities, entity_idf)
        if boost > 0:
            entity_scores.append((bookmark["id"], boost))
    
    entity_ranked = sorted(entity_scores, key=lambda x: x[1], reverse=True)
    
    # ========== RRF FUSION ==========
    ranked_lists = []
    if use_keyword and bm25_ranked:
        ranked_lists.append(bm25_ranked[:100])
    if use_semantic and semantic_ranked:
        ranked_lists.append(semantic_ranked[:100])
    if entity_ranked:
        ranked_lists.append(entity_ranked[:100])
    
    if not ranked_lists:
        return {
            "results": [],
            "query": query,
            "total": 0,
            "search_mode": {"semantic": use_semantic, "keyword": use_keyword},
            "message": "No matching bookmarks found.",
        }
    
    rrf_scores = reciprocal_rank_fusion(ranked_lists)
    
    # Build lookup maps
    bookmark_map = {b["id"]: b for b in all_candidates}
    bm25_map = {item[0]: item[1] for item in bm25_scores}
    semantic_map = {item[0]: item[1] for item in semantic_scores}
    entity_map = {item[0]: item[1] for item in entity_scores}
    
    # ========== FINAL RANKING ==========
    results = []
    for doc_id, rrf_score in rrf_scores.items():
        sem_score = semantic_map.get(doc_id, 0.0)
        bm25_score_val = bm25_map.get(doc_id, 0.0)
        entity_score_val = entity_map.get(doc_id, 0.0)
        
        # Apply semantic threshold for semantic-only mode
        if use_semantic and not use_keyword and sem_score < adaptive_threshold:
            continue
        
        # Skip if no meaningful scores
        if rrf_score <= 0:
            continue
        
        bookmark = bookmark_map[doc_id].copy()
        bookmark.pop("embedding", None)
        bookmark.pop("text_content", None)
        
        # Normalize BM25 for display (0-1 scale based on max)
        max_bm25 = max((s[1] for s in bm25_scores), default=1.0)
        normalized_bm25 = bm25_score_val / max_bm25 if max_bm25 > 0 else 0.0
        
        bookmark["relevance_score"] = round(rrf_score, 4)
        bookmark["keyword_score"] = round(normalized_bm25, 4)
        bookmark["semantic_score"] = round(sem_score, 4) if sem_score else None
        bookmark["entity_score"] = round(entity_score_val, 4) if entity_score_val else None
        
        results.append(bookmark)
    
    # Sort by RRF score
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    top_results = results[:limit]
    
    # Fetch AI summaries for results
    if top_results:
        bookmark_ids = [b["id"] for b in top_results]
        summaries = await db.ai_summaries.find(
            {"bookmark_id": {"$in": bookmark_ids}}, {"_id": 0}
        ).to_list(None)
        summary_map = {s["bookmark_id"]: s for s in summaries}
        
        for bookmark in top_results:
            summary = summary_map.get(bookmark["id"])
            if summary:
                bookmark["ai_summary"] = summary
    
    message = None
    if not top_results:
        message = "No matching bookmarks found. Try different search terms."
    
    return {
        "results": top_results,
        "query": query,
        "total": len(top_results),
        "query_type": query_type,
        "adaptive_threshold": round(adaptive_threshold, 4),
        "search_mode": {
            "semantic": use_semantic,
            "keyword": use_keyword,
            "semantic_weight": semantic_weight,
            "keyword_weight": keyword_weight,
        },
        "message": message,
    }


@api_router.get("/knowledge-graph/expand-query")
async def expand_query(
    query: str,
    max_expansions: int = 10,
    current_user: dict = Depends(get_current_user_info),
):
    """
    Expand a search query using the knowledge graph.
    
    Returns related entities and concepts that could improve search results.
    Uses:
    1. Direct entity/concept matches in user's bookmarks
    2. Co-occurring entities (appear in same bookmarks)
    3. Embedding similarity for semantic expansions
    """
    import numpy as np
    
    if not query or len(query.strip()) < 2:
        raise HTTPException(
            status_code=400, detail="Query must be at least 2 characters"
        )
    
    query_lower = query.lower().strip()
    query_tokens = set(tokenize_text(query))
    
    # Get user's entities and concepts with their bookmark associations
    all_bookmarks = await db.bookmarks.find(
        {"user_id": current_user["id"]},
        {
            "_id": 0,
            "id": 1,
            "entities": 1,
            "concepts": 1,
            "embedding": 1,
        },
    ).limit(500).to_list(None)
    
    if not all_bookmarks:
        return {
            "query": query,
            "expansions": [],
            "related_entities": [],
            "related_concepts": [],
        }
    
    # Build entity/concept co-occurrence map
    entity_to_bookmarks = {}
    concept_to_bookmarks = {}
    
    for bookmark in all_bookmarks:
        bid = bookmark["id"]
        for entity in bookmark.get("entities", []):
            if entity not in entity_to_bookmarks:
                entity_to_bookmarks[entity] = set()
            entity_to_bookmarks[entity].add(bid)
        for concept in bookmark.get("concepts", []):
            if concept not in concept_to_bookmarks:
                concept_to_bookmarks[concept] = set()
            concept_to_bookmarks[concept].add(bid)
    
    # Find direct matches (entities/concepts containing query terms)
    direct_entity_matches = []
    direct_concept_matches = []
    
    for entity in entity_to_bookmarks.keys():
        entity_lower = entity.lower()
        if any(token in entity_lower for token in query_tokens):
            direct_entity_matches.append(entity)
    
    for concept in concept_to_bookmarks.keys():
        concept_lower = concept.lower()
        if any(token in concept_lower for token in query_tokens):
            direct_concept_matches.append(concept)
    
    # Find co-occurring entities/concepts (appear in same bookmarks as matched ones)
    matched_bookmark_ids = set()
    for entity in direct_entity_matches:
        matched_bookmark_ids.update(entity_to_bookmarks.get(entity, set()))
    for concept in direct_concept_matches:
        matched_bookmark_ids.update(concept_to_bookmarks.get(concept, set()))
    
    # Collect co-occurring terms with frequency counts
    cooccur_entities = {}
    cooccur_concepts = {}
    
    for bookmark in all_bookmarks:
        if bookmark["id"] in matched_bookmark_ids:
            for entity in bookmark.get("entities", []):
                if entity not in direct_entity_matches:
                    cooccur_entities[entity] = cooccur_entities.get(entity, 0) + 1
            for concept in bookmark.get("concepts", []):
                if concept not in direct_concept_matches:
                    cooccur_concepts[concept] = cooccur_concepts.get(concept, 0) + 1
    
    # Sort by frequency and take top items
    top_cooccur_entities = sorted(
        cooccur_entities.items(), key=lambda x: x[1], reverse=True
    )[:max_expansions]
    top_cooccur_concepts = sorted(
        cooccur_concepts.items(), key=lambda x: x[1], reverse=True
    )[:max_expansions]
    
    # Build expansion list (mix of direct and co-occurring)
    expansions = []
    
    # Add direct matches first (high relevance)
    for entity in direct_entity_matches[:5]:
        expansions.append({
            "term": entity,
            "type": "entity",
            "source": "direct_match",
            "relevance": 1.0,
        })
    for concept in direct_concept_matches[:5]:
        expansions.append({
            "term": concept,
            "type": "concept",
            "source": "direct_match",
            "relevance": 1.0,
        })
    
    # Add co-occurring terms (medium relevance)
    for entity, count in top_cooccur_entities[:5]:
        expansions.append({
            "term": entity,
            "type": "entity",
            "source": "co_occurrence",
            "relevance": round(min(count / 5.0, 0.8), 2),
        })
    for concept, count in top_cooccur_concepts[:5]:
        expansions.append({
            "term": concept,
            "type": "concept",
            "source": "co_occurrence",
            "relevance": round(min(count / 5.0, 0.8), 2),
        })
    
    # Sort by relevance and limit
    expansions.sort(key=lambda x: x["relevance"], reverse=True)
    
    return {
        "query": query,
        "expansions": expansions[:max_expansions],
        "related_entities": direct_entity_matches[:10] + [e[0] for e in top_cooccur_entities[:5]],
        "related_concepts": direct_concept_matches[:10] + [c[0] for c in top_cooccur_concepts[:5]],
        "total_entities_searched": len(entity_to_bookmarks),
        "total_concepts_searched": len(concept_to_bookmarks),
    }


@api_router.post("/knowledge-graph/regenerate-embeddings")
async def regenerate_embeddings(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_info),
):
    """
    Regenerate embeddings for all bookmarks that don't have them yet.
    This is a background task that processes bookmarks asynchronously.
    """
    # Count bookmarks that need embeddings
    needs_embedding_count = await db.bookmarks.count_documents(
        {
            "user_id": current_user["id"],
            "text_content": {"$exists": True, "$ne": None},
            "$or": [{"embedding": {"$exists": False}}, {"embedding": None}],
        }
    )

    if needs_embedding_count == 0:
        return {
            "message": "All bookmarks already have embeddings",
            "processed": 0,
            "status": "completed",
        }

    # Start background processing
    async def process_embeddings():
        bookmarks = await db.bookmarks.find(
            {
                "user_id": current_user["id"],
                "text_content": {"$exists": True, "$ne": None},
                "$or": [{"embedding": {"$exists": False}}, {"embedding": None}],
            },
            {"_id": 0, "id": 1, "text_content": 1, "title": 1, "description": 1},
        ).to_list(None)

        processed = 0
        for bookmark in bookmarks:
            try:
                text_content = bookmark.get("text_content", "")
                if text_content and len(text_content.strip()) >= 50:
                    embedding = await generate_embedding(
                        text_content,
                        bookmark.get("title", ""),
                        bookmark.get("description", ""),
                    )

                    if embedding:
                        # Get AI summary for entity/concept extraction
                        ai_summary = await db.ai_summaries.find_one(
                            {"bookmark_id": bookmark["id"]}, {"_id": 0}
                        )
                        entities, concepts = await extract_entities_and_concepts(
                            text_content, ai_summary
                        )

                        update_data = {
                            "embedding": embedding,
                            "embedding_model": "text-embedding-004",
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }

                        if entities:
                            update_data["entities"] = entities
                        if concepts:
                            update_data["concepts"] = concepts

                        await db.bookmarks.update_one(
                            {"id": bookmark["id"]}, {"$set": update_data}
                        )
                        processed += 1
                        logger.info(
                            f"Generated embedding for bookmark {bookmark['id']} ({processed}/{len(bookmarks)})"
                        )

            except Exception as e:
                logger.exception(
                    f"Error generating embedding for bookmark {bookmark.get('id')}"
                )

        logger.info(
            f"Completed embedding regeneration: {processed}/{len(bookmarks)} processed"
        )

    background_tasks.add_task(process_embeddings)

    return {
        "message": f"Started regenerating embeddings for {needs_embedding_count} bookmarks",
        "queued": needs_embedding_count,
        "status": "processing",
    }


@api_router.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: str, current_user: dict = Depends(get_current_user_info)
):
    result = await db.bookmarks.delete_one(
        {"id": bookmark_id, "user_id": current_user["id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.ai_summaries.delete_one({"bookmark_id": bookmark_id})
    await db.collections.update_many(
        {"user_id": current_user["id"]}, {"$pull": {"bookmark_ids": bookmark_id}}
    )

    return {"message": "Bookmark deleted"}


@api_router.post("/bookmarks/bulk-delete")
@limiter.limit("10/minute")  # IP-based rate limiting
@limiter.limit("50/hour", key_func=get_user_identifier)  # User-based rate limiting
async def bulk_delete_bookmarks(
    request: Request,
    bookmark_ids: List[str],
    current_user: dict = Depends(get_current_user_info),
):
    result = await db.bookmarks.delete_many(
        {"id": {"$in": bookmark_ids}, "user_id": current_user["id"]}
    )
    await db.ai_summaries.delete_many({"bookmark_id": {"$in": bookmark_ids}})
    await db.collections.update_many(
        {"user_id": current_user["id"]},
        {"$pull": {"bookmark_ids": {"$in": bookmark_ids}}},
    )
    return {
        "message": f"Deleted {result.deleted_count} bookmarks",
        "count": result.deleted_count,
    }


@api_router.patch("/bookmarks/{bookmark_id}/read-status")
async def update_read_status(
    bookmark_id: str,
    read_status: bool,
    current_user: dict = Depends(get_current_user_info),
):
    result = await db.bookmarks.update_one(
        {"id": bookmark_id, "user_id": current_user["id"]},
        {
            "$set": {
                "read_status": read_status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"message": "Read status updated"}


@api_router.post("/bookmarks/bulk-mark-read")
@limiter.limit("10/minute")  # IP-based rate limiting
@limiter.limit("50/hour", key_func=get_user_identifier)  # User-based rate limiting
async def bulk_mark_read(
    request: Request,
    bookmark_ids: List[str],
    read_status: bool,
    current_user: dict = Depends(get_current_user_info),
):
    result = await db.bookmarks.update_many(
        {"id": {"$in": bookmark_ids}, "user_id": current_user["id"]},
        {
            "$set": {
                "read_status": read_status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    return {
        "message": f"Updated {result.modified_count} bookmarks",
        "count": result.modified_count,
    }


# Phase 1: Access Tracking & Aging Endpoints


@api_router.post("/bookmarks/{bookmark_id}/accessed")
async def track_bookmark_access(
    bookmark_id: str,
    source: str = "detail",  # "detail" or "external"
    current_user: dict = Depends(get_current_user_info),
):
    """
    Track when a bookmark is meaningfully accessed.
    Called when user views detail page or opens external URL.
    """
    # Validate ownership
    bookmark = await db.bookmarks.find_one(
        {"id": bookmark_id, "user_id": current_user["id"]}
    )
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    now = datetime.now(timezone.utc).isoformat()

    # Atomic update with tracking
    await db.bookmarks.update_one(
        {"id": bookmark_id},
        {
            "$set": {"last_accessed": now},
            "$inc": {"view_count": 1},
            "$push": {
                "access_history": {
                    "$each": [{"timestamp": now, "source": source}],
                    "$slice": -20,  # Keep only last 20
                }
            },
        },
    )

    return {"status": "tracked", "timestamp": now}


@api_router.get("/bookmarks/duplicates/detect")
async def detect_duplicates(current_user: dict = Depends(get_current_user_info)):
    projection = {
        "_id": 0,
        "id": 1,
        "url": 1,
        "title": 1,
        "text_content": 1,
        "domain": 1,
        "created_at": 1,
        "thumbnail": 1,
        "favicon": 1,
    }
    bookmarks = (
        await db.bookmarks.find({"user_id": current_user["id"]}, projection)
        .limit(500)
        .to_list(None)
    )

    url_groups = {}
    for bookmark in bookmarks:
        normalized_url = re.sub(r"(\?|#).*$", "", bookmark["url"]).lower().strip("/")
        if normalized_url not in url_groups:
            url_groups[normalized_url] = []
        url_groups[normalized_url].append(bookmark)

    duplicates = []
    for url, group in url_groups.items():
        if len(group) > 1:
            duplicates.append({"type": "exact_url", "bookmarks": group})

    texts = [
        b.get("text_content", "")[:1000] for b in bookmarks if b.get("text_content")
    ]
    if len(texts) > 1:
        try:
            vectorizer = TfidfVectorizer(max_features=100)
            tfidf_matrix = vectorizer.fit_transform(texts)
            similarities = cosine_similarity(tfidf_matrix)

            for i in range(len(bookmarks)):
                for j in range(i + 1, len(bookmarks)):
                    if similarities[i][j] > 0.85:
                        duplicates.append(
                            {
                                "type": "similar_content",
                                "similarity": float(similarities[i][j]),
                                "bookmarks": [bookmarks[i], bookmarks[j]],
                            }
                        )
        except Exception:
            pass

    return {"duplicates": duplicates}


@api_router.post("/bookmarks/merge")
async def merge_bookmarks(
    bookmark_ids: List[str], current_user: dict = Depends(get_current_user_info)
):
    if len(bookmark_ids) < 2:
        raise HTTPException(
            status_code=400, detail="Need at least 2 bookmarks to merge"
        )

    bookmarks = await db.bookmarks.find(
        {"id": {"$in": bookmark_ids}, "user_id": current_user["id"]}, {"_id": 0}
    ).to_list(100)
    if len(bookmarks) < 2:
        raise HTTPException(status_code=404, detail="Bookmarks not found")

    keep_bookmark = bookmarks[0]
    delete_ids = [b["id"] for b in bookmarks[1:]]

    await db.bookmarks.delete_many({"id": {"$in": delete_ids}})
    await db.ai_summaries.delete_many({"bookmark_id": {"$in": delete_ids}})

    return {"message": "Bookmarks merged", "kept_bookmark": keep_bookmark}


@api_router.post("/collections", response_model=Collection)
async def create_collection(
    collection_data: CollectionCreate,
    current_user: dict = Depends(get_current_user_info),
):
    collection = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "name": collection_data.name,
        "bookmark_ids": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.collections.insert_one(collection)
    return Collection(**collection)


@api_router.get("/collections", response_model=List[Collection])
async def get_collections(current_user: dict = Depends(get_current_user_info)):
    collections = (
        await db.collections.find({"user_id": current_user["id"]}, {"_id": 0})
        .limit(100)
        .to_list(None)
    )
    return [Collection(**c) for c in collections]


@api_router.post("/collections/{collection_id}/add")
async def add_to_collection(
    collection_id: str,
    data: AddToCollection,
    current_user: dict = Depends(get_current_user_info),
):
    result = await db.collections.update_one(
        {"id": collection_id, "user_id": current_user["id"]},
        {"$addToSet": {"bookmark_ids": data.bookmark_id}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"message": "Bookmark added to collection"}


@api_router.post("/bookmarks/import")
@limiter.limit("3/hour")  # Limit imports to prevent abuse
async def import_bookmarks(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_info),
):
    """Import bookmarks from browser HTML file"""
    try:
        # Read file content from request body
        file = await request.body()

        # Validate file exists
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")

        # Validate file size (max 10MB)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if len(file) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 10MB)")

        # Decode and validate file is valid UTF-8 HTML
        try:
            html_content = file.decode("utf-8") if isinstance(file, bytes) else file
        except UnicodeDecodeError:
            logger.warning(
                f"User {current_user['id']} attempted to import non-UTF-8 file"
            )
            raise HTTPException(
                status_code=400, detail="File must be UTF-8 encoded HTML"
            )

        # Validate file contains content
        if not html_content or len(html_content.strip()) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Detect file format: HTML bookmark file, CSV, or plain text URL list
        html_lower = html_content.lower()
        is_html_format = "<a" in html_lower or "<A" in html_lower

        # Detect CSV format (looks for comma-separated values)
        lines = html_content.strip().split("\n")
        is_csv_format = False
        if not is_html_format and len(lines) > 0:
            # Check if first few lines contain commas (likely CSV)
            first_lines = lines[:5]
            comma_count = sum(1 for line in first_lines if "," in line)
            is_csv_format = (
                comma_count >= len(first_lines) * 0.5
            )  # At least 50% have commas

        urls_to_import = []
        MAX_BOOKMARKS_PER_IMPORT = 1000

        if is_html_format:
            # Process HTML bookmark file (browser export format)
            soup = BeautifulSoup(html_content, "html.parser")
            links = soup.find_all("a")

            if not links or len(links) == 0:
                logger.warning(
                    f"User {current_user['id']} imported HTML file with no parseable bookmarks"
                )
                raise HTTPException(
                    status_code=400, detail="No bookmarks found in HTML file"
                )

            for link in links[:MAX_BOOKMARKS_PER_IMPORT]:
                url = link.get("href")
                title = link.get_text(strip=True)

                if url and url.startswith("http"):
                    urls_to_import.append(
                        {"url": url, "title": title or urlparse(url).netloc}
                    )

        elif is_csv_format:
            # Process CSV file (URL in first column, optional title in second column)
            for line in lines[:MAX_BOOKMARKS_PER_IMPORT]:
                line = line.strip()
                if not line:
                    continue

                # Split by comma
                parts = [p.strip().strip('"').strip("'") for p in line.split(",")]

                if len(parts) == 0:
                    continue

                url = parts[0]
                title = parts[1] if len(parts) > 1 and parts[1] else None

                # Skip header row (common CSV headers)
                if url.lower() in ["url", "link", "website", "address", "bookmark"]:
                    continue

                # Only import valid HTTP(S) URLs
                if url and url.startswith("http"):
                    urls_to_import.append(
                        {"url": url, "title": title or urlparse(url).netloc}
                    )

        else:
            # Process plain text URL list (one URL per line)
            for line in lines[:MAX_BOOKMARKS_PER_IMPORT]:
                url = line.strip()

                # Skip empty lines and non-URL lines
                if not url or not url.startswith("http"):
                    continue

                urls_to_import.append({"url": url, "title": urlparse(url).netloc})

        # Validate at least one URL was found
        if not urls_to_import:
            raise HTTPException(status_code=400, detail="No valid URLs found in file")

        logger.info(
            f"User {current_user['id']} importing {len(urls_to_import)} bookmarks"
        )

        # Create import job
        import_job = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "total_bookmarks": len(urls_to_import),
            "content_fetched": 0,
            "ai_processed": 0,
            "failed": 0,
            "status": "processing",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "estimated_completion_time": None,
        }
        await db.import_jobs.insert_one(import_job)

        # Create placeholder bookmarks
        bookmark_ids = []
        imported_count = 0

        for item in urls_to_import:
            url = item["url"]
            title = item["title"]

            if url and url.startswith("http"):
                bookmark = {
                    "id": str(uuid.uuid4()),
                    "user_id": current_user["id"],
                    "url": url,
                    "title": title or urlparse(url).netloc,
                    "description": None,
                    "favicon": None,
                    "thumbnail": None,
                    "html_content": None,
                    "text_content": None,
                    "domain": urlparse(url).netloc,
                    "reading_time": None,
                    "read_status": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                await db.bookmarks.insert_one(bookmark)

                ai_summary = {
                    "id": str(uuid.uuid4()),
                    "bookmark_id": bookmark["id"],
                    "processing_status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.ai_summaries.insert_one(ai_summary)

                bookmark_ids.append(bookmark["id"])
                imported_count += 1

        # Start background bulk processing
        if background_tasks and bookmark_ids:
            background_tasks.add_task(
                process_bulk_import, import_job["id"], bookmark_ids, current_user["id"]
            )

        logger.info(
            f"Successfully imported {imported_count} bookmarks for user {current_user['id']}"
        )
        return {
            "message": f"Imported {imported_count} bookmarks",
            "count": imported_count,
            "import_job_id": import_job["id"],
        }
    except HTTPException:
        # Re-raise HTTP exceptions as-is (these are validation errors with proper messages)
        raise
    except Exception as e:
        logger.exception(
            f"Error importing bookmarks for user {current_user['id']}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to import bookmarks: {str(e)}"
        )


@api_router.get("/import-jobs/{job_id}")
async def get_import_job(
    job_id: str, current_user: dict = Depends(get_current_user_info)
):
    """Get import job progress"""
    job = await db.import_jobs.find_one(
        {"id": job_id, "user_id": current_user["id"]}, {"_id": 0}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return job


@api_router.get("/import-jobs")
async def get_import_jobs(current_user: dict = Depends(get_current_user_info)):
    """Get all import jobs for user"""
    jobs = (
        await db.import_jobs.find({"user_id": current_user["id"]}, {"_id": 0})
        .sort("created_at", -1)
        .limit(50)
        .to_list(None)
    )
    return jobs


@api_router.get("/bookmarks/export")
async def export_bookmarks(current_user: dict = Depends(get_current_user_info)):
    """Export bookmarks as browser-compatible HTML"""
    projection = {"_id": 0, "url": 1, "title": 1, "created_at": 1}
    bookmarks = (
        await db.bookmarks.find({"user_id": current_user["id"]}, projection)
        .sort("created_at", -1)
        .limit(5000)
        .to_list(None)
    )

    html_parts = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Arivu Bookmarks</TITLE>",
        "<H1>Arivu Bookmarks</H1>",
        "<DL><p>",
    ]

    for bookmark in bookmarks:
        add_date = int(datetime.fromisoformat(bookmark["created_at"]).timestamp())
        title = bookmark.get("title", bookmark.get("url", "Untitled"))
        url = bookmark.get("url", "")
        html_parts.append(f'    <DT><A HREF="{url}" ADD_DATE="{add_date}">{title}</A>')

    html_parts.append("</DL><p>")

    from fastapi.responses import Response

    return Response(
        content="\n".join(html_parts),
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="arivu_bookmarks_{datetime.now().strftime("%Y%m%d")}.html"'
        },
    )


@api_router.post("/bookmarks/backup")
async def backup_bookmarks(
    backup_request: BackupRequest,
    current_user: dict = Depends(get_current_user_info)
):
    """
    Generate a comprehensive backup of bookmarks with options.
    
    Formats:
    - html: Browser-compatible bookmark file
    - json: Full data export with nested AI summaries and notes
    - csv: Spreadsheet-friendly format
    """
    from fastapi.responses import Response
    import json
    import csv
    import io

    # Build query with date filtering
    query = {"user_id": current_user["id"]}
    if backup_request.date_from:
        query["created_at"] = {"$gte": backup_request.date_from.isoformat()}
    if backup_request.date_to:
        if "created_at" in query:
            query["created_at"]["$lte"] = backup_request.date_to.isoformat()
        else:
            query["created_at"] = {"$lte": backup_request.date_to.isoformat()}

    # Fetch bookmarks
    bookmarks = (
        await db.bookmarks.find(query, {"_id": 0, "embedding": 0, "html_content": 0})
        .sort("created_at", -1)
        .limit(10000)
        .to_list(None)
    )

    # Optionally fetch AI summaries
    if backup_request.include_ai_summaries and bookmarks:
        bookmark_ids = [b["id"] for b in bookmarks]
        summaries = await db.ai_summaries.find(
            {"bookmark_id": {"$in": bookmark_ids}},
            {"_id": 0}
        ).to_list(None)
        summaries_map = {s["bookmark_id"]: s for s in summaries}
        
        for bookmark in bookmarks:
            if bookmark["id"] in summaries_map:
                bookmark["ai_summary"] = summaries_map[bookmark["id"]]

    # Optionally fetch notes
    if backup_request.include_notes and bookmarks:
        bookmark_ids = [b["id"] for b in bookmarks]
        notes = await db.notes.find(
            {"bookmark_id": {"$in": bookmark_ids}, "user_id": current_user["id"]},
            {"_id": 0}
        ).to_list(None)
        notes_map = {}
        for note in notes:
            bid = note["bookmark_id"]
            if bid not in notes_map:
                notes_map[bid] = []
            notes_map[bid].append(note)
        
        for bookmark in bookmarks:
            if bookmark["id"] in notes_map:
                bookmark["notes"] = notes_map[bookmark["id"]]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Generate output based on format
    if backup_request.format == "json":
        content = json.dumps({
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_bookmarks": len(bookmarks),
            "include_notes": backup_request.include_notes,
            "include_ai_summaries": backup_request.include_ai_summaries,
            "bookmarks": bookmarks
        }, indent=2, default=str)
        
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="arivu_backup_{timestamp}.json"'
            }
        )

    elif backup_request.format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header row
        headers = ["url", "title", "domain", "created_at", "read_status", "reading_time"]
        if backup_request.include_ai_summaries:
            headers.extend(["summary", "tags"])
        if backup_request.include_notes:
            headers.append("notes")
        writer.writerow(headers)
        
        # Data rows
        for b in bookmarks:
            row = [
                b.get("url", ""),
                b.get("title", ""),
                b.get("domain", ""),
                b.get("created_at", ""),
                b.get("read_status", False),
                b.get("reading_time", ""),
            ]
            if backup_request.include_ai_summaries:
                ai = b.get("ai_summary", {})
                row.append(ai.get("one_sentence", ""))
                row.append(", ".join(ai.get("suggested_tags", [])))
            if backup_request.include_notes:
                notes = b.get("notes", [])
                row.append(" | ".join([n.get("content", "") for n in notes]))
            writer.writerow(row)
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="arivu_backup_{timestamp}.csv"'
            }
        )

    else:  # HTML format (default)
        html_parts = [
            "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            "<TITLE>Arivu Bookmarks Backup</TITLE>",
            "<H1>Arivu Bookmarks Backup</H1>",
            f"<!-- Exported: {datetime.now(timezone.utc).isoformat()} -->",
            f"<!-- Total: {len(bookmarks)} bookmarks -->",
            "<DL><p>",
        ]

        for bookmark in bookmarks:
            add_date = int(datetime.fromisoformat(bookmark["created_at"]).timestamp())
            title = bookmark.get("title", bookmark.get("url", "Untitled"))
            url = bookmark.get("url", "")
            tags = ""
            if backup_request.include_ai_summaries:
                ai = bookmark.get("ai_summary", {})
                tag_list = ai.get("suggested_tags", [])
                if tag_list:
                    tags = f' TAGS="{",".join(tag_list)}"'
            html_parts.append(f'    <DT><A HREF="{url}" ADD_DATE="{add_date}"{tags}>{title}</A>')

        html_parts.append("</DL><p>")

        return Response(
            content="\n".join(html_parts),
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="arivu_backup_{timestamp}.html"'
            }
        )


# ============================================
# Content Intelligence APIs (Roadmap 11)
# ============================================


class ContentEvaluateRequest(BaseModel):
    url: str
    content: Optional[str] = None
    metadata: Optional[Dict] = None


@api_router.post("/content/evaluate")
async def evaluate_content(
    request_data: ContentEvaluateRequest,
    current_user: dict = Depends(get_current_user_info),
):
    """
    Evaluate content quality before saving.
    Returns credibility score, quality label, and badges.
    """
    score, breakdown = calculate_credibility_score(
        request_data.url, request_data.content, request_data.metadata
    )

    label, severity = get_quality_label(score)
    badges = get_quality_badges(breakdown)

    return {
        "score": score,
        "label": label,
        "severity": severity,
        "badges": badges,
        "breakdown": breakdown,
    }


class DuplicateCheckRequest(BaseModel):
    url: str


@api_router.post("/content/check-duplicate")
async def check_duplicate(
    request_data: DuplicateCheckRequest,
    current_user: dict = Depends(get_current_user_info),
):
    """
    Check if URL already exists for this user before saving.
    Returns duplicate status and existing bookmark if found.
    """
    result = await check_duplicate_url(request_data.url, current_user["id"], db)

    return result


# ============================================
# Learning Analytics APIs (Roadmap 12)
# ============================================


@api_router.get("/analytics/reading-stats")
async def get_analytics_reading_stats(
    days: int = 30, current_user: dict = Depends(get_current_user_info)
):
    """
    Get reading statistics for the user.
    """
    stats = await calculate_reading_stats(current_user["id"], days, db)
    return stats


@api_router.get("/analytics/topics")
async def get_analytics_topics(
    days: int = 30, current_user: dict = Depends(get_current_user_info)
):
    """
    Get topic breakdown based on AI-suggested tags.
    """
    topics = await get_topic_breakdown(current_user["id"], days, db)
    return {"topics": topics}


@api_router.get("/analytics/patterns")
async def get_analytics_patterns(
    days: int = 30, current_user: dict = Depends(get_current_user_info)
):
    """
    Get reading patterns (time of day, day of week).
    """
    patterns = await get_reading_patterns(current_user["id"], days, db)
    return patterns


@api_router.get("/analytics/insights")
async def get_analytics_insights(current_user: dict = Depends(get_current_user_info)):
    """
    Get behavioral insights and recommendations.
    """
    insights = await get_learning_insights(current_user["id"], db)
    return {"insights": insights}


@api_router.get("/analytics/summary")
async def get_analytics_summary(
    days: int = 30, current_user: dict = Depends(get_current_user_info)
):
    """
    Get complete analytics summary (stats + topics + patterns + insights).
    """
    stats = await calculate_reading_stats(current_user["id"], days, db)
    topics = await get_topic_breakdown(current_user["id"], days, db)
    patterns = await get_reading_patterns(current_user["id"], days, db)
    insights = await get_learning_insights(current_user["id"], db)

    return {
        "stats": stats,
        "topics": topics,
        "patterns": patterns,
        "insights": insights,
    }


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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
