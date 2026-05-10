# Duplicates Detection & Management

**Status:** ✅ Fully Implemented
**Implemented:** January 2026
**Frontend:** `/duplicates`
**API:** `/api/bookmarks/duplicates/*`, `/api/bookmarks/merge`

---

## Overview

The Duplicates Detection feature automatically identifies duplicate and near-duplicate bookmarks in your library using URL matching and AI-powered text similarity analysis. It helps keep your bookmark library clean and organized by merging or removing redundant content.

---

## Key Features

### 1. **Multi-Level Detection**
Finds duplicates using three methods:
- **Exact URL Match** - Same URL (100% duplicate)
- **Normalized URL Match** - URLs that normalize to same (http/https, www/non-www, trailing slashes)
- **Content Similarity** - Text similarity >85% (near-duplicates)

### 2. **Smart Grouping**
Groups duplicates intelligently:
- Primary bookmark (canonical) identified
- Duplicates listed with similarity scores
- Visual indication of duplicate reason

### 3. **Flexible Merging**
Multiple merge strategies:
- **Keep All Tags** - Combine tags from all duplicates
- **Keep All Highlights** - Merge highlights and notes
- **Keep Best Quality** - Select highest quality score
- **Manual Selection** - Choose which data to keep

### 4. **Bulk Actions**
Manage duplicates efficiently:
- Merge all duplicate groups at once
- Delete duplicates without merging
- Ignore specific duplicates
- Undo recent merges

---

## How It Works

### Detection Algorithm

1. **URL Normalization**
   ```python
   # Normalize URLs for comparison
   url = url.lower()
   url = url.replace('https://', 'http://')
   url = url.replace('www.', '')
   url = url.rstrip('/')
   url = remove_query_params(url, ['utm_*', 'ref', 'source'])
   ```

2. **Exact URL Match**
   - Direct URL comparison
   - Fastest detection method
   - 100% confidence duplicates

3. **Content Similarity**
   - Extract text content from both bookmarks
   - Generate embeddings using TF-IDF vectors
   - Calculate cosine similarity
   - Flag if similarity >85%

4. **Grouping**
   - Group bookmarks by normalized URL
   - Group similar content bookmarks
   - Select canonical (oldest or highest quality)
   - Rank duplicates by similarity

### Merge Process

1. **Data Consolidation**
   - Combine tags (unique values)
   - Merge highlights (deduplicate)
   - Preserve best summary
   - Keep highest quality score

2. **Canonical Update**
   - Update canonical bookmark with merged data
   - Add merge metadata (source IDs, timestamp)

3. **Duplicate Removal**
   - Delete duplicate bookmarks
   - Log merge action for undo
   - Update related collections

4. **Cleanup**
   - Reindex search
   - Update analytics
   - Clear caches

---

## API Endpoints

### GET /api/bookmarks/duplicates/detect
Detect all duplicate bookmarks for current user.

**Response:**
```json
{
  "duplicate_groups": [
    {
      "canonical_id": "bookmark_1",
      "canonical_bookmark": {
        "id": "bookmark_1",
        "url": "https://example.com/article",
        "title": "Complete Guide to ML",
        "created_at": "2026-01-01T00:00:00Z",
        "quality_score": 0.90
      },
      "duplicates": [
        {
          "id": "bookmark_2",
          "url": "https://example.com/article?utm_source=twitter",
          "title": "Guide to ML",
          "created_at": "2026-01-05T00:00:00Z",
          "similarity_score": 1.00,
          "similarity_type": "exact_url",
          "quality_score": 0.85
        },
        {
          "id": "bookmark_3",
          "url": "https://medium.com/ml-guide",
          "title": "Machine Learning Guide",
          "created_at": "2026-01-10T00:00:00Z",
          "similarity_score": 0.92,
          "similarity_type": "content_similarity",
          "quality_score": 0.80
        }
      ],
      "total_duplicates": 2
    }
  ],
  "total_groups": 1,
  "total_duplicates": 2,
  "detection_time": "2026-01-12T10:00:00Z"
}
```

**Similarity Types:**
- `exact_url` - Exact same URL
- `normalized_url` - URLs normalize to same
- `content_similarity` - High text similarity (>85%)
- `title_match` - Very similar titles

---

### POST /api/bookmarks/merge
Merge duplicate bookmarks into canonical.

**Request:**
```json
{
  "primary_id": "bookmark_1",
  "duplicate_ids": ["bookmark_2", "bookmark_3"],
  "merge_strategy": "keep_all_tags",
  "merge_highlights": true,
  "merge_notes": true,
  "keep_best_quality": true
}
```

**Merge Strategies:**
- `keep_all_tags` - Combine all unique tags
- `keep_primary_tags` - Only primary bookmark tags
- `keep_duplicate_tags` - Only duplicate tags

