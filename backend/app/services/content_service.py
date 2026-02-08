"""
Content service module - extracted from server.py (Phase 6, Plan 01).

Provides webpage content fetching, reading time calculation,
and bookmark content processing orchestration.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import html2text
import requests
from bs4 import BeautifulSoup
from readability import Document
from tenacity import RetryError

from app.core.database import get_database
from app.models.bookmark import is_safe_url
from app.services.ai_service import (
    extract_entities_and_concepts,
    generate_ai_summaries,
    generate_embedding,
    has_substantial_change,
)

logger = logging.getLogger(__name__)

# Content fetching limits (SEC-05)
MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10MB max for webpage content


async def fetch_webpage_content(url: str):
    """Fetch and parse webpage content with security validation"""
    try:
        # Validate URL is safe before fetching
        safe, error_msg = is_safe_url(url)
        if not safe:
            logger.warning(f"Unsafe URL blocked: {error_msg}")
            raise ValueError(f"Unsafe URL: {error_msg}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        # Use streaming to check size before loading into memory (SEC-05)
        with requests.get(url, headers=headers, timeout=15, allow_redirects=True, stream=True) as response:
            response.raise_for_status()

            # Check Content-Length header BEFORE downloading
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > MAX_CONTENT_SIZE:
                logger.warning(f"Content too large (Content-Length: {content_length}): {urlparse(url).netloc}")
                raise ValueError(f"Content too large: {int(content_length) // (1024*1024)}MB exceeds {MAX_CONTENT_SIZE // (1024*1024)}MB limit")

            # Stream content in chunks, tracking total size
            chunks = []
            total_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                total_size += len(chunk)
                if total_size > MAX_CONTENT_SIZE:
                    logger.warning(f"Content exceeded size limit during download: {urlparse(url).netloc}")
                    raise ValueError(f"Content exceeded {MAX_CONTENT_SIZE // (1024*1024)}MB limit during download")
                chunks.append(chunk)

            # Decode content - try utf-8, fall back to detected encoding
            try:
                html_content = b''.join(chunks).decode('utf-8')
            except UnicodeDecodeError:
                html_content = b''.join(chunks).decode(response.encoding or 'utf-8', errors='replace')

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


def calculate_reading_time(text_content: str) -> int:
    """Calculate estimated reading time in minutes (avg 200 words/min)"""
    if not text_content:
        return 0
    word_count = len(text_content.split())
    return max(1, round(word_count / 200))


async def process_bookmark_content(
    bookmark_id: str, url: str, collection_id: Optional[str] = None, user_id: str = None
):
    """Background task to fetch content, generate AI summaries, and create embeddings for semantic search"""
    try:
        db = get_database()
        logger.info(f"Processing bookmark content: {bookmark_id}")

        # Fetch existing content for change detection (PERF-02)
        existing_bookmark = await db.bookmarks.find_one(
            {"id": bookmark_id},
            {"_id": 0, "text_content": 1, "title": 1, "embedding": 1}
        )
        old_text_content = existing_bookmark.get("text_content", "") if existing_bookmark else ""
        old_title = existing_bookmark.get("title", "") if existing_bookmark else ""
        had_embedding = bool(existing_bookmark.get("embedding")) if existing_bookmark else False

        content = await fetch_webpage_content(url)
        new_text_content = content.get("text_content", "")
        new_title = content.get("title", "")
        reading_time = calculate_reading_time(new_text_content)

        await db.bookmarks.update_one(
            {"id": bookmark_id},
            {
                "$set": {
                    "title": new_title,
                    "description": content.get("description"),
                    "favicon": content.get("favicon"),
                    "thumbnail": content.get("thumbnail"),
                    "html_content": content.get("html_content"),
                    "text_content": new_text_content,
                    "domain": content.get("domain"),
                    "reading_time": reading_time,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

        # Generate AI summaries with retry and error classification
        # (always run regardless of content change magnitude)
        try:
            await generate_ai_summaries(new_text_content, bookmark_id)
        except RetryError:
            logger.error(f"AI summary failed after all retries for bookmark {bookmark_id}")
            await db.ai_summaries.update_one(
                {"bookmark_id": bookmark_id},
                {"$set": {
                    "processing_status": "failed",
                    "one_sentence": "AI processing temporarily unavailable. Will retry later.",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )

        # Generate embedding only if content changed substantially (PERF-02)
        text_content = new_text_content
        title = new_title
        description = content.get("description", "")

        # Determine if embedding regeneration is needed
        content_changed = has_substantial_change(old_text_content, text_content)
        title_changed = has_substantial_change(old_title, title)
        needs_embedding = not had_embedding or content_changed or title_changed

        if text_content and len(text_content.strip()) >= 50 and needs_embedding:
            logger.info(f"Regenerating embedding for bookmark {bookmark_id} (content_changed={content_changed}, title_changed={title_changed})")
            try:
                embedding = await generate_embedding(text_content, title, description)
            except RetryError:
                logger.error(f"Embedding generation failed after all retries for bookmark {bookmark_id}")
                embedding = None

            # Get AI summary data for entity/concept extraction
            ai_summary = await db.ai_summaries.find_one(
                {"bookmark_id": bookmark_id}, {"_id": 0}
            )

            try:
                entities, concepts = await extract_entities_and_concepts(
                    text_content, ai_summary
                )
            except RetryError:
                logger.error(f"Entity extraction failed after all retries for bookmark {bookmark_id}")
                entities, concepts = [], []

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
        elif text_content and len(text_content.strip()) >= 50 and not needs_embedding:
            logger.info(f"Skipping embedding regeneration for bookmark {bookmark_id} (change below 10% threshold)")

        logger.info(f"Successfully processed bookmark: {bookmark_id}")
    except Exception as e:
        logger.exception(f"Error processing bookmark {bookmark_id}")
