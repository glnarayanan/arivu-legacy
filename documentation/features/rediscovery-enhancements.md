# Rediscovery Enhancements Implementation Plan

**Version:** 1.0  
**Created:** January 15, 2026  
**Purpose:** Detailed implementation plan for three engagement-focused features to help users rediscover and engage with their saved knowledge.

---

## Overview

These three features work together to create a cohesive "second brain" experience:

1. **Memory Jogger** — Daily prominent single bookmark reminder
2. **Weekly Knowledge Digest** — AI-generated weekly insights report
3. **Connect the Dots** — Show connections immediately when saving

---

## Feature 1: Memory Jogger

### Concept
Replace the current 3-card resurfacing section with a single, prominent "Memory of the Day" at the top of the dashboard. This is opinionated — the app decides what you should revisit today.

### Backend Implementation

#### New Endpoint: `GET /api/memory-jogger`

**File:** `backend/server.py`

```python
@api_router.get("/memory-jogger")
async def get_memory_jogger(current_user: dict = Depends(get_current_user)):
    """
    Returns a single featured bookmark for today's memory jogger.
    
    Selection Algorithm:
    1. Exclude bookmarks accessed in last 7 days
    2. Exclude snoozed bookmarks (check snooze_until field)
    3. Exclude archived from resurfacing (resurfacing_archived = True)
    4. Score remaining bookmarks:
       - +30 points: Has connections to bookmarks saved in last 7 days
       - +20 points: Not accessed in 30+ days
       - +10 points: Has AI summary completed
       - +5 points: Has 3+ related bookmarks
       - Random factor: 0-15 points (for variety)
    5. Return highest scoring bookmark with context
    """
```

**Response Schema:**
```json
{
  "bookmark": {
    "id": "uuid",
    "title": "string",
    "url": "string",
    "domain": "string",
    "favicon": "string",
    "thumbnail": "string",
    "description": "string",
    "created_at": "datetime",
    "last_accessed": "datetime",
    "ai_summary": {
      "one_sentence": "string",
      "suggested_tags": ["string"]
    }
  },
  "context": {
    "days_since_saved": 47,
    "days_since_accessed": 32,
    "connection_count": 3,
    "connected_topics": ["AI", "productivity"],
    "reason": "Connects to 3 bookmarks you saved this week about AI tools"
  },
  "has_memory": true
}
```

**If no eligible bookmark:**
```json
{
  "bookmark": null,
  "context": null,
  "has_memory": false,
  "message": "Save more bookmarks to unlock daily memories"
}
```

#### Database Considerations

Add to bookmark document (if not exists):
- `memory_jogger_shown_at`: datetime — Last time this was shown as memory jogger
- `memory_jogger_dismissed_at`: datetime — If user dismissed without engaging

#### Helper Function: Calculate Connections

```python
async def get_recent_connections(bookmark_id: str, user_id: str, days: int = 7) -> dict:
    """
    Find bookmarks saved in last N days that are semantically related.
    Uses existing embedding similarity logic.
    
    Returns:
    {
        "count": 3,
        "topics": ["AI", "productivity"],
        "bookmark_ids": ["id1", "id2", "id3"]
    }
    """
```

### Frontend Implementation

#### New Component: `MemoryJogger.jsx`

**File:** `frontend/src/components/MemoryJogger.jsx`

**Design Specs (Brutalist):**
- Full-width card at very top of dashboard (above all other content)
- 2px black border, offset shadow
- Background: Subtle gradient or accent tint to stand out
- Left section: Thumbnail/favicon + title + one-sentence summary
- Right section: Context ("47 days ago • Connects to 3 recent saves")
- Single prominent CTA: "REVISIT" (primary button)
- Secondary action: "NOT TODAY" (ghost button, snoozes for 24h)
- Collapse/minimize option for returning users

**State Management:**
```javascript
const [memoryJogger, setMemoryJogger] = useState(null);
const [memoryLoading, setMemoryLoading] = useState(true);
const [memoryDismissed, setMemoryDismissed] = useState(false);

// Check localStorage for today's dismissal
useEffect(() => {
  const dismissed = localStorage.getItem('memoryJoggerDismissed');
  if (dismissed === new Date().toDateString()) {
    setMemoryDismissed(true);
  }
}, []);
```

**Actions:**
- "Revisit" → Navigate to bookmark detail, track access with source='memory_jogger'
- "Not Today" → POST `/memory-jogger/dismiss`, set localStorage, hide for 24h
- Click anywhere → Same as "Revisit"

#### New Endpoint: `POST /api/memory-jogger/dismiss`

```python
@api_router.post("/memory-jogger/dismiss")
async def dismiss_memory_jogger(
    bookmark_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Dismiss today's memory jogger.
    Records dismissal for analytics and prevents re-showing today.
    """
```

