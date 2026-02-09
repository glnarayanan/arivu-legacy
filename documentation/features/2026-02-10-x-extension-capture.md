# X Extension-Based Tweet Capture — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the expensive X API integration ($0.005/bookmark) with free, client-side tweet capture via the browser extension.

**Architecture:** The extension injects a content script on x.com/twitter.com that scrapes tweet data from the DOM when the user clicks the extension or uses a context menu. The scraped data (text, author, metrics, media) is sent to the existing `/bookmarks` endpoint with enriched fields. All server-side X OAuth, token management, and sync machinery is removed.

**Tech Stack:** Chrome Extension (Manifest V3), DOM scraping, existing FastAPI backend, existing React frontend.

---

## Summary of Changes

| Layer | Add | Remove |
|---|---|---|
| Extension `manifest.json` | `host_permissions` for x.com/twitter.com, `contextMenus` permission | — |
| Extension `x-content.js` (new) | Content script for x.com: scrapes tweet DOM on demand | — |
| Extension `background.js` | Context menu "Save tweet to Arivu", message relay | — |
| Extension `popup.js` / `popup.html` | Tweet preview UI when on x.com (shows scraped text, author) | — |
| Backend `bookmark.py` model | `BookmarkCreate` accepts optional tweet metadata fields | — |
| Backend `bookmarks.py` router | `create_bookmark` stores tweet metadata when provided | — |
| Backend `server.py` | — | ~600 lines: OAuth, token refresh, x_sync, x_api_request, x_connect, x_callback, x_disconnect, x_status, x_enabled, process_x_bookmarks_batch, build_x_oauth_url, map_x_sync_error_status, require_x_enabled, create_x_indexes |
| Frontend `ConnectionsSection.jsx` | — | Entire component (or gut X-specific parts) |
| Frontend `BookmarkCard.jsx` | — | No change (still renders `source === 'x'` bookmarks) |
| Config / env | — | `X_CLIENT_ID`, `X_CLIENT_SECRET`, `X_REDIRECT_URI`, `X_INTEGRATION_ENABLED`, `X_MAX_BOOKMARKS`, `X_MAX_BOOKMARK_PAGES`, `X_ENCRYPTION_KEY` |

---

## Task 1: Create the x.com content script (`x-content.js`)

This is the core of the new approach — a content script that runs on x.com and can scrape tweet data from the visible DOM.

**Files:**
- Create: `extension/x-content.js`

**Step 1: Create the tweet scraping content script**

