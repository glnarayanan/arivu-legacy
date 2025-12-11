from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
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
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    token: str
    user: dict

class BookmarkCreate(BaseModel):
    url: str
    collection_id: Optional[str] = None

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

class AddToCollection(BaseModel):
    bookmark_id: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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

@api_router.post("/auth/signup", response_model=TokenResponse)
async def signup(user_data: UserSignup):
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = {
        "id": str(uuid.uuid4()),
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": pwd_context.hash(user_data.password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)
    
    token = create_access_token(data={"sub": user["id"]})
    user_response = {"id": user["id"], "email": user["email"], "name": user["name"]}
    return {"token": token, "user": user_response}

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    user = await db.users.find_one({"email": login_data.email})
    if not user or not pwd_context.verify(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": user["id"]})
    user_response = {"id": user["id"], "email": user["email"], "name": user["name"]}
    return {"token": token, "user": user_response}

async def fetch_webpage_content(url: str):
    try:
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
        logging.error(f"Error fetching webpage {url}: {str(e)}")
        return {
            'title': urlparse(url).netloc,
            'domain': urlparse(url).netloc,
            'text_content': f"Failed to fetch content from {url}",
            'html_content': ''
        }

async def generate_ai_summaries(text_content: str, bookmark_id: str):
    try:
        if not text_content or len(text_content.strip()) < 50:
            raise ValueError("Insufficient content for AI processing")
        
        emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        content_snippet = text_content[:4000].strip()
        
        one_sentence_chat = LlmChat(
            api_key=emergent_key,
            session_id=f"summary-1s-{bookmark_id}",
            system_message="You are a factual summarizer. Create ONE concise sentence (max 20 words) summarizing the main point. Be direct and factual."
        ).with_model("gemini", "gemini-2.5-flash")
        
        one_sentence = await one_sentence_chat.send_message(
            UserMessage(text=f"Summarize in ONE sentence:\n\n{content_snippet}")
        )
        one_sentence = one_sentence.strip()
        
        bullet_chat = LlmChat(
            api_key=emergent_key,
            session_id=f"summary-bullets-{bookmark_id}",
            system_message="Extract exactly 3 key bullet points. Format as:\n- Point 1\n- Point 2\n- Point 3\nBe factual and concise."
        ).with_model("gemini", "gemini-2.5-flash")
        
        bullets_response = await bullet_chat.send_message(
            UserMessage(text=f"Extract 3 key points:\n\n{content_snippet}")
        )
        bullet_points = []
        for line in bullets_response.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                bullet_points.append(line.lstrip('-•* ').strip())
        bullet_points = bullet_points[:3]
        
        if len(bullet_points) < 3:
            bullet_points = [b.strip() for b in bullets_response.split('.') if b.strip()][:3]
        
        long_chat = LlmChat(
            api_key=emergent_key,
            session_id=f"summary-long-{bookmark_id}",
            system_message="Create a comprehensive summary (150-200 words) with clear sections. Be factual and well-structured."
        ).with_model("gemini", "gemini-2.5-flash")
        
        long_form = await long_chat.send_message(
            UserMessage(text=f"Create a detailed summary with Overview, Key Facts, and Main Points:\n\n{content_snippet}")
        )
        long_form = long_form.strip()
        
        highlights_chat = LlmChat(
            api_key=emergent_key,
            session_id=f"highlights-{bookmark_id}",
            system_message="Extract 3-5 important direct quotes or key statements. Return one per line without bullets."
        ).with_model("gemini", "gemini-2.5-flash")
        
        highlights_response = await highlights_chat.send_message(
            UserMessage(text=f"Extract key quotes or statements:\n\n{content_snippet}")
        )
        highlights = []
        for line in highlights_response.split('\n'):
            line = line.strip().strip('-•*"').strip('"').strip()
            if len(line) > 10:
                highlights.append(line)
        highlights = highlights[:5]
        
        tags_chat = LlmChat(
            api_key=emergent_key,
            session_id=f"tags-{bookmark_id}",
            system_message="Generate 4-6 relevant single-word or two-word tags. Return comma-separated lowercase tags."
        ).with_model("gemini", "gemini-2.5-flash")
        
        tags_response = await tags_chat.send_message(
            UserMessage(text=f"Generate relevant tags:\n\n{content_snippet[:1500]}")
        )
        suggested_tags = []
        for tag in tags_response.replace(',', ' ').replace('\n', ' ').split():
            tag = tag.strip().strip('.,;:').lower()
            if tag and len(tag) > 2:
                suggested_tags.append(tag)
        suggested_tags = list(set(suggested_tags))[:6]
        
        summary = {
            "id": str(uuid.uuid4()),
            "bookmark_id": bookmark_id,
            "one_sentence": one_sentence,
            "bullet_points": bullet_points,
            "long_form": long_form,
            "highlights": highlights,
            "suggested_tags": suggested_tags,
            "processing_status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.ai_summaries.insert_one(summary)
        logging.info(f"AI summaries generated successfully for bookmark {bookmark_id}")
        return summary
    except Exception as e:
        logging.error(f"Error generating AI summaries for {bookmark_id}: {e}")
        summary = {
            "id": str(uuid.uuid4()),
            "bookmark_id": bookmark_id,
            "processing_status": "failed",
            "one_sentence": "AI processing failed",
            "bullet_points": [],
            "highlights": [],
            "suggested_tags": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.ai_summaries.insert_one(summary)
        return summary

def calculate_reading_time(text_content: str) -> int:
    """Calculate estimated reading time in minutes (avg 200 words/min)"""
    if not text_content:
        return 0
    word_count = len(text_content.split())
    return max(1, round(word_count / 200))

async def process_bookmark_content(bookmark_id: str, url: str, collection_id: Optional[str] = None, user_id: str = None):
    """Background task to fetch content and generate AI summaries"""
    try:
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
    except Exception as e:
        logging.error(f"Error processing bookmark {bookmark_id}: {e}")

@api_router.post("/bookmarks", response_model=Bookmark)
async def create_bookmark(bookmark_data: BookmarkCreate, current_user: dict = Depends(get_current_user)):
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
    
    asyncio.create_task(process_bookmark_content(
        bookmark["id"], 
        bookmark_data.url, 
        bookmark_data.collection_id,
        current_user["id"]
    ))
    
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
async def bulk_delete_bookmarks(bookmark_ids: List[str], current_user: dict = Depends(get_current_user)):
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
async def bulk_mark_read(bookmark_ids: List[str], read_status: bool, current_user: dict = Depends(get_current_user)):
    result = await db.bookmarks.update_many(
        {"id": {"$in": bookmark_ids}, "user_id": current_user["id"]},
        {"$set": {"read_status": read_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": f"Updated {result.modified_count} bookmarks", "count": result.modified_count}

@api_router.get("/bookmarks/duplicates/detect")
async def detect_duplicates(current_user: dict = Depends(get_current_user)):
    bookmarks = await db.bookmarks.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(1000)
    
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
    collections = await db.collections.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(1000)
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
async def import_bookmarks(file: bytes = None, current_user: dict = Depends(get_current_user)):
    """Import bookmarks from browser HTML file"""
    try:
        from fastapi import UploadFile, File
        html_content = file.decode('utf-8') if isinstance(file, bytes) else file
        
        soup = BeautifulSoup(html_content, 'html.parser')
        links = soup.find_all('a')
        
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
                
                asyncio.create_task(process_bookmark_content(bookmark["id"], url, None, current_user["id"]))
                imported_count += 1
        
        return {"message": f"Imported {imported_count} bookmarks", "count": imported_count}
    except Exception as e:
        logging.error(f"Error importing bookmarks: {e}")
        raise HTTPException(status_code=400, detail="Failed to import bookmarks")

@api_router.get("/bookmarks/export")
async def export_bookmarks(current_user: dict = Depends(get_current_user)):
    """Export bookmarks as browser-compatible HTML"""
    bookmarks = await db.bookmarks.find({"user_id": current_user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(10000)
    
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

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()