### Dashboard Integration

**File:** `frontend/src/pages/DashboardPage.jsx`

```jsx
// Add to imports
import MemoryJogger from '../components/MemoryJogger';

// Add to state
const [memoryJogger, setMemoryJogger] = useState(null);

// Add to useEffect (fetch on mount)
const fetchMemoryJogger = async () => {
  try {
    const response = await axiosInstance.get('/memory-jogger');
    if (response.data.has_memory) {
      setMemoryJogger(response.data);
    }
  } catch (error) {
    console.error('Failed to fetch memory jogger:', error);
  }
};

// Render at TOP of main content (before filters, before resurfacing section)
{memoryJogger && !memoryDismissed && (
  <MemoryJogger
    data={memoryJogger}
    onRevisit={handleMemoryRevisit}
    onDismiss={handleMemoryDismiss}
  />
)}
```

### Remove/Modify Existing Resurfacing

**Option A:** Remove ResurfacingSection entirely (Memory Jogger replaces it)
**Option B:** Keep ResurfacingSection but collapse by default, show "See more suggestions"

**Recommendation:** Option A for simplicity. Memory Jogger is more opinionated.

---

## Feature 2: Weekly Knowledge Digest

### Concept
AI-generated weekly report showing patterns, connections, and forgotten gems. Available both in-app and via email.

### Backend Implementation

#### Database: New Collection `digests`

```python
digest_schema = {
    "id": "uuid",
    "user_id": "uuid",
    "type": "weekly",  # Future: "monthly", "quarterly"
    "period_start": "datetime",
    "period_end": "datetime",
    "generated_at": "datetime",
    "content": {
        "summary": "string",  # AI-generated overview
        "bookmarks_saved_count": 5,
        "patterns": [
            {
                "topic": "AI Tools",
                "bookmark_count": 3,
                "insight": "You're exploring AI productivity tools"
            }
        ],
        "forgotten_gems": [
            {
                "bookmark_id": "uuid",
                "title": "string",
                "saved_days_ago": 45,
                "connection_to_recent": "Relates to your new AI bookmarks"
            }
        ],
        "connections_discovered": [
            {
                "bookmark_ids": ["id1", "id2"],
                "connection_reason": "Both discuss productivity frameworks"
            }
        ],
        "reading_stats": {
            "total_reading_time_minutes": 45,
            "most_saved_domain": "medium.com",
            "read_percentage": 60
        }
    },
    "email_sent": false,
    "email_sent_at": null,
    "viewed_in_app": false,
    "viewed_at": null
}
```

#### Scheduled Job: Generate Weekly Digest

**File:** `backend/server.py` (or new `backend/jobs/digest_generator.py`)

```python
async def generate_weekly_digest(user_id: str) -> dict:
    """
    Generate weekly digest for a user.
    Called by scheduler every Sunday at 9 AM user's local time (or UTC).
    
    Steps:
    1. Fetch all bookmarks saved in last 7 days
    2. Fetch all bookmarks for pattern analysis
    3. Use Gemini to identify patterns and generate insights
    4. Find "forgotten gems" (30+ days, connects to recent saves)
    5. Calculate reading stats
    6. Store digest in database
    7. Queue email if user has email notifications enabled
    """
```

**AI Prompt for Pattern Analysis:**
```python
DIGEST_PROMPT = """
Analyze these bookmarks saved by a user this week and provide insights.

Bookmarks saved this week:
{recent_bookmarks_json}

User's existing bookmark topics:
{existing_topics}

Provide a JSON response with:
1. "summary": A 2-sentence overview of what they explored this week
2. "patterns": Array of topics/themes with counts and insights
3. "observation": One interesting observation about their knowledge collection

Keep the tone friendly and insightful, not robotic.
"""
```

#### Endpoints

**GET `/api/digest/latest`**
```python
@api_router.get("/digest/latest")
async def get_latest_digest(current_user: dict = Depends(get_current_user)):
    """
    Returns the most recent digest for the user.
    Marks as viewed_in_app if first time viewing.
    """
```

**GET `/api/digest/history`**
```python
@api_router.get("/digest/history")
async def get_digest_history(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Returns past digests for the user."""
```

**POST `/api/digest/generate`** (Manual trigger for testing)
```python
@api_router.post("/digest/generate")
async def trigger_digest_generation(current_user: dict = Depends(get_current_user)):
    """Manually generate a digest (useful for testing or on-demand)."""
```

#### Email Integration

**Option A: Use existing email service (if any)**
Check if there's already email infrastructure for password reset, etc.

**Option B: Add email service**
```python
# backend/services/email_service.py
import resend  # or sendgrid, mailgun, etc.

async def send_digest_email(user_email: str, digest: dict):
    """
    Send weekly digest email with brutalist HTML template.
    """
```