```js
// x-content.js — Runs on x.com/twitter.com pages
// Scrapes tweet data from the DOM when requested by popup or background script

function scrapeTweetFromDOM() {
  // Strategy: find the focused/primary tweet article on the page.
  // On a tweet detail page (x.com/user/status/123), the primary tweet
  // is the first article[data-testid="tweet"] in the main column.
  // On the timeline, we grab the tweet closest to viewport center.

  const articles = document.querySelectorAll('article[data-testid="tweet"]');
  if (!articles.length) return null;

  // If URL is a tweet permalink, grab the first (primary) tweet
  const isTweetPage = /\/status\/\d+/.test(window.location.pathname);
  const article = isTweetPage ? articles[0] : getMostVisibleArticle(articles);
  if (!article) return null;

  return extractTweetData(article);
}

function getMostVisibleArticle(articles) {
  const viewportCenter = window.innerHeight / 2;
  let closest = null;
  let closestDistance = Infinity;

  for (const article of articles) {
    const rect = article.getBoundingClientRect();
    const articleCenter = rect.top + rect.height / 2;
    const distance = Math.abs(articleCenter - viewportCenter);
    if (distance < closestDistance) {
      closestDistance = distance;
      closest = article;
    }
  }
  return closest;
}

function extractTweetData(article) {
  // Author info
  const userLinks = article.querySelectorAll('a[role="link"]');
  let authorUsername = '';
  let authorName = '';
  for (const link of userLinks) {
    const href = link.getAttribute('href') || '';
    if (href.match(/^\/[A-Za-z0-9_]+$/) && !href.startsWith('/i/')) {
      authorUsername = href.replace('/', '');
      const nameEl = link.querySelector('span');
      if (nameEl) authorName = nameEl.textContent.trim();
      break;
    }
  }

  // Tweet text
  const tweetTextEl = article.querySelector('[data-testid="tweetText"]');
  const tweetText = tweetTextEl ? tweetTextEl.innerText.trim() : '';

  // Timestamp & tweet ID
  const timeEl = article.querySelector('time');
  const createdAt = timeEl ? timeEl.getAttribute('datetime') : null;
  const timeLink = timeEl ? timeEl.closest('a') : null;
  const tweetHref = timeLink ? timeLink.getAttribute('href') : '';
  const tweetIdMatch = tweetHref.match(/\/status\/(\d+)/);
  const tweetId = tweetIdMatch ? tweetIdMatch[1] : null;

  // Metrics
  const metrics = {};
  const metricGroups = article.querySelectorAll('[role="group"] button');
  const metricNames = ['reply_count', 'retweet_count', 'like_count', 'view_count'];
  metricGroups.forEach((btn, i) => {
    if (i < metricNames.length) {
      const ariaLabel = btn.getAttribute('aria-label') || '';
      const numMatch = ariaLabel.match(/(\d[\d,]*)/);
      metrics[metricNames[i]] = numMatch ? parseInt(numMatch[1].replace(/,/g, ''), 10) : 0;
    }
  });

  // Media (images)
  const mediaUrls = [];
  const images = article.querySelectorAll('[data-testid="tweetPhoto"] img');
  images.forEach(img => {
    const src = img.getAttribute('src');
    if (src && !src.includes('emoji') && !src.includes('profile_images')) {
      mediaUrls.push(src);
    }
  });

  // External links in tweet
  const externalUrls = [];
  const cardLink = article.querySelector('[data-testid="card.wrapper"] a');
  if (cardLink) {
    const href = cardLink.getAttribute('href');
    if (href && !href.includes('x.com') && !href.includes('twitter.com')) {
      externalUrls.push(href);
    }
  }

  const tweetUrl = tweetId && authorUsername
    ? `https://x.com/${authorUsername}/status/${tweetId}`
    : window.location.href;

  return {
    tweet_id: tweetId,
    tweet_text: tweetText,
    tweet_url: tweetUrl,
    author_username: authorUsername,
    author_name: authorName,
    created_at: createdAt,
    metrics: metrics,
    media_urls: mediaUrls,
    external_urls: externalUrls,
  };
}

// Listen for scrape requests from popup or background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'scrapeTweet') {
    const data = scrapeTweetFromDOM();
    sendResponse({ success: !!data, tweet: data });
  }
  return true;
});
```

**Step 2: Commit**

```bash
git add extension/x-content.js
git commit -m "feat(extension): add x.com tweet scraping content script"
```

---

## Task 2: Update extension manifest

Register the new content script for x.com/twitter.com and add the `contextMenus` permission.

**Files:**
- Modify: `extension/manifest.json`

**Step 1: Update manifest.json**

Add `https://x.com/*` and `https://twitter.com/*` to `host_permissions`, register `x-content.js` as a content script for those domains, and add `contextMenus` permission:

```json
{
  "manifest_version": 3,
  "name": "Arivu - AI Bookmarks",
  "version": "1.2.0",
  "description": "Save and organize web pages with AI-powered summaries",
  "permissions": [
    "activeTab",
    "storage",
    "contextMenus"
  ],
  "host_permissions": [
    "https://arivu.app/*",
    "http://localhost:8001/*",
    "https://x.com/*",
    "https://twitter.com/*"
  ],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icon16.png",
      "48": "icon48.png",
      "128": "icon128.png"
    }
  },
  "icons": {
    "16": "icon16.png",
    "48": "icon48.png",
    "128": "icon128.png"
  },
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["https://arivu.app/*", "http://localhost/*"],
      "js": ["content.js"],
      "run_at": "document_idle"
    },
    {
      "matches": ["https://x.com/*", "https://twitter.com/*"],
      "js": ["x-content.js"],
      "run_at": "document_idle"
    }
  ],
  "commands": {
    "save-bookmark": {
      "suggested_key": {
        "default": "Ctrl+Shift+S",
        "mac": "Command+Shift+S"
      },
      "description": "Save current page to Arivu"
    }
  }
}
```

