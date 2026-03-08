"""
Content Intelligence Module
Provides content quality evaluation, credibility scoring, and duplicate detection.

Part of Advanced Content Intelligence & Curation (Roadmap Item 11)
"""

from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Optional, Dict, Tuple, List
import re
import logging

logger = logging.getLogger(__name__)

# Trusted source domains (expanded list)
ACADEMIC_DOMAINS = {
    '.edu', '.gov', '.ac.uk', '.edu.au', '.edu.cn',
    'arxiv.org', 'scholar.google.com', 'pubmed.ncbi.nlm.nih.gov',
    'nature.com', 'science.org', 'ieee.org', 'acm.org'
}

TRUSTED_NEWS_OUTLETS = {
    'nytimes.com', 'washingtonpost.com', 'bbc.com', 'bbc.co.uk',
    'reuters.com', 'apnews.com', 'theguardian.com', 'economist.com',
    'wsj.com', 'ft.com', 'bloomberg.com', 'npr.org', 'pbs.org'
}

TECH_AUTHORITY_SITES = {
    'github.com', 'stackoverflow.com', 'developer.mozilla.org',
    'docs.python.org', 'reactjs.org', 'nodejs.org', 'kubernetes.io',
    'aws.amazon.com', 'cloud.google.com', 'azure.microsoft.com',
    'hbr.org', 'mitsloan.mit.edu', 'ycombinator.com'
}

KNOWN_LOW_QUALITY = {
    'buzzfeed.com', 'dailymail.co.uk', 'thesun.co.uk',
    'examiner.com', 'naturalnews.com'
}


