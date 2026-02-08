"""
AI service module - extracted from server.py (Phase 6, Plan 01).

Provides Gemini AI rate limiting, embedding generation, entity extraction,
and AI summary generation for bookmark content processing.
"""

import asyncio
import json
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from typing import List, Optional

import google.generativeai as genai

from app.core.database import get_database

logger = logging.getLogger(__name__)


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


# Module-level singleton: shared across all consumers
gemini_rate_limiter = EnhancedGeminiRateLimiter(
    max_rpm=500,  # 50% of 1000 RPM (conservative buffer)
    max_tpm=500000,  # 50% of 1M tokens/min
    max_daily=5000,  # 50% of 10K requests/day
)


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


async def generate_ai_summaries(text_content: str, bookmark_id: str):
    """Generate AI summaries for bookmark content with timeout protection"""
    try:
        db = get_database()
        # Wrap AI processing with 60-second timeout to prevent hanging
        return await asyncio.wait_for(
            _generate_ai_summaries_impl(text_content, bookmark_id), timeout=60.0
        )
    except asyncio.TimeoutError:
        db = get_database()
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
        if not text_content or len(text_content.strip()) < 20:
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
- Be specific\u2014avoid generic statements like "this article discusses..."
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
- Use clear, direct language\u2014no filler phrases
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
                line = line.lstrip("-\u2022*0123456789.)")
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
                tag = tag.lstrip("-\u2022*0123456789.) ")
                if tag and len(tag) > 2 and len(tag) < 30:
                    suggested_tags.append(tag)
            suggested_tags = list(dict.fromkeys(suggested_tags))[:6]  # Preserve order, remove dupes

        db = get_database()
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
        db = get_database()
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
) -> tuple:
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
