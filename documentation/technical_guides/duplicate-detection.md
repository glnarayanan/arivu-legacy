# Duplicate Detection

> **One-liner:** Find bookmarks you've saved multiple times — even if the URLs are slightly different.

## What Is It?

Duplicate Detection identifies bookmarks that are either:

1. **Exact duplicates** — Same URL saved twice
2. **Near-duplicates** — Same content with different URLs (e.g., with/without tracking parameters)
3. **Similar content** — Different articles covering nearly identical information

## Why It Matters

**The Problem:**
- You bookmark an article, forget about it, bookmark it again
- You save the same article from different sources (Twitter link vs. direct link)
- You end up with 5 slightly different "How to Use Git" tutorials

**The Solution:**
- Arivu identifies duplicates so you can merge or delete them
- Keep your library clean and organized
- Free up mental space by reducing clutter

## How It Works

### Method 1: Exact URL Matching

The simplest approach — check if the URL already exists.

**Normalization steps:**
1. Convert to lowercase
2. Remove trailing slashes
3. Strip tracking parameters (`?utm_source=`, `?ref=`, etc.)

```
Original: https://www.Example.com/Article/?utm_source=twitter
Normalized: https://example.com/article
```

**If two bookmarks have the same normalized URL → they're duplicates.**

### Method 2: Similar URL Detection

Sometimes the same article has slightly different paths:

```
URL 1: https://blog.example.com/2024/01/my-article
URL 2: https://blog.example.com/2024/01/my-article/page/2
```

**The algorithm:**
1. Extract the domain and path components
2. Split paths into segments
3. Calculate overlap percentage
4. If 80%+ overlap on same domain → likely duplicate

### Method 3: Content Similarity (TF-IDF)

For articles that are similar but have completely different URLs.

**TF-IDF Explained Simply:**
- **TF (Term Frequency):** How often a word appears in this document
- **IDF (Inverse Document Frequency):** How unique is this word across all documents
- **Result:** Important words get high scores, common words (the, and) get low scores

**The Process:**
1. Take the first 1000 characters of each bookmark's content
2. Convert to TF-IDF vectors (numerical representation of word importance)
3. Calculate cosine similarity between all pairs
4. If similarity > 85% → flag as similar content

## Key Functions Explained

### `check_duplicate_url(url, user_id)`
Called when saving a new bookmark. Checks if it already exists.

**Returns:**
```json
{
  "is_duplicate": true,
  "existing_bookmark": { "id": "...", "title": "...", "url": "..." },
  "similarity_type": "exact_url" | "similar_url"
}
```

### `detect_duplicates()`
Scans your entire library for duplicates.

**How it works:**
1. Fetch all bookmarks (up to 500)
2. Group by normalized URL → find exact duplicates
3. Build TF-IDF matrix of content
4. Calculate pairwise similarity → find similar content
5. Return grouped duplicates

**Returns:**
```json
{
  "duplicates": [
    {
      "type": "exact_url",
      "bookmarks": [bookmark1, bookmark2]
    },
    {
      "type": "similar_content",
      "similarity": 0.92,
      "bookmarks": [bookmark3, bookmark4]
    }
  ]
}
```

### `merge_bookmarks(bookmark_ids)`
Combine multiple duplicates into one.

**Merge logic:**
- Keep the oldest bookmark (first saved)
- Combine all tags and notes
- Delete the duplicates

## Real-World Examples

### Example 1: Same Article, Different Links

```
Bookmark 1: https://techcrunch.com/2024/01/15/ai-startup-raises-funding
Bookmark 2: https://techcrunch.com/2024/01/15/ai-startup-raises-funding/?utm_source=newsletter
```

**Detected as:** Exact URL duplicate (after normalization)

### Example 2: Same Content, Different Sources

```
Bookmark 1: Original blog post at example.com
Bookmark 2: Same post syndicated to medium.com
```

**Detected as:** Similar content (87% TF-IDF similarity)

### Example 3: Updated Article

```
Bookmark 1: "React 18 Features" (saved January)
Bookmark 2: "React 18 Features (Updated)" (saved March)
```

**Detected as:** Similar content (90% overlap)

## The 85% Threshold

Why 85% similarity to flag as duplicate?

- **Too low (60%):** Catches articles on same topic but different content
- **Too high (95%):** Misses articles with minor edits
- **Just right (85%):** Catches true duplicates while allowing related content

## Technical Details

| Component | Technology | Purpose |
|-----------|------------|---------|
| URL Parsing | Python `urlparse` | Extract domain/path for comparison |
| Text Vectorization | scikit-learn `TfidfVectorizer` | Convert text to numerical vectors |
| Similarity Calculation | scikit-learn `cosine_similarity` | Compare TF-IDF vectors |
| Content Limit | First 1000 chars | Balance accuracy vs. performance |

## Content Similarity Formula

The cosine similarity between two documents:

```
                    A · B
cos(θ) = ─────────────────────
           ‖A‖ × ‖B‖
```

Where:
- A and B are TF-IDF vectors
- Result ranges from 0 (completely different) to 1 (identical)
- We flag pairs with similarity > 0.85

## User Actions

When duplicates are detected, users can:

1. **Merge** — Combine into one bookmark, keeping all metadata
2. **Delete** — Remove the duplicate
3. **Ignore** — Mark as "not a duplicate" (for intentionally saved similar content)