def calculate_credibility_score(
    url: str,
    content: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Tuple[int, Dict[str, any]]:
    """
    Calculate credibility score for a URL/content.
    
    Args:
        url: The URL to evaluate
        content: Optional text content of the page
        metadata: Optional metadata dict with keys like 'publication_date', 'author', 'title'
    
    Returns:
        Tuple of (score 0-100, breakdown dict)
    """
    score = 50  # Start at neutral
    breakdown = {
        "source_authority": 0,
        "citation_quality": 0,
        "content_depth": 0,
        "recency": 0,
        "author": 0,
        "penalties": 0
    }
    
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace('www.', '')
    
    # 1. Source Authority (+20 points max)
    if any(domain.endswith(edu) for edu in ACADEMIC_DOMAINS) or domain in ACADEMIC_DOMAINS:
        breakdown["source_authority"] = 20
    elif domain in TRUSTED_NEWS_OUTLETS:
        breakdown["source_authority"] = 15
    elif domain in TECH_AUTHORITY_SITES:
        breakdown["source_authority"] = 12
    elif domain in KNOWN_LOW_QUALITY:
        breakdown["source_authority"] = -10
        breakdown["penalties"] = -10
    else:
        # Unknown sources get neutral score
        breakdown["source_authority"] = 0
    
    # 2. Citation Quality (+15 points max) - count outbound links
    if content:
        # Count http/https links in content (excluding same domain)
        link_pattern = r'https?://(?:www\.)?([a-zA-Z0-9.-]+)'
        links = re.findall(link_pattern, content)
        # Filter out same-domain links
        external_links = [l for l in links if l.lower().replace('www.', '') != domain]
        unique_external_links = len(set(external_links))
        
        if unique_external_links >= 10:
            breakdown["citation_quality"] = 15
        elif unique_external_links >= 5:
            breakdown["citation_quality"] = 10
        elif unique_external_links >= 2:
            breakdown["citation_quality"] = 5
        elif unique_external_links == 0:
            breakdown["citation_quality"] = -5
    
    # 3. Content Depth (+10 points max)
    if content:
        word_count = len(content.split())
        if word_count >= 2000:
            breakdown["content_depth"] = 10
        elif word_count >= 1000:
            breakdown["content_depth"] = 7
        elif word_count >= 500:
            breakdown["content_depth"] = 5
        elif word_count < 300:
            breakdown["content_depth"] = -5
    
    # 4. Recency (+10 points max)
    if metadata and metadata.get('publication_date'):
        pub_date = metadata['publication_date']
        if isinstance(pub_date, str):
            try:
                pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pub_date = None
        
        if pub_date:
            days_old = (datetime.now(timezone.utc) - pub_date).days
            if days_old < 30:
                breakdown["recency"] = 10
            elif days_old < 180:
                breakdown["recency"] = 7
            elif days_old < 365:
                breakdown["recency"] = 5
            elif days_old > 1825:  # > 5 years
                breakdown["recency"] = -5
    
    # 5. Author Presence (+5 points max)
    if metadata and metadata.get('author'):
        author = metadata['author']
        if len(author) > 2 and author.lower() not in ['admin', 'administrator', 'staff', 'team']:
            breakdown["author"] = 5
    
    # Calculate total
    score = 50 + sum(breakdown.values())
    score = min(100, max(0, score))  # Clamp to 0-100
    
    breakdown["total"] = score
    
    return score, breakdown


def get_quality_label(score: int) -> Tuple[str, str]:
    """
    Get human-readable quality label and color.
    
    Args:
        score: Credibility score 0-100
    
    Returns:
        Tuple of (label, color_class)
    """
    if score >= 80:
        return ("High Quality", "success")
    elif score >= 60:
        return ("Good Quality", "info")
    elif score >= 40:
        return ("Average Quality", "warning")
    else:
        return ("Low Quality", "error")


def get_quality_badges(breakdown: Dict) -> List[Dict]:
    """
    Generate quality badges based on score breakdown.
    
    Args:
        breakdown: Score breakdown from calculate_credibility_score
    
    Returns:
        List of badge dicts with 'text', 'type' (positive/negative/neutral)
    """
    badges = []
    
    # Source authority badges
    if breakdown.get("source_authority", 0) >= 15:
        badges.append({"text": "Trusted Source", "type": "positive"})
    elif breakdown.get("source_authority", 0) >= 10:
        badges.append({"text": "Authoritative", "type": "positive"})
    elif breakdown.get("source_authority", 0) < 0:
        badges.append({"text": "Low Authority", "type": "negative"})
    
    # Citation badges
    if breakdown.get("citation_quality", 0) >= 10:
        badges.append({"text": "Well-Cited", "type": "positive"})
    elif breakdown.get("citation_quality", 0) < 0:
        badges.append({"text": "Few Sources", "type": "negative"})
    
    # Content depth badges
    if breakdown.get("content_depth", 0) >= 7:
        badges.append({"text": "In-Depth", "type": "positive"})
    elif breakdown.get("content_depth", 0) < 0:
        badges.append({"text": "Brief Content", "type": "neutral"})
    
    # Recency badges
    if breakdown.get("recency", 0) >= 7:
        badges.append({"text": "Recent", "type": "positive"})
    elif breakdown.get("recency", 0) < 0:
        badges.append({"text": "Dated", "type": "negative"})
    
    # Author badge
    if breakdown.get("author", 0) > 0:
        badges.append({"text": "Named Author", "type": "positive"})
    
    return badges


async def check_duplicate_url(url: str, user_id: str, db) -> Dict:
    """
    Check if URL or similar URL already exists for this user.
    
    Args:
        url: URL to check
        user_id: User ID to check against
        db: Database instance
    
    Returns:
        Dict with 'is_duplicate', 'existing_bookmark' (if found), 'similarity_type'
    """
    parsed = urlparse(url)
    
    # Normalize URL for comparison
    normalized_url = url.lower().rstrip('/')
    # Remove common query params that don't change content
    normalized_url = re.sub(r'\?(utm_[^&]+&?)+', '', normalized_url)
    normalized_url = re.sub(r'[?&]ref=[^&]+', '', normalized_url)
    
    # Extract canonical components
    domain = parsed.netloc.lower().replace('www.', '')
    path = parsed.path.rstrip('/')
    
    # Check 1: Exact URL match
    existing = await db.bookmarks.find_one({
        "user_id": user_id,
        "url": {"$regex": f"^https?://(www\\.)?{re.escape(domain)}{re.escape(path)}/?", "$options": "i"}
    }, {"_id": 0, "id": 1, "title": 1, "url": 1, "created_at": 1, "thumbnail": 1})
    
    if existing:
        return {
            "is_duplicate": True,
            "existing_bookmark": existing,
            "similarity_type": "exact_url"
        }
    
    # Check 2: Same domain + similar path (might be same article with different params)
    # Find bookmarks on same domain
    domain_bookmarks = await db.bookmarks.find({
        "user_id": user_id,
        "domain": domain
    }, {"_id": 0, "id": 1, "title": 1, "url": 1, "created_at": 1}).to_list(100)
    
    for bm in domain_bookmarks:
        bm_parsed = urlparse(bm["url"])
        bm_path = bm_parsed.path.rstrip('/')
        
        # Check if paths are very similar (might be pagination or variant)
        if path and bm_path:
            # Simple similarity: check if one is prefix of other or they share most of path
            common_prefix = len(set(path.split('/')) & set(bm_path.split('/')))
            total_parts = max(len(path.split('/')), len(bm_path.split('/')))
            
            if total_parts > 0 and common_prefix / total_parts >= 0.8:
                return {
                    "is_duplicate": True,
                    "existing_bookmark": bm,
                    "similarity_type": "similar_url"
                }
    
    return {
        "is_duplicate": False,
        "existing_bookmark": None,
        "similarity_type": None
    }
