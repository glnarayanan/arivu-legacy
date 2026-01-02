from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks, Request
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Enhanced Rate limiter for Gemini API with multi-dimensional tracking
class EnhancedGeminiRateLimiter:
    def __init__(
        self,
        max_rpm=500,              # 50% of 1000 RPM limit (conservative)
        max_tpm=500000,           # 50% of 1M tokens/minute
        max_daily=5000            # 50% of 10K requests/day
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
                logger.debug(f"Dynamic throttling: RPM={rpm_utilization:.0%}, TPM={tpm_utilization:.0%}")

            # Hard limit: must wait if at capacity
            if current_rpm >= self.max_rpm:
                oldest_request = self.rpm_bucket[0][0]
                wait_time = max(wait_time, 60 - (now - oldest_request) + 0.1)

            if current_tpm + estimated_tokens >= self.max_tpm:
                oldest_tokens = self.tpm_bucket[0][0]
                wait_time = max(wait_time, 60 - (now - oldest_tokens) + 0.1)

            # Check daily limit (hard stop)
            if current_daily >= self.max_daily:
                logger.error(f"Daily Gemini API quota exceeded: {current_daily}/{self.max_daily}")
                raise Exception("Daily Gemini API quota exceeded. Please try again tomorrow.")

            # 5. Wait if needed
            if wait_time > 0:
                logger.info(f"Rate limiting: waiting {wait_time:.1f}s (RPM: {rpm_utilization:.0%}, TPM: {tpm_utilization:.0%}, Daily: {current_daily}/{self.max_daily})")
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
                self.total_tokens_today += (actual_tokens - estimated)

gemini_rate_limiter = EnhancedGeminiRateLimiter(
    max_rpm=500,        # 50% of 1000 RPM (conservative buffer)
    max_tpm=500000,     # 50% of 1M tokens/min
    max_daily=5000      # 50% of 10K requests/day
)

# Configure structured logging
logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO').upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

mongo_url = os.environ['MONGO_URL']
# Configure MongoDB client with timeouts to prevent hanging connections
client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=5000,      # 5 second timeout for server selection
    connectTimeoutMS=10000,              # 10 second timeout for initial connection
    socketTimeoutMS=30000,               # 30 second timeout for socket operations
    maxPoolSize=50,                      # Limit connection pool size
    maxIdleTimeMS=45000,                 # Close idle connections after 45 seconds
    waitQueueTimeoutMS=10000,            # 10 second timeout waiting for connection from pool
    retryWrites=True,                    # Enable retry for write operations
    retryReads=True                      # Enable retry for read operations
)
db_name = os.environ.get('DB_NAME', 'arivu_db')
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
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
    except:
        pass
    # Fallback to IP-based rate limiting
    return f"ip:{get_remote_address(request)}"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Validate SECRET_KEY is set and strong
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY or len(SECRET_KEY) < 32:
    logger.error("SECRET_KEY must be set and at least 32 characters long")
    raise ValueError("SECRET_KEY must be set and at least 32 characters long")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour for access tokens
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days for refresh tokens

# Security validation functions
def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets security requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, ""