**Step 2: Commit**

```bash
git add extension/manifest.json
git commit -m "feat(extension): register x.com content script and contextMenus permission"
```

---

## Task 3: Update background.js — context menu + message relay

Add a right-click context menu on x.com pages: "Save tweet to Arivu."

**Files:**
- Modify: `extension/background.js`

**Step 1: Update background.js**

```js
// Context menu for saving tweets
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'save-tweet-to-arivu',
    title: 'Save tweet to Arivu',
    contexts: ['page', 'link'],
    documentUrlPatterns: ['https://x.com/*', 'https://twitter.com/*'],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'save-tweet-to-arivu' && tab?.id) {
    // Ask content script to scrape the tweet
    chrome.tabs.sendMessage(tab.id, { action: 'scrapeTweet' }, (response) => {
      if (response?.success && response.tweet) {
        // Store scraped tweet data so popup can read it
        chrome.storage.session.set({ pendingTweet: response.tweet });
        // Open popup for user to confirm/save
        chrome.action.openPopup();
      }
    });
  }
});

chrome.commands.onCommand.addListener((command) => {
  if (command === 'save-bookmark') {
    chrome.action.openPopup();
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'saveTokens') {
    chrome.storage.session.set({
      accessToken: request.accessToken,
      refreshToken: request.refreshToken,
    });
    sendResponse({ success: true });
  }
  return true;
});
```

**Step 2: Commit**

```bash
git add extension/background.js
git commit -m "feat(extension): add right-click 'Save tweet to Arivu' context menu"
```

---

## Task 4: Update popup.js and popup.html — tweet-aware save flow

When the user is on x.com, the popup should show a tweet preview instead of a plain URL field.

**Files:**
- Modify: `extension/popup.js`
- Modify: `extension/popup.html`

**Step 1: Add tweet preview section to popup.html**

Add a `#tweetPreview` section after `#saveForm` that shows the scraped tweet text and author, visible only when saving from x.com:

```html
<!-- Add inside #saveForm, before the submit button -->
<div id="tweetPreview" style="display:none;">
  <div class="form-group">
    <label>Tweet</label>
    <div id="tweetContent" style="
      padding: 10px 12px;
      border: 2px solid #0F0F0F;
      background: white;
      font-size: 14px;
      font-family: 'DM Sans', sans-serif;
      max-height: 120px;
      overflow-y: auto;
      white-space: pre-wrap;
    "></div>
  </div>
  <div class="form-group">
    <label>Author</label>
    <input type="text" id="tweetAuthor" readonly>
  </div>
</div>
```

**Step 2: Update popup.js to detect x.com and scrape**

In the `init()` function, after getting the current tab, detect if the user is on x.com. If so, message the content script to scrape tweet data. Also check `pendingTweet` from context menu flow. Update the save handler to include tweet metadata in the POST body.

Key changes to `popup.js`:

