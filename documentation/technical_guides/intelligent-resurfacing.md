# Intelligent Resurfacing

> **One-liner:** Never forget valuable bookmarks — Arivu reminds you of forgotten content at the perfect time.

## What Is It?

Intelligent Resurfacing proactively surfaces bookmarks you haven't visited in a while but might find valuable. It's like having a personal librarian who says:

> "Hey, you saved this great article 30 days ago but never read it. Today seems like a good day to revisit it."

## Why It Matters

**The Bookmark Graveyard Problem:**
- You save articles with good intentions
- They disappear into your collection
- You never look at them again
- Your valuable curation goes to waste

**The Solution:**
- Smart scoring identifies forgotten-but-valuable content
- Resurfaces at optimal review intervals (spaced repetition)
- Prioritizes based on past engagement and content quality

## How the Scoring Algorithm Works

Every bookmark gets a **resurfacing score** (0-50 points) based on five factors:

### Factor 1: Age Score (0-10 points)

How long since you last accessed this bookmark?

| Days Since Access | Score | Reason |
|-------------------|-------|--------|
| 0-6 days | 0 | Too recent — you remember it |
| 7-90 days | days/10 | Sweet spot for rediscovery |
| 90+ days | 10 (max) | Definitely forgotten |

**Example:** 30 days since access → 3 points

### Factor 2: Engagement Score (0-10 points)

How much have you interacted with this bookmark before?

```
Score = min(view_count × 2, 10)
```

| Views | Score | Meaning |
|-------|-------|---------|
| 0 | 0 | Never opened |
| 1-2 | 2-4 | Moderate interest |
| 3-4 | 6-8 | High interest |
| 5+ | 10 | You found this very valuable |

**Why it matters:** If you've viewed something multiple times, it's probably worth revisiting.

### Factor 3: Content Quality Score (0-5 points)

Does this bookmark have rich AI-generated metadata?

| Has Summary? | Has Tags? | Score |
|--------------|-----------|-------|
| Yes | Yes | 5 |
| Yes | No | 3 |
| No | Yes | 2 |
| No | No | 0 |

**Why it matters:** Well-summarized content is easier to resurface meaningfully.

### Factor 4: Reading Time Score (0-9 points)

Shorter articles are easier to commit to.

```
Score = 10 - reading_time (if reading_time ≤ 10 min)
```

| Reading Time | Score | Reason |
|--------------|-------|--------|
| 1 min | 9 | Quick read, easy commitment |
| 5 min | 5 | Medium commitment |
| 10 min | 0 | Longer commitment |
| 10+ min | 0 | No bonus for long reads |

### Factor 5: Spaced Repetition Boost (0-15 points)

Inspired by the Leitner System used for flashcard learning.

**Optimal review intervals:** 1, 3, 7, 14, 30 days

| Days Since Access | Score | Description |
|-------------------|-------|-------------|
| Exactly 1, 3, 7, 14, or 30 | 15 | Perfect timing! |
| Within 1 day of an interval | 10 | Close to optimal |
| Other | 0 | Not a review day |

**Why spaced repetition?** Memory research shows we retain information better when reviewed at increasing intervals.

## The Reason Generator

Each surfaced bookmark gets a human-readable reason explaining why it appeared:

**Primary reasons (based on top scoring factor):**
- "Review from yesterday" (1-day interval)
- "Weekly review" (7-day interval)
- "Monthly review" (30-day interval)
- "Not opened in 45 days" (age factor)

**Secondary context:**
- "You've found this valuable (5 views)"
- "Quick 3 min read"

**Combined example:**
> "Weekly review • Quick 2 min read"

## Key Functions Explained

### `calculate_resurfacing_score(bookmark, ai_summary)`
Calculates the total score and breakdown for one bookmark.

**Returns:**
```python
(total_score, {
  "age": 5.0,
  "engagement": 4.0,
  "quality": 5.0,
  "reading_time": 7.0,
  "spaced_repetition": 15.0,
  "total": 36.0
})
```

### `should_resurface(bookmark)`
Checks if a bookmark is eligible for resurfacing.

**Excluded:**
- Archived from resurfacing
- Currently snoozed
- Accessed within the last 24 hours
- No title (incomplete bookmarks)

### `get_resurfacing_reason(bookmark, breakdown, days_since)`
Generates the human-readable reason string.

### `get_resurfacing_suggestions(limit=5)`
API endpoint that returns top N resurfacing candidates.

## User Controls

### Snooze
Don't show this bookmark for N days (1-90).

```
POST /api/resurfacing/{bookmark_id}/snooze
Body: { "days": 7 }
```

**Use case:** "I saw this but not ready to read it yet"

### Archive
Never show this bookmark in resurfacing again.

```
POST /api/resurfacing/{bookmark_id}/archive
```

**Use case:** "This is outdated/irrelevant now"

### Unarchive
Bring a bookmark back to resurfacing.

```
POST /api/resurfacing/{bookmark_id}/unarchive
```

## Memory Jogger Feature

A special variant that shows ONE featured bookmark per day on the dashboard.

**How it selects:**
1. Get bookmarks not accessed in 7+ days
2. Exclude snoozed and archived
3. Prioritize bookmarks with AI summaries
4. Prioritize bookmarks connected to recently saved content
5. Return the highest-scoring candidate

**Connection bonus:** If a forgotten bookmark is semantically similar to something you saved in the last 7 days, it gets prioritized. This creates timely, relevant rediscovery.

## Real-World Example

**Your bookmark:** "Advanced Git Branching Strategies"
- Saved 14 days ago
- You viewed it twice before
- Has AI summary and tags
- 4-minute read

**Scoring breakdown:**
| Factor | Calculation | Score |
|--------|-------------|-------|
| Age | 14 days → 14/10 capped at 10 | 1.4 |
| Engagement | 2 views × 2 | 4 |
| Quality | Has summary + tags | 5 |
| Reading Time | 10 - 4 | 6 |
| Spaced Repetition | 14 is in [1,3,7,14,30] | 15 |
| **Total** | | **31.4** |

**Reason shown:** "Optimal review timing (14 days) • Quick 4 min read"

## Technical Architecture

```
┌─────────────────────────────────────────────┐
│              Resurfacing Engine             │
├─────────────────────────────────────────────┤
│                                             │
│  1. Fetch user's bookmarks (max 500)        │
│  2. Filter by should_resurface()            │
│  3. Score each with calculate_score()       │
│  4. Sort by score descending                │
│  5. Return top N with reasons               │
│                                             │
└─────────────────────────────────────────────┘
```

## Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| Max bookmarks fetched | 500 | Performance cap |
| Minimum age | 1 day | Don't resurface recently viewed |
| Spaced intervals | [1, 3, 7, 14, 30] | Optimal review days |
| Max snooze | 90 days | Longest possible snooze |