def is_safe_url(url: str) -> tuple[bool, str]:
    """Validate URL to prevent SSRF attacks (non-blocking validation)"""
    try:
        parsed = urlparse(url)

        # Only allow http/https schemes
        if parsed.scheme not in ['http', 'https']:
            return False, "Only HTTP and HTTPS URLs are allowed"

        # Must have a hostname
        if not parsed.hostname:
            return False, "Invalid URL: missing hostname"

        hostname = parsed.hostname.lower()

        # Block localhost and loopback addresses (check hostname directly)
        if hostname in ['localhost', '127.0.0.1', '0.0.0.0', '::1', '[::1]']:
            return False, "Cannot fetch from localhost or loopback addresses"

        # Block private hostnames
        if hostname.endswith('.local') or hostname.endswith('.localhost'):
            return False, "Cannot fetch from local network addresses"

        # Block private IP ranges (check if hostname is already an IP)
        try:
            # If hostname is an IP address, validate it directly (no DNS lookup needed)
            ip_obj = ipaddress.ip_address(hostname)

            # Block private, loopback, link-local, and reserved ranges
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                return False, "Cannot fetch from private or reserved IP addresses"

            # Block cloud metadata endpoints (AWS, GCP, Azure)
            if str(ip_obj) == '169.254.169.254':
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

    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Name cannot be empty')
        if len(v) > 100:
            raise ValueError('Name too long (max 100 characters)')
        if not re.match(r'^[\w\s\-\.]+$', v):
            raise ValueError('Name contains invalid characters')
        return v.strip()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class BookmarkCreate(BaseModel):
    url: str
    collection_id: Optional[str] = None

    @validator('url')
    def validate_url(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('URL cannot be empty')
        if len(v) > 2048:
            raise ValueError('URL too long (max 2048 characters)')

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

    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Collection name cannot be empty')
        if len(v) > 100:
            raise ValueError('Collection name too long (max 100 characters)')
        if not re.match(r'^[\w\s\-\.]+$', v):
            raise ValueError('Collection name contains invalid characters')
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
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate access token and return current user"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Verify this is an access token
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Health check endpoint for Docker/Kubernetes
@api_router.get("/health")
async def health_check():
    """Health check endpoint for monitoring and container orchestration."""
    try:
        # Check database connectivity
        await db.command('ping')
        return {
            "status": "healthy",
            "service": "arivu-backend",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )

@api_router.post("/auth/signup", response_model=TokenResponse)
@limiter.limit("3/hour")  # Limit signups to prevent abuse
async def signup(request: Request, user_data: UserSignup):
    """Register a new user with password validation"""
    # SIGNUPS DISABLED: Only existing users can login
    # To re-enable signups, remove or comment out the following block
    logger.info(f"Signup attempt blocked (signups disabled): {user_data.email}")
    raise HTTPException(
        status_code=403,
        detail="Signups are currently disabled. Only existing users can log in."
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
        "created_at": datetime.now(timezone.utc).isoformat()
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
        "user": user_response
    }

@api_router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # Prevent brute force attacks
async def login(request: Request, login_data: UserLogin):
    """Authenticate user and return tokens"""
    user = await db.users.find_one({"email": login_data.email})
    if not user or not pwd_context.verify(login_data.password, user["password_hash"]):
        logger.warning(f"Login failed: invalid credentials for {login_data.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create tokens
    access_token = create_access_token(data={"sub": user["id"]})
    refresh_token = create_refresh_token(data={"sub": user["id"]})

    user_response = {"id": user["id"], "email": user["email"], "name": user["name"]}
    logger.info(f"User logged in successfully: {user['id']}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_response
    }

@api_router.post("/auth/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token_endpoint(request: Request, token_data: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    try:
        payload = jwt.decode(token_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        # Verify this is a refresh token
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Verify user still exists
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        # Create new tokens
        new_access_token = create_access_token(data={"sub": user_id})
        new_refresh_token = create_refresh_token(data={"sub": user_id})

        user_response = {"id": user["id"], "email": user["email"], "name": user["name"]}
        logger.info(f"Tokens refreshed for user: {user_id}")

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": user_response
        }
    except jwt.ExpiredSignatureError:
        logger.info("Refresh token expired")
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        logger.warning("Invalid refresh token")
        raise HTTPException(status_code=401, detail="Invalid refresh token")

async def fetch_webpage_content(url: str):
    """Fetch and parse webpage content with security validation"""
    try:
        # Validate URL is safe before fetching
        is_safe, error_msg = is_safe_url(url)
        if not is_safe:
            logger.warning(f"Unsafe URL blocked: {error_msg}")
            raise ValueError(f"Unsafe URL: {error_msg}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
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
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content')
        
        favicon = None
        favicon_tag = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
        if favicon_tag and favicon_tag.get('href'):
            favicon_url = favicon_tag.get('href')
            if favicon_url.startswith('//'):
                favicon = 'https:' + favicon_url
            elif favicon_url.startswith('/'):
                parsed = urlparse(url)
                favicon = f"{parsed.scheme}://{parsed.netloc}{favicon_url}"
            elif not favicon_url.startswith('http'):
                parsed = urlparse(url)
                favicon = f"{parsed.scheme}://{parsed.netloc}/{favicon_url}"
            else:
                favicon = favicon_url
        
        thumbnail = None
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        if og_image and og_image.get('content'):
            thumbnail = og_image.get('content')
        
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0
        text_content = h.handle(summary_html)
        text_content = text_content.strip() if text_content else ""

        if not text_content or len(text_content) < 100:
            cleaned_soup = BeautifulSoup(summary_html, 'html.parser')
            paragraphs = cleaned_soup.find_all(['p', 'article', 'section'])
            text_parts = []
            for p in paragraphs:
                text = p.get_text(separator=' ', strip=True)
                if len(text) > 50:
                    text_parts.append(text)
            if text_parts:
                text_content = '\n\n'.join(text_parts)

        if not text_content or len(text_content) < 50:
            text_content = soup.get_text(separator='\n', strip=True)
            text_content = text_content if text_content else ""
        
        text_content = ' '.join(text_content.split())[:10000]
        
        logger.info(f"Successfully fetched content from {urlparse(url).netloc}")
        return {
            'title': title.strip() if title else urlparse(url).netloc,
            'description': description,
            'favicon': favicon,
            'thumbnail': thumbnail,
            'html_content': summary_html,
            'text_content': text_content,
            'domain': urlparse(url).netloc
        }
    except Exception as e:
        # Sanitize URL in logs - remove query params and fragments
        safe_url = urlparse(url)._replace(query='', fragment='').geturl()
        logger.error(f"Error fetching webpage from domain {urlparse(url).netloc}: {type(e).__name__}: {str(e)}", exc_info=True)
        return {
            'title': urlparse(url).netloc,
            'domain': urlparse(url).netloc,
            'text_content': f"Failed to fetch content",
            'html_content': ''
        }

async def generate_ai_summaries(text_content: str, bookmark_id: str):
    """Generate AI summaries for bookmark content with timeout protection"""
    try:
        # Wrap AI processing with 60-second timeout to prevent hanging
        return await asyncio.wait_for(
            _generate_ai_summaries_impl(text_content, bookmark_id),
            timeout=60.0
        )
    except asyncio.TimeoutError:
        logger.error(f"AI summary generation timed out for bookmark {bookmark_id}")
        await db.ai_summaries.update_one(
            {"bookmark_id": bookmark_id},
            {"$set": {
                "processing_status": "failed",
                "one_sentence": "AI processing timed out",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        return {"processing_status": "failed"}
    except Exception as e:
        logger.error(f"Error in AI summary wrapper for bookmark {bookmark_id}: {type(e).__name__}")
        return {"processing_status": "failed"}

async def _generate_ai_summaries_impl(text_content: str, bookmark_id: str):
    """Internal implementation of AI summary generation"""
    try:
        if not text_content or len(text_content.strip()) < 50:
            logger.info(f"Insufficient content for AI processing: bookmark {bookmark_id}")
            raise ValueError("Insufficient content for AI processing")

        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY not configured")
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        content_snippet = text_content[:4000].strip()

        # Define all prompts upfront
        prompts = {
            'one_sentence': f"""You are a factual summarizer. Create ONE concise sentence (max 20 words) summarizing the main point. Be direct and factual.

Summarize in ONE sentence:

{content_snippet}""",
            'bullets': f"""Extract exactly 3 key bullet points. Format as:
- Point 1
- Point 2
- Point 3
Be factual and concise.

Extract 3 key points:

{content_snippet}""",
            'long_form': f"""Create a comprehensive summary (150-200 words) with clear sections. Be factual and well-structured.

Create a detailed summary with Overview, Key Facts, and Main Points:

{content_snippet}""",
            'highlights': f"""Extract 3-5 important direct quotes or key statements. Return one per line without bullets.

Extract key quotes or statements:

{content_snippet}""",
            'tags': f"""Generate 4-6 relevant single-word or two-word tags. Return comma-separated lowercase tags.

Generate relevant tags:

{content_snippet[:1500]}"""
        }

        # Estimated tokens per prompt (avg ~1000 tokens each)
        estimated_tokens_per_call = 1000

        # Parallel API call function
        async def call_gemini(prompt_type, prompt_text):
            await gemini_rate_limiter.acquire(estimated_tokens=estimated_tokens_per_call)
            response = await asyncio.to_thread(
                model.generate_content,
                prompt_text
            )
            # Record actual tokens if available
            if hasattr(response, 'usage_metadata') and hasattr(response.usage_metadata, 'total_token_count'):
                actual_tokens = response.usage_metadata.total_token_count
                await gemini_rate_limiter.record_actual_tokens(actual_tokens)

            return prompt_type, response

        # Execute all 5 calls in parallel
        results = await asyncio.gather(*[
            call_gemini('one_sentence', prompts['one_sentence']),
            call_gemini('bullets', prompts['bullets']),
            call_gemini('long_form', prompts['long_form']),
            call_gemini('highlights', prompts['highlights']),
            call_gemini('tags', prompts['tags'])
        ])

        # Parse results into dictionary
        results_dict = dict(results)

        # Parse one-sentence summary
        one_sentence = results_dict['one_sentence'].text.strip() if results_dict['one_sentence'].text else "Summary unavailable"

        # Parse bullet points
        bullet_points = []
        if results_dict['bullets'].text:
            for line in results_dict['bullets'].text.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    bullet_points.append(line.lstrip('-•* ').strip())
            bullet_points = bullet_points[:3]

            if len(bullet_points) < 3:
                bullet_points = [b.strip() for b in results_dict['bullets'].text.split('.') if b.strip()][:3]

        # Parse long-form summary
        long_form = results_dict['long_form'].text.strip() if results_dict['long_form'].text else "Detailed summary unavailable"

        # Parse highlights
        highlights = []
        if results_dict['highlights'].text:
            for line in results_dict['highlights'].text.split('\n'):
                line = line.strip().strip('-•*"').strip('"').strip()
                if len(line) > 10:
                    highlights.append(line)
            highlights = highlights[:5]

        # Parse tags
        suggested_tags = []
        if results_dict['tags'].text:
            for tag in results_dict['tags'].text.replace(',', ' ').replace('\n', ' ').split():
                tag = tag.strip().strip('.,;:').lower()
                if tag and len(tag) > 2:
                    suggested_tags.append(tag)
            suggested_tags = list(set(suggested_tags))[:6]
        
        await db.ai_summaries.update_one(
            {"bookmark_id": bookmark_id},
            {"$set": {
                "one_sentence": one_sentence,
                "bullet_points": bullet_points,
                "long_form": long_form,
                "highlights": highlights,
                "suggested_tags": suggested_tags,
                "processing_status": "completed",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        logger.info(f"AI summaries generated successfully for bookmark {bookmark_id}")
        return {"processing_status": "completed"}
    except Exception as e:
        logger.error(f"Error generating AI summaries for bookmark {bookmark_id}: {type(e).__name__}")
        await db.ai_summaries.update_one(
            {"bookmark_id": bookmark_id},
            {"$set": {
                "processing_status": "failed",
                "one_sentence": "AI processing failed",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        return {"processing_status": "failed"}

def calculate_reading_time(text_content: str) -> int:
    """Calculate estimated reading time in minutes (avg 200 words/min)"""
    if not text_content:
        return 0
    word_count = len(text_content.split())
    return max(1, round(word_count / 200))

async def process_bookmark_content(bookmark_id: str, url: str, collection_id: Optional[str] = None, user_id: str = None):
    """Background task to fetch content and generate AI summaries"""
    try:
        logger.info(f"Processing bookmark content: {bookmark_id}")
        content = await fetch_webpage_content(url)
        reading_time = calculate_reading_time(content.get('text_content', ''))

        await db.bookmarks.update_one(
            {"id": bookmark_id},
            {"$set": {
                "title": content.get('title'),
                "description": content.get('description'),
                "favicon": content.get('favicon'),
                "thumbnail": content.get('thumbnail'),
                "html_content": content.get('html_content'),
                "text_content": content.get('text_content'),
                "domain": content.get('domain'),
                "reading_time": reading_time,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        await generate_ai_summaries(content.get('text_content', ''), bookmark_id)
        logger.info(f"Successfully processed bookmark: {bookmark_id}")
    except Exception as e:
        logger.error(f"Error processing bookmark {bookmark_id}: {type(e).__name__}")

async def process_bulk_import(import_job_id: str, bookmark_ids: List[str], user_id: str):
    """Background task to process bulk import in two phases"""
    try:
        total = len(bookmark_ids)
        logger.info(f"Starting bulk import processing for job {import_job_id}: {total} bookmarks")

        # Phase 1: Fast content fetching (no rate limit)
        content_fetched = 0
        failed = 0

        for bookmark_id in bookmark_ids:
            try:
                bookmark = await db.bookmarks.find_one({"id": bookmark_id})
                if not bookmark:
                    continue

                content = await fetch_webpage_content(bookmark['url'])
                reading_time = calculate_reading_time(content.get('text_content', ''))

                await db.bookmarks.update_one(
                    {"id": bookmark_id},
                    {"$set": {
                        "title": content.get('title'),
                        "description": content.get('description'),
                        "favicon": content.get('favicon'),
                        "thumbnail": content.get('thumbnail'),
                        "html_content": content.get('html_content'),
                        "text_content": content.get('text_content'),
                        "domain": content.get('domain'),
                        "reading_time": reading_time,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                content_fetched += 1

                # Update progress every 10 bookmarks
                if content_fetched % 10 == 0:
                    await db.import_jobs.update_one(
                        {"id": import_job_id},
                        {"$set": {
                            "content_fetched": content_fetched,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
            except Exception as e:
                failed += 1
                logger.error(f"Error fetching content for bookmark {bookmark_id}: {type(e).__name__}")

        # Update after Phase 1 completion
        await db.import_jobs.update_one(
            {"id": import_job_id},
            {"$set": {
                "content_fetched": content_fetched,
                "failed": failed,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        logger.info(f"Phase 1 complete for job {import_job_id}: {content_fetched}/{total} fetched, {failed} failed")

        # Phase 2: Rate-limited AI processing
        ai_processed = 0

        for bookmark_id in bookmark_ids:
            try:
                bookmark = await db.bookmarks.find_one({"id": bookmark_id})
                if not bookmark or not bookmark.get('text_content'):
                    continue

                result = await generate_ai_summaries(bookmark['text_content'], bookmark_id)
                if result.get('processing_status') == 'completed':
                    ai_processed += 1
                else:
                    failed += 1

                # Update progress every 5 AI processes
                if ai_processed % 5 == 0:
                    # Calculate ETA
                    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(
                        (await db.import_jobs.find_one({"id": import_job_id}))['created_at']
                    )).total_seconds()
                    remaining = total - ai_processed
                    eta = datetime.now(timezone.utc) + timedelta(seconds=(elapsed / ai_processed) * remaining if ai_processed > 0 else 0)

                    await db.import_jobs.update_one(
                        {"id": import_job_id},
                        {"$set": {
                            "ai_processed": ai_processed,
                            "failed": failed,
                            "estimated_completion_time": eta.isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
            except Exception as e:
                failed += 1
                logger.error(f"Error processing AI for bookmark {bookmark_id}: {type(e).__name__}")

        # Mark job as completed
        await db.import_jobs.update_one(
            {"id": import_job_id},
            {"$set": {
                "ai_processed": ai_processed,
                "failed": failed,
                "status": "completed",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        logger.info(f"Bulk import completed for job {import_job_id}: {ai_processed}/{total} AI processed")

    except Exception as e:
        logger.error(f"Error in bulk import job {import_job_id}: {type(e).__name__}")
        await db.import_jobs.update_one(
            {"id": import_job_id},
            {"$set": {
                "status": "failed",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

@api_router.post("/bookmarks", response_model=Bookmark)
@limiter.limit("20/minute")  # IP-based rate limiting
@limiter.limit("100/hour", key_func=get_user_identifier)  # User-based rate limiting
async def create_bookmark(request: Request, bookmark_data: BookmarkCreate, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
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
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.bookmarks.insert_one(bookmark)
    
    ai_summary = {
        "id": str(uuid.uuid4()),
        "bookmark_id": bookmark["id"],
        "processing_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.ai_summaries.insert_one(ai_summary)
    
    background_tasks.add_task(
        process_bookmark_content,
        bookmark["id"], 
        bookmark_data.url, 
        bookmark_data.collection_id,
        current_user["id"]
    )
    
    if bookmark_data.collection_id:
        await db.collections.update_one(
            {"id": bookmark_data.collection_id, "user_id": current_user["id"]},
            {"$addToSet": {"bookmark_ids": bookmark["id"]}}
        )
    
    return Bookmark(**bookmark)

@api_router.get("/bookmarks", response_model=List[dict])
async def get_bookmarks(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    domain: Optional[str] = None,
    collection_id: Optional[str] = None,
    read_status: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    limit: Optional[int] = 100,
    current_user: dict = Depends(get_current_user)
):
    query = {"user_id": current_user["id"]}
    
    if domain:
        query["domain"] = domain
    
    if read_status == "read":
        query["read_status"] = True
    elif read_status == "unread":
        query["read_status"] = False
    
    if collection_id:
        collection = await db.collections.find_one({"id": collection_id}, {"_id": 0, "bookmark_ids": 1})
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
        "view_count": 1       # Phase 1: For usage tracking
    }
    
    bookmarks = await db.bookmarks.find(query, projection).sort(sort_field, sort_order).limit(min(limit, 1000)).to_list(None)
    
    if search:
        search_lower = search.lower()
        bookmarks = [b for b in bookmarks if 
                    search_lower in (b.get('title') or '').lower() or 
                    search_lower in (b.get('description') or '').lower()]
    
    bookmark_ids = [b["id"] for b in bookmarks]
    summaries = await db.ai_summaries.find(
        {"bookmark_id": {"$in": bookmark_ids}}, 
        {"_id": 0}
    ).to_list(None)
    
    summary_map = {s["bookmark_id"]: s for s in summaries}
    
    result = []
    for bookmark in bookmarks:
        summary = summary_map.get(bookmark["id"])
        
        if tag and summary:
            if tag.lower() not in [t.lower() for t in summary.get('suggested_tags', [])]:
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
    current_user: dict = Depends(get_current_user)
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
            {"last_accessed": {"$exists": False}}  # Unmigrated bookmarks
        ]
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
        "view_count": 1
    }

    bookmarks = await db.bookmarks.find(query, projection) \
        .sort("last_accessed", 1) \
        .limit(limit) \
        .to_list(None)

    return {
        "count": len(bookmarks),
        "bookmarks": bookmarks
    }

@api_router.get("/bookmarks/{bookmark_id}")
async def get_bookmark(bookmark_id: str, current_user: dict = Depends(get_current_user)):
    bookmark = await db.bookmarks.find_one({"id": bookmark_id, "user_id": current_user["id"]}, {"_id": 0})
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    summary = await db.ai_summaries.find_one({"bookmark_id": bookmark_id}, {"_id": 0})

    result = {**bookmark}
    if summary:
        result["ai_summary"] = summary

    # Phase 1: Auto-track detail page view
    await track_bookmark_access(bookmark_id, "detail", current_user)

    return result

@api_router.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.bookmarks.delete_one({"id": bookmark_id, "user_id": current_user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    await db.ai_summaries.delete_one({"bookmark_id": bookmark_id})
    await db.collections.update_many(
        {"user_id": current_user["id"]},
        {"$pull": {"bookmark_ids": bookmark_id}}
    )
    
    return {"message": "Bookmark deleted"}

@api_router.post("/bookmarks/bulk-delete")
@limiter.limit("10/minute")  # IP-based rate limiting
@limiter.limit("50/hour", key_func=get_user_identifier)  # User-based rate limiting
async def bulk_delete_bookmarks(request: Request, bookmark_ids: List[str], current_user: dict = Depends(get_current_user)):
    result = await db.bookmarks.delete_many({"id": {"$in": bookmark_ids}, "user_id": current_user["id"]})
    await db.ai_summaries.delete_many({"bookmark_id": {"$in": bookmark_ids}})
    await db.collections.update_many(
        {"user_id": current_user["id"]},
        {"$pull": {"bookmark_ids": {"$in": bookmark_ids}}}
    )
    return {"message": f"Deleted {result.deleted_count} bookmarks", "count": result.deleted_count}

@api_router.patch("/bookmarks/{bookmark_id}/read-status")
async def update_read_status(bookmark_id: str, read_status: bool, current_user: dict = Depends(get_current_user)):
    result = await db.bookmarks.update_one(
        {"id": bookmark_id, "user_id": current_user["id"]},
        {"$set": {"read_status": read_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"message": "Read status updated"}

@api_router.post("/bookmarks/bulk-mark-read")
@limiter.limit("10/minute")  # IP-based rate limiting
@limiter.limit("50/hour", key_func=get_user_identifier)  # User-based rate limiting
async def bulk_mark_read(request: Request, bookmark_ids: List[str], read_status: bool, current_user: dict = Depends(get_current_user)):
    result = await db.bookmarks.update_many(
        {"id": {"$in": bookmark_ids}, "user_id": current_user["id"]},
        {"$set": {"read_status": read_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": f"Updated {result.modified_count} bookmarks", "count": result.modified_count}

# Phase 1: Access Tracking & Aging Endpoints

@api_router.post("/bookmarks/{bookmark_id}/accessed")
async def track_bookmark_access(
    bookmark_id: str,
    source: str = "detail",  # "detail" or "external"
    current_user: dict = Depends(get_current_user)
):
    """
    Track when a bookmark is meaningfully accessed.
    Called when user views detail page or opens external URL.
    """
    # Validate ownership
    bookmark = await db.bookmarks.find_one({
        "id": bookmark_id,
        "user_id": current_user["id"]
    })
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
                    "$slice": -20  # Keep only last 20
                }
            }
        }
    )

    return {"status": "tracked", "timestamp": now}

@api_router.get("/bookmarks/duplicates/detect")
async def detect_duplicates(current_user: dict = Depends(get_current_user)):
    projection = {"_id": 0, "id": 1, "url": 1, "title": 1, "text_content": 1, "domain": 1, "created_at": 1, "thumbnail": 1, "favicon": 1}
    bookmarks = await db.bookmarks.find({"user_id": current_user["id"]}, projection).limit(500).to_list(None)
    
    url_groups = {}
    for bookmark in bookmarks:
        normalized_url = re.sub(r'(\?|#).*$', '', bookmark['url']).lower().strip('/')
        if normalized_url not in url_groups:
            url_groups[normalized_url] = []
        url_groups[normalized_url].append(bookmark)
    
    duplicates = []
    for url, group in url_groups.items():
        if len(group) > 1:
            duplicates.append({"type": "exact_url", "bookmarks": group})
    
    texts = [b.get('text_content', '')[:1000] for b in bookmarks if b.get('text_content')]
    if len(texts) > 1:
        try:
            vectorizer = TfidfVectorizer(max_features=100)
            tfidf_matrix = vectorizer.fit_transform(texts)
            similarities = cosine_similarity(tfidf_matrix)
            
            for i in range(len(bookmarks)):
                for j in range(i + 1, len(bookmarks)):
                    if similarities[i][j] > 0.85:
                        duplicates.append({
                            "type": "similar_content",
                            "similarity": float(similarities[i][j]),
                            "bookmarks": [bookmarks[i], bookmarks[j]]
                        })
        except:
            pass
    
    return {"duplicates": duplicates}

@api_router.post("/bookmarks/merge")
async def merge_bookmarks(bookmark_ids: List[str], current_user: dict = Depends(get_current_user)):
    if len(bookmark_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 bookmarks to merge")
    
    bookmarks = await db.bookmarks.find({"id": {"$in": bookmark_ids}, "user_id": current_user["id"]}, {"_id": 0}).to_list(100)
    if len(bookmarks) < 2:
        raise HTTPException(status_code=404, detail="Bookmarks not found")
    
    keep_bookmark = bookmarks[0]
    delete_ids = [b["id"] for b in bookmarks[1:]]
    
    await db.bookmarks.delete_many({"id": {"$in": delete_ids}})
    await db.ai_summaries.delete_many({"bookmark_id": {"$in": delete_ids}})
    
    return {"message": "Bookmarks merged", "kept_bookmark": keep_bookmark}

@api_router.post("/collections", response_model=Collection)
async def create_collection(collection_data: CollectionCreate, current_user: dict = Depends(get_current_user)):
    collection = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "name": collection_data.name,
        "bookmark_ids": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.collections.insert_one(collection)
    return Collection(**collection)

@api_router.get("/collections", response_model=List[Collection])
async def get_collections(current_user: dict = Depends(get_current_user)):
    collections = await db.collections.find({"user_id": current_user["id"]}, {"_id": 0}).limit(100).to_list(None)
    return [Collection(**c) for c in collections]

@api_router.post("/collections/{collection_id}/add")
async def add_to_collection(collection_id: str, data: AddToCollection, current_user: dict = Depends(get_current_user)):
    result = await db.collections.update_one(
        {"id": collection_id, "user_id": current_user["id"]},
        {"$addToSet": {"bookmark_ids": data.bookmark_id}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"message": "Bookmark added to collection"}

@api_router.post("/bookmarks/import")
@limiter.limit("3/hour")  # Limit imports to prevent abuse
async def import_bookmarks(request: Request, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
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
            html_content = file.decode('utf-8') if isinstance(file, bytes) else file
        except UnicodeDecodeError:
            logger.warning(f"User {current_user['id']} attempted to import non-UTF-8 file")
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded HTML")

        # Validate file contains content
        if not html_content or len(html_content.strip()) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Detect file format: HTML bookmark file, CSV, or plain text URL list
        html_lower = html_content.lower()
        is_html_format = '<a' in html_lower or '<A' in html_lower

        # Detect CSV format (looks for comma-separated values)
        lines = html_content.strip().split('\n')
        is_csv_format = False
        if not is_html_format and len(lines) > 0:
            # Check if first few lines contain commas (likely CSV)
            first_lines = lines[:5]
            comma_count = sum(1 for line in first_lines if ',' in line)
            is_csv_format = comma_count >= len(first_lines) * 0.5  # At least 50% have commas

        urls_to_import = []
        MAX_BOOKMARKS_PER_IMPORT = 1000

        if is_html_format:
            # Process HTML bookmark file (browser export format)
            soup = BeautifulSoup(html_content, 'html.parser')
            links = soup.find_all('a')

            if not links or len(links) == 0:
                logger.warning(f"User {current_user['id']} imported HTML file with no parseable bookmarks")
                raise HTTPException(status_code=400, detail="No bookmarks found in HTML file")

            for link in links[:MAX_BOOKMARKS_PER_IMPORT]:
                url = link.get('href')
                title = link.get_text(strip=True)

                if url and url.startswith('http'):
                    urls_to_import.append({'url': url, 'title': title or urlparse(url).netloc})

        elif is_csv_format:
            # Process CSV file (URL in first column, optional title in second column)
            for line in lines[:MAX_BOOKMARKS_PER_IMPORT]:
                line = line.strip()
                if not line:
                    continue

                # Split by comma
                parts = [p.strip().strip('"').strip("'") for p in line.split(',')]

                if len(parts) == 0:
                    continue

                url = parts[0]
                title = parts[1] if len(parts) > 1 and parts[1] else None

                # Skip header row (common CSV headers)
                if url.lower() in ['url', 'link', 'website', 'address', 'bookmark']:
                    continue

                # Only import valid HTTP(S) URLs
                if url and url.startswith('http'):
                    urls_to_import.append({'url': url, 'title': title or urlparse(url).netloc})

        else:
            # Process plain text URL list (one URL per line)
            for line in lines[:MAX_BOOKMARKS_PER_IMPORT]:
                url = line.strip()

                # Skip empty lines and non-URL lines
                if not url or not url.startswith('http'):
                    continue

                urls_to_import.append({'url': url, 'title': urlparse(url).netloc})

        # Validate at least one URL was found
        if not urls_to_import:
            raise HTTPException(status_code=400, detail="No valid URLs found in file")

        logger.info(f"User {current_user['id']} importing {len(urls_to_import)} bookmarks")

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
            "estimated_completion_time": None
        }
        await db.import_jobs.insert_one(import_job)

        # Create placeholder bookmarks
        bookmark_ids = []
        imported_count = 0

        for item in urls_to_import:
            url = item['url']
            title = item['title']

            if url and url.startswith('http'):
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
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }

                await db.bookmarks.insert_one(bookmark)

                ai_summary = {
                    "id": str(uuid.uuid4()),
                    "bookmark_id": bookmark["id"],
                    "processing_status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.ai_summaries.insert_one(ai_summary)

                bookmark_ids.append(bookmark["id"])
                imported_count += 1

        # Start background bulk processing
        if background_tasks and bookmark_ids:
            background_tasks.add_task(process_bulk_import, import_job["id"], bookmark_ids, current_user["id"])

        logger.info(f"Successfully imported {imported_count} bookmarks for user {current_user['id']}")
        return {
            "message": f"Imported {imported_count} bookmarks",
            "count": imported_count,
            "import_job_id": import_job["id"]
        }
    except HTTPException:
        # Re-raise HTTP exceptions as-is (these are validation errors with proper messages)
        raise
    except Exception as e:
        logger.error(f"Error importing bookmarks for user {current_user['id']}: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to import bookmarks: {str(e)}")

@api_router.get("/import-jobs/{job_id}")
async def get_import_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Get import job progress"""
    job = await db.import_jobs.find_one({"id": job_id, "user_id": current_user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return job

@api_router.get("/import-jobs")
async def get_import_jobs(current_user: dict = Depends(get_current_user)):
    """Get all import jobs for user"""
    jobs = await db.import_jobs.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(None)
    return jobs

@api_router.get("/bookmarks/export")
async def export_bookmarks(current_user: dict = Depends(get_current_user)):
    """Export bookmarks as browser-compatible HTML"""
    projection = {"_id": 0, "url": 1, "title": 1, "created_at": 1}
    bookmarks = await db.bookmarks.find({"user_id": current_user["id"]}, projection).sort("created_at", -1).limit(5000).to_list(None)
    
    html_parts = [
        '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        '<TITLE>Arivu Bookmarks</TITLE>',
        '<H1>Arivu Bookmarks</H1>',
        '<DL><p>'
    ]
    
    for bookmark in bookmarks:
        add_date = int(datetime.fromisoformat(bookmark['created_at']).timestamp())
        title = bookmark.get('title', bookmark.get('url', 'Untitled'))
        url = bookmark.get('url', '')
        html_parts.append(f'    <DT><A HREF="{url}" ADD_DATE="{add_date}">{title}</A>')
    
    html_parts.append('</DL><p>')
    
    from fastapi.responses import Response
    return Response(
        content='\n'.join(html_parts),
        media_type='text/html',
        headers={
            'Content-Disposition': f'attachment; filename="arivu_bookmarks_{datetime.now().strftime("%Y%m%d")}.html"'
        }
    )

# Request size limit middleware
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request, call_next):
        # Check Content-Length header if present
        content_length = request.headers.get('content-length')
        if content_length:
            content_length = int(content_length)
            if content_length > self.max_size:
                logger.warning(f"Request rejected: size {content_length} exceeds limit {self.max_size}")
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body too large. Maximum size is {self.max_size / (1024 * 1024):.1f}MB"
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
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.include_router(api_router)

# Add middleware (order matters - applied in reverse order)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)  # 10MB limit

# Validate CORS origins
cors_origins_env = os.environ.get('CORS_ORIGINS', '*')
if cors_origins_env == '*':
    logger.warning("CORS_ORIGINS set to '*' - allowing all origins (not recommended for production)")
    cors_origins = ['*']
else:
    cors_origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
    if not cors_origins:
        logger.warning("CORS_ORIGINS configured but empty - defaulting to allow all origins")
        cors_origins = ['*']

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