```js
// In init(), after getting currentTab:
const isXPage = currentTab.url?.match(/https:\/\/(x\.com|twitter\.com)/);

if (isXPage) {
  // Check if there's a pending tweet from context menu
  const stored = await chrome.storage.session.get(['pendingTweet']);
  let tweetData = stored.pendingTweet;

  if (!tweetData) {
    // Ask content script to scrape
    tweetData = await new Promise((resolve) => {
      chrome.tabs.sendMessage(currentTab.id, { action: 'scrapeTweet' }, (response) => {
        resolve(response?.success ? response.tweet : null);
      });
    });
  }

  if (tweetData) {
    // Clear pending tweet
    await chrome.storage.session.remove(['pendingTweet']);

    // Show tweet preview
    document.getElementById('tweetPreview').style.display = 'block';
    document.getElementById('tweetContent').textContent = tweetData.tweet_text;
    document.getElementById('tweetAuthor').value =
      `@${tweetData.author_username}` + (tweetData.author_name ? ` (${tweetData.author_name})` : '');
    document.getElementById('url').value = tweetData.tweet_url || currentTab.url;
    document.getElementById('title').value = tweetData.tweet_text?.substring(0, 100) || currentTab.title;

    // Store for save handler
    window._tweetData = tweetData;
  }
}

// In the submit handler, update the POST body:
const body = { url, collection_id: collectionId };

if (window._tweetData) {
  body.source = 'x';
  body.x_tweet_id = window._tweetData.tweet_id;
  body.x_author_username = window._tweetData.author_username;
  body.x_author_name = window._tweetData.author_name;
  body.x_tweet_url = window._tweetData.tweet_url;
  body.x_metrics = window._tweetData.metrics;
  body.text_content = window._tweetData.tweet_text;
}
```

**Step 3: Commit**

```bash
git add extension/popup.js extension/popup.html
git commit -m "feat(extension): tweet-aware popup with preview and metadata"
```

---

## Task 5: Update backend `BookmarkCreate` model to accept tweet metadata

**Files:**
- Modify: `backend/app/models/bookmark.py`

**Step 1: Add optional tweet fields to BookmarkCreate**

```python
class BookmarkCreate(BaseModel):
    url: str
    collection_id: Optional[str] = None
    # Extension-captured tweet metadata (optional)
    source: Optional[str] = None  # "x" when saving a tweet
    x_tweet_id: Optional[str] = None
    x_author_username: Optional[str] = None
    x_author_name: Optional[str] = None
    x_tweet_url: Optional[str] = None
    x_metrics: Optional[Dict] = None
    text_content: Optional[str] = None

    @validator("url")
    def validate_url(cls, v):
        # ... existing validation unchanged ...
```

**Step 2: Commit**

```bash
git add backend/app/models/bookmark.py
git commit -m "feat(backend): accept tweet metadata in BookmarkCreate model"
```

---

## Task 6: Update `create_bookmark` endpoint to store tweet metadata

**Files:**
- Modify: `backend/app/routers/bookmarks.py` (lines ~85-130)

**Step 1: Update create_bookmark to use tweet fields when provided**

After building the `bookmark` dict (line ~97-113), add the tweet fields if the source is `"x"`:

```python
bookmark = {
    "id": str(uuid.uuid4()),
    "user_id": current_user["id"],
    "url": bookmark_data.url,
    "title": parsed_url.netloc or "Loading...",
    # ... existing fields ...
    "version": 1,
}

# If this is a tweet saved via extension, add tweet metadata
if bookmark_data.source == "x":
    bookmark["source"] = "x"
    bookmark["x_tweet_id"] = bookmark_data.x_tweet_id
    bookmark["x_author_username"] = bookmark_data.x_author_username
    bookmark["x_author_name"] = bookmark_data.x_author_name
    bookmark["x_tweet_url"] = bookmark_data.x_tweet_url
    bookmark["x_metrics"] = bookmark_data.x_metrics
    if bookmark_data.text_content:
        bookmark["text_content"] = bookmark_data.text_content
        bookmark["title"] = bookmark_data.text_content[:100] + (
            "..." if len(bookmark_data.text_content) > 100 else ""
        )
        bookmark["description"] = bookmark_data.text_content
```

**Step 2: Commit**

```bash
git add backend/app/routers/bookmarks.py
git commit -m "feat(backend): store tweet metadata from extension capture"
```

---

## Task 7: Remove server-side X API integration from `server.py`

This is the big cleanup — remove ~600 lines of OAuth, token management, sync, and X API code.

**Files:**
- Modify: `backend/server.py`

**Step 1: Remove X API functions and endpoints**