**Response:**
```json
{
  "merged_bookmark": {
    "id": "bookmark_1",
    "url": "https://example.com/article",
    "title": "Complete Guide to ML",
    "tags": ["ml", "ai", "guide", "tutorial"],  // Merged from all
    "highlights": [
      "Key quote from primary",
      "Important insight from duplicate"
    ],
    "quality_score": 0.90,  // Best quality kept
    "merged_from": ["bookmark_2", "bookmark_3"],
    "merged_at": "2026-01-12T10:00:00Z"
  },
  "deleted_ids": ["bookmark_2", "bookmark_3"],
  "merge_metadata": {
    "tags_added": ["tutorial"],
    "highlights_added": 1,
    "quality_improved": false
  }
}
```

---

## Use Cases

### 1. **After Import**
"I imported bookmarks from Pocket and Raindrop.io - the duplicate detector found 50 overlaps and helped me merge them."

### 2. **Browser Extension Duplicates**
"I accidentally saved the same article from two different URLs - duplicates detection caught it."

### 3. **Content Aggregation**
"I saved both the original article and a Medium re-publication - the system detected 92% similarity and suggested merging."

### 4. **Library Cleanup**
"Periodic duplicate scans keep my library clean - I run detection monthly and merge any duplicates."

### 5. **Tag Consolidation**
"Merging duplicates also merged my tags 'ML', 'machine-learning', and 'MachineLearning' - helped organize better."

---

## Duplicate Detection Rules

### Exact URL Duplicates
```python
# Considered exact duplicates:
"https://example.com/article"
"http://example.com/article"
"https://www.example.com/article"
"https://example.com/article/"
"https://example.com/article?utm_source=twitter"
```

### Content Similarity Duplicates
```python
# Similarity calculation
similarity_score = cosine_similarity(
    tfidf_vector_1,
    tfidf_vector_2
)

# Threshold
if similarity_score >= 0.85:
    flag_as_duplicate()
```

### Title Similarity
```python
# Fuzzy title matching
from difflib import SequenceMatcher

title_similarity = SequenceMatcher(
    None, title1.lower(), title2.lower()
).ratio()

if title_similarity >= 0.90:
    flag_as_potential_duplicate()
```

---

## Canonical Selection

The system chooses canonical bookmark based on:

1. **Quality Score** (highest weight)
   - Highest quality_score wins

2. **Age** (oldest preferred)
   - Older bookmarks preferred (first saved)

3. **Completeness**
   - Most tags, highlights, notes
   - Best summary quality

4. **Read Status**
   - Read bookmarks preferred over unread

**Selection Formula:**
```python
canonical_score = (
    quality_score * 0.40 +
    age_score * 0.30 +
    completeness_score * 0.20 +
    read_status_score * 0.10
)
```

---

## Merge Strategies

### Strategy 1: Keep All Tags
Combines all unique tags from all bookmarks:
```python
primary_tags = ["ai", "ml"]
duplicate_tags = ["machine-learning", "tutorial"]
merged_tags = ["ai", "ml", "machine-learning", "tutorial"]
```

### Strategy 2: Keep All Highlights
Merges and deduplicates highlights:
```python
primary_highlights = ["Quote 1", "Quote 2"]
duplicate_highlights = ["Quote 2", "Quote 3"]  # Quote 2 duplicate
merged_highlights = ["Quote 1", "Quote 2", "Quote 3"]
```

### Strategy 3: Keep Best Quality
Selects data from highest quality bookmark:
```python
if duplicate.quality_score > primary.quality_score:
    use_duplicate_summary = True
    use_duplicate_highlights = True
```

### Strategy 4: Smart Merge (Default)
Combines best aspects from all:
```python
merged = {
    "tags": unique(primary.tags + duplicate.tags),
    "highlights": dedupe(primary.highlights + duplicate.highlights),
    "summary": best_summary_by_quality,
    "quality_score": max(primary.quality_score, duplicate.quality_score)
}
```

---

## Configuration

### Detection Thresholds
```python
# Content similarity threshold
DUPLICATE_SIMILARITY_THRESHOLD = 0.85

# Title similarity threshold
TITLE_SIMILARITY_THRESHOLD = 0.90

# URL normalization aggressive
NORMALIZE_URLS = True
REMOVE_QUERY_PARAMS = True
```

### Performance
```python
# Batch size for duplicate detection
DUPLICATE_DETECTION_BATCH_SIZE = 100

# Max comparisons per bookmark
MAX_COMPARISONS = 1000  # Prevent O(n²) explosion

# Cache duplicate results
CACHE_DUPLICATE_DETECTION = True
CACHE_TTL = 3600  # 1 hour
```

---

## Frontend Implementation

### Duplicates Page (`/duplicates`)

**Components:**
1. **DetectionButton** - Trigger duplicate scan
2. **DuplicateGroupList** - Display grouped duplicates
3. **DuplicateCard** - Show canonical + duplicates
4. **MergeDialog** - Merge options and preview
5. **BulkActions** - Merge all or delete all

**State Management:**
```javascript
const [duplicateGroups, setDuplicateGroups] = useState([])
const [detecting, setDetecting] = useState(false)
const [selectedGroup, setSelectedGroup] = useState(null)
const [mergeStrategy, setMergeStrategy] = useState('keep_all_tags')
```

