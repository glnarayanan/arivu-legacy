# AI Summarization

> **One-liner:** Instantly understand any saved article without reading the whole thing.

## What Is It?

When you save a bookmark, Arivu's AI reads the entire content and generates:

1. **One-sentence summary** — The core idea in under 20 words
2. **Key points** — 3-5 bullet points of the main takeaways
3. **Suggested tags** — Auto-generated labels for organization
4. **Actionability** — Is this reference material or an action item?

## Why It Matters

**The Information Overload Problem:**
- You save 20 articles per week
- Each takes 5-10 minutes to read
- You can't possibly read everything
- Most bookmarks stay unread forever

**The Solution:**
- AI reads everything for you in seconds
- You get the gist instantly
- Decide what's worth your full attention
- Never lose important insights

## How It Works

### Step 1: Content Fetching

When you save a URL, Arivu immediately fetches:
- Page title
- Meta description
- Full text content (stripped of ads, navigation, etc.)
- Favicon and thumbnail

### Step 2: AI Processing

The text content is sent to **Gemini 2.5 Flash** with a structured prompt:

```
Analyze this content and provide:
1. One-sentence summary (max 20 words, capture the core idea)
2. Key points (3-5 bullet points, most important takeaways)
3. Suggested tags (3-7 relevant labels for categorization)
4. Content type (article, tutorial, reference, news, opinion)
5. Actionability (none, low, medium, high)
```

### Step 3: Background Processing

This happens in the background so saving is instant:

```
User clicks "Save"
     │
     ▼
┌─────────────────────┐
│ Bookmark created    │ ← Returns immediately
│ Status: "pending"   │
└─────────────────────┘
     │
     ▼ (Background)
┌─────────────────────┐
│ Fetch page content  │
│ Generate AI summary │
│ Extract entities    │
│ Create embedding    │
│ Status: "completed" │
└─────────────────────┘
```

## What the AI Generates

### One-Sentence Summary
A single sentence that captures the essence.

**Example content:** A 2000-word article about React Server Components

**One-sentence summary:** "React Server Components let you run components on the server, reducing client-side JavaScript and improving performance."

### Key Points
The 3-5 most important takeaways.

**Example:**
- Server Components render on the server, not in the browser
- They can directly access databases and file systems
- Client Components handle interactivity and state
- Reduces JavaScript bundle size significantly
- Requires React 18+ and a compatible framework

### Suggested Tags
Auto-generated labels for categorization.

**Example:** `react`, `web-development`, `performance`, `server-side-rendering`

### Content Type
What kind of content is this?

| Type | Description |
|------|-------------|
| article | General informative content |
| tutorial | Step-by-step guide |
| reference | Documentation, API reference |
| news | Current events, announcements |
| opinion | Editorial, thought piece |
| research | Academic, data-driven |

### Actionability Score
Should you act on this or just file it away?

| Level | Meaning | Example |
|-------|---------|---------|
| None | Pure reference | API documentation |
| Low | Informational | Industry news |
| Medium | Consider applying | Best practices article |
| High | Take action now | Security vulnerability alert |

## Key Functions Explained

### `generate_ai_summaries(text_content, bookmark_id)`
Main function that orchestrates AI summary generation.

**Process:**
1. Check if content is long enough (minimum 100 characters)
2. Rate-limit API calls to avoid quota issues
3. Send to Gemini with structured prompt
4. Parse JSON response
5. Store in `ai_summaries` collection
6. Update bookmark status

### `process_bookmark_content(bookmark_id, url)`
Background task that handles the full pipeline:
1. Fetch webpage content
2. Calculate reading time
3. Generate AI summaries
4. Generate embedding
5. Extract entities
6. Update bookmark with all data

## Rate Limiting

To avoid API quota issues, Arivu uses a rate limiter:

```python
gemini_rate_limiter.acquire(estimated_tokens=800)
```

This ensures:
- Bulk imports don't overwhelm the API
- Costs stay predictable
- All bookmarks eventually get processed

## None Safety

AI responses can be unpredictable. Every response is checked:

```python
response = model.generate_content(content)
summary = response.text if response and response.text else "Summary unavailable"
```

If AI fails, the bookmark still saves — it just won't have AI enhancements.

## Real-World Example

**You save:** https://blog.example.com/kubernetes-cost-optimization

**AI generates:**

| Field | Value |
|-------|-------|
| One-sentence | "Reduce Kubernetes costs by 40% using spot instances, right-sizing, and autoscaling policies." |
| Key points | • Use spot/preemptible instances for non-critical workloads<br>• Right-size pods based on actual usage metrics<br>• Implement cluster autoscaler for demand-based scaling<br>• Set resource requests and limits properly<br>• Consider multi-tenancy for better utilization |
| Tags | `kubernetes`, `devops`, `cloud-costs`, `optimization`, `infrastructure` |
| Type | tutorial |
| Actionability | high |

**Reading time calculated:** 8 minutes (based on 1,600 words ÷ 200 wpm)

## Technical Details

| Component | Technology | Purpose |
|-----------|------------|---------|
| AI Model | Gemini 2.5 Flash | Fast, cost-effective summarization |
| Content Limit | First 10,000 chars | Stay within token limits |
| Rate Limiter | Token bucket | Prevent API quota exhaustion |
| Storage | MongoDB `ai_summaries` | Separate collection for summaries |
| Background Processing | FastAPI BackgroundTasks | Non-blocking save experience |

## Data Model

```json
{
  "bookmark_id": "abc123",
  "one_sentence": "Summary here...",
  "key_points": ["Point 1", "Point 2", "Point 3"],
  "suggested_tags": ["tag1", "tag2"],
  "content_type": "article",
  "actionability": "medium",
  "processing_status": "completed",
  "created_at": "2024-01-15T10:30:00Z"
}
```

## Processing Status

| Status | Meaning |
|--------|---------|
| pending | Bookmark saved, waiting for processing |
| processing | AI is generating summaries |
| completed | All summaries generated successfully |
| failed | AI processing failed (rare) |