Delete the following blocks (keep the `X_INTEGRATION_ENABLED` flag for now — it can gate whether tweet metadata is accepted):

| What | Lines (approx) |
|---|---|
| `build_x_oauth_url()` | 234-251 |
| `map_x_sync_error_status()` | 254-260 |
| `refresh_x_token()` | 663-706 |
| `x_api_request()` | 709-750 |
| `require_x_enabled()` | 753-755 |
| `x_enabled` endpoint | 758-761 |
| `x_connect` endpoint | 764-801 |
| `x_callback` endpoint | 803-902 |
| `x_disconnect` endpoint | 904-928 |
| `x_status` endpoint | 930-952 |
| `x_sync` endpoint | 954-1197 |
| `process_x_bookmarks_batch()` | 1200-1279 |
| `create_x_indexes()` | 1833+ |
| X config vars | 158-173 (`X_INTEGRATION_ENABLED`, `X_CLIENT_ID`, `X_CLIENT_SECRET`, etc.) |

Also remove related imports: `httpx` (if only used for X), `encrypt_token`/`decrypt_token` (if only used for X tokens).

**Step 2: Remove X env vars from config**

Remove from `.env.example`: `X_CLIENT_ID`, `X_CLIENT_SECRET`, `X_REDIRECT_URI`, `X_ENCRYPTION_KEY`, `X_MAX_BOOKMARKS`, `X_MAX_BOOKMARK_PAGES`.

Remove from `docker-compose.yml` and `docker-compose.prod.yml`: X-related environment variable mappings.

**Step 3: Commit**

```bash
git add backend/server.py .env.example docker-compose.yml docker-compose.prod.yml
git commit -m "refactor(backend): remove X API OAuth/sync machinery (~600 lines)"
```

---

## Task 8: Update frontend — remove X connection UI from Settings

**Files:**
- Modify: `frontend/src/components/settings/ConnectionsSection.jsx`

**Step 1: Replace the OAuth connect/sync UI**

Replace the entire OAuth connect/disconnect/sync flow with a simple informational card that says:

> "Save tweets directly using the Arivu browser extension. Click the extension icon or right-click while viewing any tweet."

Remove: all `axiosInstance` calls to `/auth/x/*`, OAuth callback handling, sync polling, connect/disconnect buttons.

Keep: the `XLogo` component and the card layout structure.

**Step 2: Commit**

```bash
git add frontend/src/components/settings/ConnectionsSection.jsx
git commit -m "refactor(frontend): replace X OAuth UI with extension instructions"
```

---

## Task 9: Verify and test end-to-end

**Files:**
- No new files

**Step 1: Run backend tests**

```bash
cd backend && python backend_test.py
```

Expected: All existing tests pass (X sync tests will be gone).

**Step 2: Load the extension in Chrome**

1. Go to `chrome://extensions/`, enable Developer mode
2. Load unpacked from `extension/`
3. Navigate to a tweet on x.com
4. Click the Arivu extension icon
5. Verify: tweet text and author appear in the popup preview
6. Click "Save Bookmark"
7. Verify: bookmark appears in Arivu dashboard with `source: "x"`, tweet text, author

**Step 3: Test context menu**

1. Right-click on a tweet page
2. Click "Save tweet to Arivu"
3. Verify: popup opens with tweet data pre-filled

**Step 4: Test non-X pages still work**

1. Navigate to any non-X page
2. Click extension → should show normal URL/title save flow (unchanged)

**Step 5: Commit**

```bash
git add -A
git commit -m "test: verify extension-based tweet capture end-to-end"
```

---

## Out of Scope (Future)

- **Batch import from x.com/i/bookmarks page:** A "Select All" overlay on the X bookmarks page that lets users pick multiple tweets. Content script scrolls and scrapes. This is fragile and should be a separate effort.
- **Twitter data export import:** Accept `bookmarks.js` from X data archive. Low priority.
- **MongoDB `x_connections` collection cleanup:** Migration to drop the collection for existing users. Not urgent — it just sits there unused.
