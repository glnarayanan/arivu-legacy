# Content Intelligence

> **One-liner:** Know which sources to trust with automatic quality and credibility scoring.

## What Is It?

Content Intelligence evaluates the quality and credibility of your saved content by analyzing:

- **Source Authority** — Is this from a reputable website?
- **Citation Quality** — Does the article link to external sources?
- **Content Depth** — Is this substantial or thin content?
- **Recency** — Is this current or outdated?
- **Author Attribution** — Is there a named author?

Each bookmark gets a credibility score (0-100) and quality badges.

## Why It Matters

**The Misinformation Problem:**
- Not all sources are equally reliable
- A random blog post isn't the same as MIT research
- You save content quickly without vetting sources

**The Solution:**
- Automatic quality assessment at save time
- Visual badges show source credibility
- Make informed decisions about what to trust

## How the Scoring Works

Every bookmark starts at **50 points** (neutral) and gains or loses points based on factors:

### Factor 1: Source Authority (+20 to -10 points)

| Source Type | Points | Examples |
|-------------|--------|----------|
| Academic (.edu, .gov) | +20 | mit.edu, nih.gov, arxiv.org |
| Trusted News | +15 | nytimes.com, bbc.com, reuters.com |
| Tech Authority | +12 | github.com, developer.mozilla.org |
| Unknown Source | 0 | Most websites |
| Known Low Quality | -10 | Sites with history of misinformation |

**Trusted source lists:**
- **Academic:** .edu, .gov, arxiv.org, nature.com, ieee.org, acm.org
- **News:** nytimes.com, washingtonpost.com, bbc.com, reuters.com, economist.com
- **Tech:** github.com, stackoverflow.com, developer.mozilla.org, official documentation sites

### Factor 2: Citation Quality (+15 to -5 points)

Does the content link to external sources?

| External Links | Points | Meaning |
|----------------|--------|---------|
| 10+ unique | +15 | Well-researched |
| 5-9 | +10 | Good research |
| 2-4 | +5 | Some sources |
| 1 | 0 | Minimal sourcing |
| 0 | -5 | No external sources |

**How it's calculated:**
- Extract all URLs from content
- Filter out same-domain links (internal navigation)
- Count unique external domains

### Factor 3: Content Depth (+10 to -5 points)

How substantial is the content?

| Word Count | Points | Category |
|------------|--------|----------|
| 2000+ | +10 | In-depth |
| 1000-1999 | +7 | Substantial |
| 500-999 | +5 | Medium |
| 300-499 | 0 | Brief |
| < 300 | -5 | Too thin |

### Factor 4: Recency (+10 to -5 points)

How current is the publication?

| Age | Points | Status |
|-----|--------|--------|
| < 30 days | +10 | Fresh |
| 30-180 days | +7 | Recent |
| 6-12 months | +5 | Relevant |
| 1-5 years | 0 | Neutral |
| > 5 years | -5 | Dated |

*Note: Requires publication date metadata*

### Factor 5: Author Attribution (+5 points)

Is there a named, credible author?

| Author | Points |
|--------|--------|
| Named individual | +5 |
| "Admin", "Staff", "Team" | 0 |
| No author | 0 |

## Final Score Interpretation

| Score Range | Label | Color |
|-------------|-------|-------|
| 80-100 | High Quality | Green |
| 60-79 | Good Quality | Blue |
| 40-59 | Average Quality | Yellow |
| 0-39 | Low Quality | Red |

## Quality Badges

Based on the scoring breakdown, bookmarks get visual badges:

**Positive Badges (green):**
- 🏛️ Trusted Source (high source authority)
- 🔗 Well-Cited (many external sources)
- 📖 In-Depth (substantial content)
- 🕐 Recent (published recently)
- ✍️ Named Author (has attribution)

**Negative Badges (red):**
- ⚠️ Low Authority (questionable source)
- 📭 Few Sources (no citations)
- ⏳ Dated (old content)

**Neutral Badges (gray):**
- 📝 Brief Content (short but not necessarily bad)

## Key Functions Explained