**Email Template Design:**
- Subject: "Your Weekly Knowledge Digest — Arivu"
- Brutalist design matching app aesthetic
- Sections: Summary, Patterns, Forgotten Gems, Stats
- CTA: "View Full Digest in Arivu"

#### Scheduler Setup

**Using APScheduler or similar:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', day_of_week='sun', hour=9)
async def weekly_digest_job():
    """Generate and send weekly digests for all users."""
    users = await db.users.find({"digest_enabled": True}).to_list(None)
    for user in users:
        await generate_weekly_digest(user["id"])
```

### Frontend Implementation

#### New Page: `DigestPage.jsx`

**File:** `frontend/src/pages/DigestPage.jsx`

**Route:** `/digest` (add to router)

**Design:**
- Full-page view of latest digest
- Sections matching digest content structure
- Each "forgotten gem" is clickable → navigates to bookmark
- Historical digests accessible via "Past Digests" button

**Components:**
```
DigestPage.jsx
├── DigestHeader (period, date generated)
├── DigestSummary (AI-generated overview)
├── DigestPatterns (topic cards with counts)
├── ForgottenGems (bookmark cards with "why it matters")
├── DigestStats (reading time, domains, read %)
└── PastDigestsModal (list of historical digests)
```

#### Sidebar Integration

**File:** `frontend/src/components/Sidebar.jsx`

Add new navigation item:
```jsx
<SidebarItem
  icon={<CalendarIcon />}
  label="WEEKLY DIGEST"
  to="/digest"
  badge={hasUnreadDigest ? "NEW" : null}
