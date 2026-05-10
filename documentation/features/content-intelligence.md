# Content Intelligence

**Status:** ✅ Backend Implemented (Roadmap Item 11)
**Implemented:** January 2026
**Frontend:** Integrated in Dashboard and Bookmark Detail
**API:** `/api/content/*`

---

## Overview

The Content Intelligence module uses AI to evaluate the quality, relevance, and uniqueness of web content before and after you save it. It helps you maintain a high-quality bookmark library by filtering out low-value content and identifying duplicates.

---

## Key Features

### 1. **Content Quality Scoring**
AI-powered evaluation of content based on:
- **Readability** - How easy is the content to understand?
- **Depth** - How comprehensive and detailed is the content?
- **Originality** - Is this original content or aggregated/copied?
- **Citations** - Does the content cite sources and references?
- **Structure** - Is the content well-organized?

### 2. **Duplicate Detection**
Identify duplicate or near-duplicate content:
- Exact URL matching
- Text similarity analysis (>85% similarity threshold)
- Title similarity detection
- Content fingerprinting

### 3. **Content Recommendations**
AI-generated suggestions:
- "This is high-quality original research - worth saving"
- "This appears to be a summary of existing content"
- "Consider reading the original source instead"
- "This content is already in your library"

### 4. **Pre-Save Evaluation**
Check content quality before adding to library:
- Preview quality score in extension/dashboard
- Warning for low-quality or duplicate content
- Option to save anyway or skip

---

## How It Works

### Backend Processing

1. **Content Fetching**
   - HTML content extracted from URL
   - Text cleaned and normalized
   - Metadata extracted (title, author, publish date)

2. **Quality Analysis**
   - Gemini 2.5 Flash analyzes content
   - Evaluates against quality criteria
   - Generates composite quality score (0-1)

3. **Duplicate Checking**
   - Compare URL against existing bookmarks
   - Calculate text similarity using embeddings
   - Flag if similarity > 85%

4. **Recommendation Generation**
   - Based on quality score and uniqueness
   - Personalized to user's library
   - Actionable suggestions provided

### Scoring Algorithm

**Quality Score Formula:**
```python
quality_score = (
    readability_score * 0.25 +
    depth_score * 0.30 +
    originality_score * 0.25 +
    citations_score * 0.10 +
    structure_score * 0.10
)
```

**Quality Levels:**
- **Excellent:** 0.85 - 1.00 (Original research, in-depth analysis)
- **Good:** 0.70 - 0.84 (Well-written articles, tutorials)
- **Fair:** 0.50 - 0.69 (Average blog posts, listicles)
- **Poor:** 0.00 - 0.49 (Low-effort content, clickbait)

---

## API Endpoints

### POST /api/content/evaluate
Evaluate content quality of a URL before saving.

**Request:**
```json
{
  "url": "https://example.com/article"
}
```

**Response:**
```json
{
  "url": "https://example.com/article",
  "quality_score": 0.85,
  "quality_level": "excellent",
  "factors": {
    "readability": 0.90,
    "depth": 0.80,
    "originality": 0.85,
    "citations": 0.70,
    "structure": 0.90
  },
  "recommendation": "High quality original content worth saving. Contains in-depth analysis with proper citations.",
  "warnings": [],
  "metadata": {
    "title": "Advanced Guide to Machine Learning",
    "author": "Dr. Jane Smith",
    "publish_date": "2026-01-10",
    "reading_time_minutes": 15,
    "word_count": 3500
  },
  "evaluated_at": "2026-01-12T10:00:00Z"
}
```

---

### POST /api/content/check-duplicate
Check if content is already in your library.

**Request:**
```json
{
  "url": "https://example.com/article"
}
```

**Response:**
```json
{
  "is_duplicate": true,
  "duplicate_type": "high_similarity",
  "existing_bookmark_id": "bookmark_abc123",
  "existing_bookmark": {
    "id": "bookmark_abc123",
    "title": "Machine Learning Guide",
    "url": "https://example.com/ml-guide",
    "saved_at": "2026-01-05T00:00:00Z"
  },
  "similarity_score": 0.92,
  "recommendation": "This content is very similar to an existing bookmark. Consider reviewing the existing one instead.",
  "checked_at": "2026-01-12T10:00:00Z"
}
```