### `calculate_credibility_score(url, content, metadata)`
Main scoring function.

**Parameters:**
- `url` — The bookmark URL
- `content` — Optional text content
- `metadata` — Optional dict with `publication_date`, `author`, `title`

**Returns:**
```python
(
  75,  # Total score
  {
    "source_authority": 15,
    "citation_quality": 10,
    "content_depth": 7,
    "recency": 5,
    "author": 5,
    "penalties": 0,
    "total": 75
  }
)
```

### `get_quality_label(score)`
Converts score to human-readable label.

```python
get_quality_label(85)  # Returns: ("High Quality", "success")
get_quality_label(45)  # Returns: ("Average Quality", "warning")
```

### `get_quality_badges(breakdown)`
Generates badge list from score breakdown.

```python
get_quality_badges({"source_authority": 15, "citation_quality": 10})
# Returns:
# [
#   {"text": "Trusted Source", "type": "positive"},
#   {"text": "Well-Cited", "type": "positive"}
# ]
```

## Real-World Examples

### Example 1: Academic Paper

**URL:** arxiv.org/abs/2301.12345
**Content:** 5000 words with 50 citations
**Author:** Dr. Jane Smith, MIT

| Factor | Score |
|--------|-------|
| Source Authority | +20 (academic domain) |
| Citation Quality | +15 (50+ citations) |
| Content Depth | +10 (5000 words) |
| Recency | +7 (3 months old) |
| Author | +5 (named researcher) |
| **Total** | **50 + 57 = 100** (capped) |

**Badges:** 🏛️ Trusted Source, 🔗 Well-Cited, 📖 In-Depth, ✍️ Named Author

### Example 2: Random Blog Post

**URL:** myblog.wordpress.com/thoughts
**Content:** 400 words, no citations
**Author:** "Admin"

| Factor | Score |
|--------|-------|
| Source Authority | 0 (unknown) |
| Citation Quality | -5 (no sources) |
| Content Depth | 0 (400 words) |
| Recency | 0 (no date) |
| Author | 0 ("Admin") |
| **Total** | **50 - 5 = 45** |

**Badges:** 📭 Few Sources

### Example 3: Known Unreliable Source

**URL:** knowninfosite.com/article
**Content:** 600 words, 2 citations

| Factor | Score |
|--------|-------|
| Source Authority | -10 (known low quality) |
| Citation Quality | +5 (2 citations) |
| Content Depth | +5 (600 words) |
| Recency | 0 |
| Author | 0 |
| **Total** | **50 + 0 = 50** |

**Badges:** ⚠️ Low Authority

## Trusted Source Lists

### Academic Domains
```
.edu, .gov, .ac.uk, .edu.au, .edu.cn
arxiv.org, scholar.google.com, pubmed.ncbi.nlm.nih.gov
nature.com, science.org, ieee.org, acm.org
```

### Trusted News
```
nytimes.com, washingtonpost.com, bbc.com, bbc.co.uk
reuters.com, apnews.com, theguardian.com, economist.com
wsj.com, ft.com, bloomberg.com, npr.org, pbs.org
```

### Tech Authority Sites
```
github.com, stackoverflow.com, developer.mozilla.org
docs.python.org, reactjs.org, nodejs.org, kubernetes.io
aws.amazon.com, cloud.google.com, azure.microsoft.com
hbr.org, mitsloan.mit.edu, ycombinator.com
```

## Technical Details

| Component | Implementation |
|-----------|----------------|
| URL Parsing | Python `urlparse` |
| Domain Extraction | Remove www. prefix |
| Link Detection | Regex pattern matching |
| Word Counting | Simple split() |
| Score Clamping | min(100, max(0, score)) |

## Limitations

- **Publication date** requires metadata extraction (not always available)
- **Source lists** are manually curated (new sites may not be rated)
- **Citation counting** is heuristic (may count irrelevant links)
- **Author detection** is basic (doesn't verify author credentials)

## Future Enhancements

- Fact-checking integration
- Author verification against known experts
- Cross-reference with other saved bookmarks on same topic
- Community-sourced source ratings