/>
```

#### User Settings: Digest Preferences

**File:** `frontend/src/components/settings/NotificationsSection.jsx` (new section)

```jsx
// Settings for digest
- Toggle: "Enable weekly digest" (default: on)
- Toggle: "Send digest via email" (default: on if email verified)
- Select: "Digest day" (Sunday, Monday, etc.)
```

**Backend:** Add to user document:
```python
{
  "digest_settings": {
    "enabled": True,
    "email_enabled": True,
    "day_of_week": "sunday"
  }
}
```

---

## Feature 3: Connect the Dots on Save

### Concept
When a user saves a new bookmark, immediately show them how it connects to their existing knowledge. Creates an "aha moment" and reinforces the value of the app.

### Backend Implementation

#### Modify Existing Endpoint: `POST /api/bookmarks`

**Current behavior:** Returns saved bookmark after inserting.

**New behavior:** Return saved bookmark + immediate connections.

```python
@api_router.post("/bookmarks")
async def create_bookmark(
    bookmark_data: BookmarkCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    # ... existing save logic ...
    
    # NEW: Find quick connections before AI processing completes
    quick_connections = await find_quick_connections(
        url=bookmark_data.url,
        title=extracted_title,
        user_id=current_user["id"],
        limit=5
    )
    
    # Queue full AI processing in background
    background_tasks.add_task(process_bookmark_ai, bookmark_id)
    
    return {
        "bookmark": saved_bookmark,
        "connections": quick_connections,
        "connections_count": len(quick_connections)
    }
```

#### New Helper: `find_quick_connections()`

```python
async def find_quick_connections(
    url: str,
    title: str,
    user_id: str,
    limit: int = 5
) -> list:
    """
    Find related bookmarks quickly (before embeddings are generated).
    
    Strategy (fast, no embedding needed):
    1. Domain match: Other bookmarks from same domain
    2. Title keyword overlap: TF-IDF or simple keyword matching
    3. Tag overlap: If URL patterns suggest topics
    
    Returns list of:
    {
        "id": "uuid",
        "title": "string",
        "domain": "string",
        "favicon": "string",
        "connection_type": "same_domain" | "similar_topic" | "keyword_match",
        "connection_reason": "Also from medium.com"
    }
    """
```

#### Enhanced Connections (Post-AI Processing)

After AI processing completes, update connections with semantic similarity:

```python
async def process_bookmark_ai(bookmark_id: str):
    # ... existing AI processing ...
    
    # After embedding is generated:
    semantic_connections = await find_semantic_connections(
        bookmark_id=bookmark_id,
        embedding=new_embedding,
        limit=5
    )
    
    # Store connections for later retrieval
    await db.bookmarks.update_one(
        {"id": bookmark_id},
        {"$set": {"cached_connections": semantic_connections}}
    )
```

### Frontend Implementation

#### New Component: `ConnectionsModal.jsx`

**File:** `frontend/src/components/ConnectionsModal.jsx`

**Triggered:** After successful bookmark save (in dialog or via extension)

**Design (Brutalist):**
```
┌─────────────────────────────────────────────────┐
│  ✓ BOOKMARK SAVED                               │
│                                                 │
│  "Article Title Here"                           │
│  medium.com • AI processing...                  │
│                                                 │
├─────────────────────────────────────────────────┤
│  CONNECTS TO YOUR KNOWLEDGE                     │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │ 📄 Related Article Title                │   │
│  │    same domain • saved 2 weeks ago      │   │
│  └─────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────┐   │
│  │ 📄 Another Related Article              │   │
│  │    similar topic • saved 1 month ago    │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  [ VIEW BOOKMARK ]        [ SAVE ANOTHER ]     │
└─────────────────────────────────────────────────┘
```

**States:**
- 0 connections: "This is your first bookmark about [domain]!"
- 1-5 connections: Show connection cards
- Loading: Skeleton cards while fetching

#### Dashboard Integration

**File:** `frontend/src/pages/DashboardPage.jsx`

```jsx
// Add state
const [showConnectionsModal, setShowConnectionsModal] = useState(false);
const [savedBookmarkConnections, setSavedBookmarkConnections] = useState(null);

// Modify handleAddBookmark
const handleAddBookmark = async (e) => {
  e.preventDefault();
  if (!newBookmarkUrl) return;

  setAddingBookmark(true);
  try {
    const response = await axiosInstance.post('/bookmarks', { url: newBookmarkUrl });
    
    // NEW: Show connections modal instead of just closing
    if (response.data.connections && response.data.connections.length > 0) {
      setSavedBookmarkConnections({
        bookmark: response.data.bookmark,
        connections: response.data.connections
      });
      setShowConnectionsModal(true);
    } else {
      toast.success('Bookmark saved! AI is processing...');
    }
    
    setNewBookmarkUrl('');
    setDialogOpen(false);
    setTimeout(() => fetchBookmarks(), 2000);
  } catch (error) {
    toast.error('Failed to save bookmark');
  } finally {
    setAddingBookmark(false);
  }
};

// Add modal
<ConnectionsModal
  open={showConnectionsModal}
  onOpenChange={setShowConnectionsModal}
  data={savedBookmarkConnections}
  onViewBookmark={(id) => navigate(`/bookmark/${id}`)}
/>
```

#### Browser Extension Integration

**File:** `extension/popup.js` (or equivalent)

After saving from extension:
1. Show success state
2. Fetch connections from API
3. Display mini-version of connections
4. "View in Arivu" button to see full connections

---

## Implementation Order

### Phase 1: Memory Jogger (Estimated: 4-6 hours)
1. Backend endpoint `/memory-jogger`
2. Scoring algorithm
3. Frontend component
4. Dashboard integration
5. Dismiss functionality
6. Remove/modify existing ResurfacingSection

### Phase 2: Connect the Dots (Estimated: 3-4 hours)
1. Modify POST `/bookmarks` response
2. Quick connections helper function
3. ConnectionsModal component
4. Dashboard integration
5. Test with various bookmark types

### Phase 3: Weekly Digest (Estimated: 6-8 hours)
1. Database schema for digests
2. Digest generation logic
3. AI prompt engineering
4. GET `/digest/latest` endpoint
5. DigestPage frontend
6. Sidebar integration
7. Scheduler setup
8. Email template and sending (if email service exists)
9. User settings for digest preferences

---

## Testing Checklist

### Memory Jogger
- [ ] Returns correct bookmark based on scoring
- [ ] Excludes recently accessed bookmarks
- [ ] Excludes snoozed bookmarks
- [ ] Handles users with < 5 bookmarks gracefully
- [ ] Dismiss persists for 24 hours
- [ ] Tracks access source correctly

### Connect the Dots
- [ ] Returns connections with saved bookmark
- [ ] Handles first bookmark (no connections) gracefully
- [ ] Domain matching works
- [ ] Keyword matching works
- [ ] Modal displays correctly
- [ ] Extension integration works

### Weekly Digest
- [ ] Generates correctly for users with bookmarks
- [ ] Handles users with no bookmarks this week
- [ ] AI patterns are sensible
- [ ] Forgotten gems are actually old and relevant
- [ ] Email sends correctly (if enabled)
- [ ] Scheduler runs on correct day
- [ ] In-app viewing marks as read

---

## Analytics Events to Track

```javascript
// Memory Jogger
"memory_jogger_shown"
"memory_jogger_clicked"
"memory_jogger_dismissed"

// Connect the Dots
"connections_shown" // with count
"connection_clicked"
"connections_modal_closed"

// Weekly Digest
"digest_generated"
"digest_viewed_in_app"
"digest_email_opened"
"digest_gem_clicked"
```

---

## Future Enhancements

1. **Memory Jogger:** Add "Why this?" explainer tooltip
2. **Connect the Dots:** Show connections on bookmark detail page too
3. **Weekly Digest:** Add monthly/quarterly digests
4. **All:** Push notifications (mobile/browser) for high-value resurfaces