**Duplicate Types:**
- `exact_url` - Exact same URL
- `high_similarity` - >85% text similarity
- `title_match` - Very similar title
- `not_duplicate` - Unique content

---

## Use Cases

### 1. **Quality Filtering**
"Before saving a bookmark, I check the quality score. If it's below 0.5, I skip it and look for better sources."

### 2. **Duplicate Prevention**
"The extension warned me I already saved this article last week under a different URL - saved me from a duplicate!"

### 3. **Source Prioritization**
"Content Intelligence told me this was a summary of another article - I saved the original instead."

### 4. **Library Curation**
"I periodically review low-quality bookmarks (score < 0.6) and clean up my library."

### 5. **Research Quality**
"When researching a topic, I filter for bookmarks with score > 0.8 to get the best sources."

---

## Configuration

### Quality Thresholds
```python
# Minimum score for automatic save
MIN_QUALITY_SCORE = 0.5

# Score for "excellent" badge
EXCELLENT_THRESHOLD = 0.85

# Score for warning display
WARNING_THRESHOLD = 0.6
```

### Duplicate Detection
```python
# Similarity threshold for duplicates
DUPLICATE_SIMILARITY_THRESHOLD = 0.85

# Text sample size for comparison
SIMILARITY_SAMPLE_SIZE = 2000  # characters
```

### AI Processing
```python
# Gemini model for evaluation
EVALUATION_MODEL = "gemini-2.5-flash"

# Max content length for analysis
MAX_CONTENT_LENGTH = 50000  # characters

# Timeout for evaluation
EVALUATION_TIMEOUT = 30  # seconds
```

---

## Performance

### Caching
- Content evaluations cached for 30 days
- Duplicate checks cached for 7 days
- Cache invalidated on bookmark changes

### Optimization
- Parallel processing for batch evaluations
- Background evaluation after initial save
- Incremental similarity matching (fast path for exact URLs)

### Database Indexes
- `url` - Fast URL lookup
- `content_hash` - Quick duplicate detection
- `quality_score` + `user_id` - Quality filtering

---

## Frontend Integration

### Dashboard Integration

**Quality Badges:**
```javascript
{score >= 0.85 && <Badge color="green">Excellent</Badge>}
{score >= 0.70 && score < 0.85 && <Badge color="blue">Good</Badge>}
{score >= 0.50 && score < 0.70 && <Badge color="yellow">Fair</Badge>}
{score < 0.50 && <Badge color="red">Poor</Badge>}
```

**Filter by Quality:**
```javascript
const highQualityBookmarks = bookmarks.filter(b => b.quality_score >= 0.8)
```

### Extension Integration

**Pre-Save Check:**
```javascript
// When user clicks "Save"
const evaluation = await fetch('/api/content/evaluate', {
  method: 'POST',
  body: JSON.stringify({ url: currentTab.url })
})

if (evaluation.quality_score < 0.5) {
  showWarning("This content has a low quality score. Save anyway?")
}

if (evaluation.is_duplicate) {
  showWarning("You already saved similar content!")
}
```

---

## Quality Factors Explained

### Readability (25% weight)
**Measures:** Sentence complexity, vocabulary level, paragraph length

**Good indicators:**
- Clear, concise sentences
- Appropriate vocabulary for audience
- Well-structured paragraphs
- Good use of headings and lists

**Poor indicators:**
- Run-on sentences
- Overly complex jargon
- Wall-of-text paragraphs
- Poor grammar/spelling

---

### Depth (30% weight - highest)
**Measures:** Content comprehensiveness, detail level, expertise

**Good indicators:**
- In-depth analysis
- Multiple perspectives covered
- Technical details and examples
- Original research or data

**Poor indicators:**
- Superficial coverage
- Lack of supporting evidence
- Generic/obvious advice
- Clickbait titles

---

### Originality (25% weight)
**Measures:** Content uniqueness, original insights

**Good indicators:**
- Original research or analysis
- Unique perspective
- Primary sources
- Author expertise demonstrated

**Poor indicators:**
- Copied/aggregated content
- No attribution to sources
- Rehashed common knowledge
- AI-generated generic content

---

### Citations (10% weight)
**Measures:** Source attribution, references

**Good indicators:**
- Links to original sources
- Academic/research citations
- Data sources identified
- Expert quotes attributed

**Poor indicators:**
- No sources cited
- Vague "studies show" claims
- Broken/missing links
- Circular references