**Duplicate Detection Flow:**
```javascript
const detectDuplicates = async () => {
  setDetecting(true)
  const result = await fetch('/api/bookmarks/duplicates/detect')
  setDuplicateGroups(result.duplicate_groups)
  setDetecting(false)
}
```

**Merge Flow:**
```javascript
const mergeDuplicates = async (primary_id, duplicate_ids) => {
  const result = await fetch('/api/bookmarks/merge', {
    method: 'POST',
    body: JSON.stringify({
      primary_id,
      duplicate_ids,
      merge_strategy: mergeStrategy
    })
  })

  // Remove merged group from list
  setDuplicateGroups(groups =>
    groups.filter(g => g.canonical_id !== primary_id)
  )
}
```

---

## Performance Optimization

### Indexing
- `url_normalized` - B-tree index for fast lookups
- `content_hash` - For quick exact content matches
- `embedding_vector` - For similarity search

### Caching
- Detection results cached for 1 hour
- Invalidated on new bookmarks
- Per-user cache key

### Batch Processing
```python
# Process in batches to avoid memory issues
for batch in batches(bookmarks, size=100):
    detect_duplicates_in_batch(batch)
```

### Smart Comparison
```python
# Skip unlikely duplicates
if abs(len(text1) - len(text2)) / max(len(text1), len(text2)) > 0.5:
    skip_comparison()  # Too different in length
```

---

## Best Practices

### For Users
1. Run duplicate detection after imports
2. Review duplicates before bulk merging
3. Check merge preview carefully
4. Keep backups before major merges
5. Use quality scores to guide canonical selection

### For Developers
1. Always normalize URLs before comparison
2. Cache similarity calculations
3. Limit comparisons to prevent O(n²)
4. Provide undo for merge operations
5. Log all merge actions

---

## Limitations

Current limitations:
- Maximum 10,000 bookmarks for detection
- Content similarity only works for text content
- No detection for video/image duplicates
- English content optimized (TF-IDF)

Not currently implemented:
- Multi-language similarity tuning
- Image duplicate detection
- URL shortener expansion for fuzzy URL matching
- Automatic merge suggestions
- Scheduled duplicate detection

---

## Troubleshooting

### No duplicates detected
- Ensure bookmarks are processed (status: "completed")
- Check similarity threshold (may be too high)
- Verify bookmark count (min 2 bookmarks needed)

### False positives (not real duplicates)
- Adjust similarity threshold higher
- Check content extraction (may be incomplete)
- Review title matching logic

### Merge failed
- Check bookmark permissions (user_id match)
- Verify bookmark still exists
- Check for concurrent modifications
- Review backend logs

---

## Technical Implementation

### Libraries Used
- **Similarity:** `scikit-learn` (TF-IDF, cosine similarity)
- **Text Processing:** `beautifulsoup4` (content extraction)
- **Fuzzy Matching:** `difflib` (title similarity)
- **URL Parsing:** `urllib.parse` (URL normalization)

### Database Schema

**Bookmark with Merge Metadata:**
```json
{
  "id": "bookmark_1",
  "url": "https://example.com/article",
  "url_normalized": "http://example.com/article",
  "content_hash": "md5_hash_of_content",
  "merged_from": ["bookmark_2", "bookmark_3"],
  "merged_at": "2026-01-12T10:00:00Z",
  "merge_metadata": {
    "original_tags": ["ai"],
    "tags_added_from_merge": ["ml", "tutorial"],
    "highlights_added": 2
  }
}
```

**Duplicate Detection Cache:**
```json
{
  "user_id": "user_id",
  "duplicate_groups": [ /* ... */ ],
  "generated_at": "2026-01-12T10:00:00Z",
  "expires_at": "2026-01-12T11:00:00Z"
}
```

---

## Edge Cases

### Different URLs, Same Content
**Example:** Original article vs. Medium re-publication
- **Detection:** Content similarity >90%
- **Recommendation:** Keep original, merge tags
- **Action:** User decides which to keep

### Same URL, Different Timestamps
**Example:** Article updated/edited over time
- **Detection:** Exact URL match
- **Recommendation:** Keep latest version
- **Action:** Automatically merge (configurable)

### URL Shorteners
**Example:** bit.ly/abc → https://example.com/article
- **Detection:** Currently not detected (planned feature)
- **Workaround:** Manual merge
- **Future:** Resolve shortened URLs before comparison

---

## Related Features

- **[Content Intelligence](content-intelligence.md)** - Quality scores guide canonical selection
- **[Import/Export](import-export.md)** - Duplicate detection runs during import
- **Dashboard** - Shows duplicate count badge

---

## References

- **API Docs:** [documentation/api/README.md](../api/README.md#duplicates-endpoints)
- **Algorithm:** TF-IDF Cosine Similarity - https://en.wikipedia.org/wiki/Tf%E2%80%93idf

---

**Last Updated:** May 10, 2026
**Status:** Implemented for URL/text duplicate detection and manual merge
