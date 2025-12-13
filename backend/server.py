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
from typing import List, Optional
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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
client = AsyncIOMotorClient(mongo_url)
db_name = os.environ.get('DB_NAME', 'arivu_db')
db = client[db_name]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True, max_redirects=5)
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
        text_content = h.handle(summary_html).strip()
        
        if not text_content or len(text_content.strip()) < 100:
            cleaned_soup = BeautifulSoup(summary_html, 'html.parser')
            paragraphs = cleaned_soup.find_all(['p', 'article', 'section'])
            text_parts = []
            for p in paragraphs:
                text = p.get_text(separator=' ', strip=True)
                if len(text) > 50:
                    text_parts.append(text)
            if text_parts:
                text_content = '\\n\\n'.join(text_parts)
        
        if len(text_content) < 50:
            text_content = soup.get_text(separator='\\n', strip=True)
        
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
        logger.error(f"Error fetching webpage from domain {urlparse(url).netloc}: {type(e).__name__}")
        return {
            'title': urlparse(url).netloc,
            'domain': urlparse(url).netloc,
            'text_content': f"Failed to fetch content",
            'html_content': ''
        }

async def generate_ai_summaries(text_content: str, bookmark_id: str):
    """Generate AI summaries for bookmark content"""
    try:
        if not text_content or len(text_content.strip()) < 50:
            logger.info(f"Insufficient content for AI processing: bookmark {bookmark_id}")
            raise ValueError("Insufficient content for AI processing")

        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY not configured")
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        content_snippet = text_content[:4000].strip()
        
        # Generate one-sentence summary
        one_sentence_prompt = f"""You are a factual summarizer. Create ONE concise sentence (max 20 words) summarizing the main point. Be direct and factual.

Summarize in ONE sentence:

{content_snippet}"""
        
        response = await asyncio.to_thread(
            model.generate_content,
            one_sentence_prompt
        )
        one_sentence = response.text.strip() if response.text else "Summary unavailable"
        
        # Generate bullet points
        bullets_prompt = f"""Extract exactly 3 key bullet points. Format as:
- Point 1
- Point 2
- Point 3
Be factual and concise.

Extract 3 key points:

{content_snippet}"""
        
        response = await asyncio.to_thread(
            model.generate_content,
            bullets_prompt
        )
        bullet_points = []
        if response.text:
            for line in response.text.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    bullet_points.append(line.lstrip('-•* ').strip())
            bullet_points = bullet_points[:3]
            
            if len(bullet_points) < 3:
                bullet_points = [b.strip() for b in response.text.split('.') if b.strip()][:3]
        
        # Generate long-form summary
        long_form_prompt = f"""Create a comprehensive summary (150-200 words) with clear sections. Be factual and well-structured.

Create a detailed summary with Overview, Key Facts, and Main Points:

{content_snippet}"""
        
        response = await asyncio.to_thread(
            model.generate_content,
            long_form_prompt
        )
        long_form = response.text.strip() if response.text else "Detailed summary unavailable"
        
        # Extract highlights
        highlights_prompt = f"""Extract 3-5 important direct quotes or key statements. Return one per line without bullets.

Extract key quotes or statements:

{content_snippet}"""
        
        response = await asyncio.to_thread(
            model.generate_content,
            highlights_prompt
        )
        highlights = []
        if response.text:
            for line in response.text.split('\n'):
                line = line.strip().strip('-•*"').strip('"').strip()
                if len(line) > 10:
                    highlights.append(line)
            highlights = highlights[:5]
        
        # Generate tags
        tags_prompt = f"""Generate 4-6 relevant single-word or two-word tags. Return comma-separated lowercase tags.

Generate relevant tags:

{content_snippet[:1500]}"""
        
        response = await asyncio.to_thread(
            model.generate_content,
            tags_prompt
        )
        suggested_tags = []
        if response.text:
            for tag in response.text.replace(',', ' ').replace('\n', ' ').split():
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

@api_router.post("/bookmarks", response_model=Bookmark)
@limiter.limit("20/minute")  # Limit bookmark creation to prevent abuse
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
        "updated_at": 1
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

@api_router.get("/bookmarks/{bookmark_id}")
async def get_bookmark(bookmark_id: str, current_user: dict = Depends(get_current_user)):
    bookmark = await db.bookmarks.find_one({"id": bookmark_id, "user_id": current_user["id"]}, {"_id": 0})
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    summary = await db.ai_summaries.find_one({"bookmark_id": bookmark_id}, {"_id": 0})
    
    result = {**bookmark}
    if summary:
        result["ai_summary"] = summary
    
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
@limiter.limit("10/minute")  # Limit bulk operations
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
@limiter.limit("10/minute")  # Limit bulk operations
async def bulk_mark_read(request: Request, bookmark_ids: List[str], read_status: bool, current_user: dict = Depends(get_current_user)):
    result = await db.bookmarks.update_many(
        {"id": {"$in": bookmark_ids}, "user_id": current_user["id"]},
        {"$set": {"read_status": read_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": f"Updated {result.modified_count} bookmarks", "count": result.modified_count}

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

        # Validate file contains HTML bookmark structure
        if not html_content or len(html_content.strip()) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Check for basic HTML structure and bookmark links
        html_lower = html_content.lower()
        if not ('<a' in html_lower or '<A' in html_lower):
            logger.warning(f"User {current_user['id']} attempted to import file without bookmark links")
            raise HTTPException(status_code=400, detail="File does not appear to be a valid HTML bookmark file (no links found)")

        soup = BeautifulSoup(html_content, 'html.parser')
        links = soup.find_all('a')

        # Validate at least one link was found
        if not links or len(links) == 0:
            logger.warning(f"User {current_user['id']} imported file with no parseable bookmarks")
            raise HTTPException(status_code=400, detail="No bookmarks found in file")

        # Limit number of bookmarks per import
        MAX_BOOKMARKS_PER_IMPORT = 1000
        links = links[:MAX_BOOKMARKS_PER_IMPORT]

        logger.info(f"User {current_user['id']} importing {len(links)} bookmarks")
        imported_count = 0
        for link in links:
            url = link.get('href')
            title = link.get_text(strip=True)
            
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
                
                if background_tasks:
                    background_tasks.add_task(process_bookmark_content, bookmark["id"], url, None, current_user["id"])
                imported_count += 1

        logger.info(f"Successfully imported {imported_count} bookmarks for user {current_user['id']}")
        return {"message": f"Imported {imported_count} bookmarks", "count": imported_count}
    except HTTPException:
        # Re-raise HTTP exceptions as-is (these are validation errors with proper messages)
        raise
    except Exception as e:
        logger.error(f"Error importing bookmarks for user {current_user['id']}: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to import bookmarks: {str(e)}")

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

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

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