---

### Structure (10% weight)
**Measures:** Content organization, formatting

**Good indicators:**
- Clear headings/subheadings
- Logical flow
- Good use of lists and tables
- Visual aids (charts, diagrams)

**Poor indicators:**
- No structure/organization
- Poor formatting
- Missing headings
- Hard to scan

---

## Evaluation Examples

### Example 1: Excellent Content (Score: 0.92)

**URL:** Research paper on new ML algorithm

**Breakdown:**
- Readability: 0.85 (Technical but clear)
- Depth: 0.95 (Comprehensive analysis, experiments, proofs)
- Originality: 1.00 (Novel research, original findings)
- Citations: 0.90 (Extensive references to related work)
- Structure: 0.90 (Well-organized with clear sections)

**Recommendation:** "Excellent original research with comprehensive analysis and strong citations. Highly recommended for saving."

---

### Example 2: Poor Content (Score: 0.35)

**URL:** Clickbait listicle

**Breakdown:**
- Readability: 0.60 (Easy to read but low substance)
- Depth: 0.20 (Superficial, no details)
- Originality: 0.10 (Aggregated content from elsewhere)
- Citations: 0.00 (No sources cited)
- Structure: 0.50 (Basic numbered list)

**Recommendation:** "Low-quality content with minimal depth and no original insights. Consider finding a better source on this topic."

---

## Limitations

Current limitations:
- English content only
- Requires full HTML content (no paywalls)
- Quality evaluation is subjective (AI-based)
- Slower for very long articles (>50k characters)

Not currently implemented:
- Multi-language quality scoring
- Paywall detection and handling
- User-customizable quality criteria
- Bulk evaluation of existing bookmarks
- Quality trend tracking over time

---

## Troubleshooting

### Evaluation fails
- Check URL is accessible (not behind paywall)
- Verify Gemini API key is configured
- Check content length (max 50k characters)
- Review backend logs for errors

### Incorrect quality score
- Quality is subjective and AI-based
- Report egregious errors via GitHub issues
- Consider content type (academic vs. blog post)

### Duplicate not detected
- Similarity threshold is 85% (adjustable)
- Check if URLs are very different
- Text content may have changed significantly

---

## Technical Implementation

### Libraries Used
- **NLP:** `scikit-learn` (text similarity, TF-IDF)
- **AI:** `google-generativeai` (Gemini evaluation)
- **Text Processing:** `beautifulsoup4` (HTML parsing)
- **Hashing:** `hashlib` (content fingerprinting)

### Database Schema

**Content Evaluation Collection:**
```json
{
  "url": "https://example.com/article",
  "url_hash": "md5_hash_of_url",
  "content_hash": "md5_hash_of_content",
  "quality_score": 0.85,
  "quality_factors": {
    "readability": 0.90,
    "depth": 0.80,
    "originality": 0.85,
    "citations": 0.70,
    "structure": 0.90
  },
  "recommendation": "High quality...",
  "evaluated_at": "2026-01-12T10:00:00Z",
  "cached_until": "2026-02-11T10:00:00Z"
}
```

**Bookmark Quality (embedded):**
```json
{
  "id": "bookmark_xyz",
  "url": "https://example.com/article",
  "quality_score": 0.85,
  "quality_level": "excellent",
  "quality_evaluated_at": "2026-01-12T10:00:00Z"
}
```

---

## Best Practices

### For Users
1. Check quality score before saving from unknown sources
2. Enable duplicate warnings in extension settings
3. Periodically review low-quality bookmarks (score < 0.6)
4. Trust the score but also use your judgment

### For Developers
1. Cache evaluations to reduce API calls
2. Process evaluations in background after save
3. Handle timeout gracefully (degrade to no score)
4. Don't block saves on evaluation failures

---

## Related Features

- **[Duplicates Detection](duplicates-detection.md)** - Uses content intelligence for similarity
- **[Analytics](analytics.md)** - Tracks quality distribution in your library
- **Dashboard** - Displays quality badges on bookmarks

---

## References

- **API Docs:** [documentation/api/README.md](../api/README.md#content-intelligence-endpoints)
- **Architecture:** [documentation/architecture.md](../architecture.md)

---

**Last Updated:** May 10, 2026
**Status:** Implemented for URL quality evaluation and bookmark detail quality display
