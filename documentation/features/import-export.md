# Import/Export

**Status:** ✅ Fully Implemented
**Implemented:** January 2026
**Frontend:** `/imports`
**API:** `/api/bookmarks/import`, `/api/bookmarks/export`, `/api/import-jobs/*`

---

## Overview

The Import/Export feature allows seamless migration of bookmarks from other services like Pocket, Raindrop.io, Chrome, Firefox, and generic bookmark managers. It also provides flexible export options for backing up or moving your Arivu bookmarks elsewhere.

---

## Supported Services

### Import Sources

#### 1. **Pocket**
- Format: HTML or JSON export
- Data imported: URLs, titles, tags, timestamps, read status
- Notes: Pocket archive includes read/unread status

#### 2. **Raindrop.io**
- Format: JSON export from Raindrop.io, plus generic CSV/plain URL imports through the same endpoint
- Data imported: URLs and titles
- Notes: The API accepts `X-Import-Source: raindrop` for Raindrop JSON and skips unsafe URLs before bookmark creation

#### 3. **Chrome Bookmarks**
- Format: HTML export (Bookmarks Manager → Export)
- Data imported: URLs, titles, folders (as tags)
- Notes: Nested folders flattened to tags

#### 4. **Firefox Bookmarks**
- Format: JSON or HTML export
- Data imported: URLs, titles, folders (as tags), timestamps
- Notes: Similar to Chrome import

#### 5. **Generic HTML**
- Format: Standard Netscape Bookmark File Format
- Data imported: URLs, titles, basic metadata
- Notes: Compatible with most bookmark managers

#### 6. **Generic JSON**
- Format: Custom or standard bookmark JSON
- Data imported: Configurable based on schema
- Notes: Flexible mapping for custom formats

---

## Export Formats

### 1. **JSON Export**
Complete data export with all metadata:
```json
{
  "format": "arivu_json_v1",
  "export_date": "2026-01-12T10:00:00Z",
  "total_bookmarks": 156,
  "bookmarks": [
    {
      "id": "bookmark_xyz",
      "url": "https://example.com/article",
      "title": "Article Title",
      "summary": "One-sentence summary",
      "one_sentence_summary": "...",
      "bullet_points": ["Point 1", "Point 2"],
      "long_summary": "...",
      "highlights": ["Quote 1", "Quote 2"],
      "tags": ["ai", "technology"],
      "created_at": "2026-01-12T00:00:00Z",
      "read_status": false,
      "reading_time_minutes": 5,
      "quality_score": 0.85
    }
  ]
}
```

### 2. **HTML Export**
Standard Netscape Bookmark File Format (compatible with all browsers):
```html
<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Arivu Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><A HREF="https://example.com/article" ADD_DATE="1673481600" TAGS="ai,technology">Article Title</A>
    <DD>One-sentence summary
</DL><p>
```

### 3. **CSV Export**
Spreadsheet-compatible format:
```csv
URL,Title,Tags,Summary,Created At,Read Status,Reading Time (min),Quality Score
https://example.com/article,Article Title,"ai,technology",One-sentence summary,2026-01-12T00:00:00Z,false,5,0.85
```

---

## How It Works

### Import Process

1. **File Upload**
   - User uploads file via `/imports` page
   - File validated for format and size (max 50MB)
   - File content parsed and validated

2. **Parsing**
   - HTML parsed with BeautifulSoup
   - Raindrop JSON accepts top-level arrays or objects containing `items`, `bookmarks`, `raindrops`, or `result`
   - CSV parsed with Python's CSV parser
   - Metadata extracted (URLs, titles, tags, timestamps)
   - Unsafe URLs are skipped before database insertion

3. **Background Processing**
   - Import job created with unique ID
   - Bookmarks queued for processing
   - Each bookmark processed in background:
     - Duplicate check performed
     - Content fetched and analyzed
     - AI summaries generated
     - Tags normalized

4. **Progress Tracking**
   - Real-time progress updates via API
   - Email notification on completion (optional)
   - Failed items logged with reasons

5. **Completion**
   - Import statistics generated
   - User notified
   - Failed items available for retry

### Export Process

1. **Request**
   - User selects export format (JSON, HTML, CSV)
   - Optional filters applied (tags, date range, read status)

2. **Generation**
   - Bookmarks fetched from database
   - Data formatted according to selected format
   - File generated in-memory

3. **Download**
   - File returned as attachment
   - Filename: `arivu_bookmarks_2026-01-12.json`
   - No server storage (generated on-demand)

---

## API Endpoints

### POST /api/bookmarks/import
Start a new bookmark import job.

**Request:**
```javascript
// Form data with file upload
const formData = new FormData()
formData.append('file', selectedFile)
formData.append('source', 'pocket')  // pocket, raindrop, chrome, firefox, html, json
formData.append('format', 'html')     // html, json, csv
```

**Response:**
```json
{
  "job_id": "import_job_123",
  "status": "processing",
  "message": "Import started. Processing bookmarks in background.",
  "total_bookmarks": 150,
  "created_at": "2026-01-12T10:00:00Z"
}
```

---

### GET /api/import-jobs
List all import jobs for the current user.

**Response:**
```json
[
  {
    "id": "import_job_123",
    "status": "completed",
    "source": "pocket",
    "format": "html",
    "total_bookmarks": 150,
    "imported_count": 145,
    "failed_count": 5,
    "duplicate_count": 12,
    "created_at": "2026-01-12T10:00:00Z",
    "started_at": "2026-01-12T10:00:01Z",
    "completed_at": "2026-01-12T10:05:00Z",
    "duration_seconds": 299
  }
]
```

**Status Values:**
- `pending` - Job created, waiting to start
- `processing` - Currently importing bookmarks
- `completed` - Import finished successfully
- `failed` - Import failed with errors
- `partial` - Some bookmarks imported, some failed

---

### GET /api/import-jobs/{job_id}
Get detailed status of a specific import job.

**Response:**
```json
{
  "id": "import_job_123",
  "status": "processing",
  "source": "pocket",
  "format": "html",
  "total_bookmarks": 150,
  "imported_count": 87,
  "failed_count": 2,
  "duplicate_count": 5,
  "progress_percentage": 58,
  "current_bookmark": "Processing: Article Title...",
  "failed_items": [
    {
      "url": "https://example.com/broken",
      "reason": "URL not accessible",
      "timestamp": "2026-01-12T10:02:30Z"
    }
  ],
  "created_at": "2026-01-12T10:00:00Z",
  "started_at": "2026-01-12T10:00:01Z",
  "estimated_completion": "2026-01-12T10:08:00Z"
}
```

---

### GET /api/bookmarks/export
Export all bookmarks in specified format.

**Query Parameters:**
- `format`: Export format (`json`, `html`, `csv`)
- `tags` (optional): Filter by tags (comma-separated)
- `read_status` (optional): Filter by read status (`true`, `false`)
- `from_date` (optional): Export bookmarks from date (ISO 8601)
- `to_date` (optional): Export bookmarks until date (ISO 8601)

**Example:**
```
GET /api/bookmarks/export?format=json&tags=ai,ml&read_status=true
```

**Response:**
- Content-Type: application/json (or text/html, text/csv)
- Content-Disposition: attachment; filename="arivu_bookmarks_2026-01-12.json"
- Body: Exported file content

---

## Use Cases

### 1. **Migrate from Pocket**
"I'm switching from Pocket to Arivu. I export my Pocket bookmarks as HTML and import them in seconds."

### 2. **Consolidate Bookmarks**
"I have bookmarks in Chrome, Firefox, and Raindrop.io. I import all of them into Arivu and have one unified library."

### 3. **Backup Bookmarks**
"I export my Arivu bookmarks as JSON monthly for backup, and as HTML for browser import if needed."

### 4. **Share Collections**
"I export bookmarks tagged 'resources' as HTML and share with my team."

### 5. **Migrate to Another Service**
"If I ever want to leave Arivu, I can export everything as JSON or HTML and import elsewhere."

---

## Import Mapping

### Pocket → Arivu
| Pocket Field | Arivu Field | Notes |
|--------------|-------------|-------|
| `resolved_url` | `url` | Primary URL |
| `given_title` | `title` | User-provided title |
| `tags` | `tags` | Array of tags |
| `time_added` | `created_at` | Unix timestamp converted |
| `status` | `read_status` | 0=unread, 1=read |

### Raindrop.io → Arivu
| Raindrop Field | Arivu Field | Notes |
|----------------|-------------|-------|
| `link` | `url` | Bookmark URL |
| `title` | `title` | Title |
| `tags` | `tags` | CSV converted to array |
| `collection` | `tags` | Collection name added as tag |
| `created` | `created_at` | ISO 8601 date |

### Chrome/Firefox → Arivu
| Browser Field | Arivu Field | Notes |
|---------------|-------------|-------|
| `HREF` | `url` | Bookmark URL |
| Title text | `title` | Link text |
| Folder path | `tags` | Folders → tags |
| `ADD_DATE` | `created_at` | Unix timestamp |

---

## Configuration

### Import Limits
```python
# Maximum file size for import
MAX_IMPORT_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Maximum bookmarks per import
MAX_BOOKMARKS_PER_IMPORT = 10000

# Import timeout per bookmark
IMPORT_TIMEOUT_PER_BOOKMARK = 30  # seconds
```

### Processing
```python
# Background task workers
IMPORT_WORKERS = 5

# Batch size for bulk insert
IMPORT_BATCH_SIZE = 100

# Retry failed bookmarks
IMPORT_RETRY_COUNT = 3
```

### Duplicate Handling
```python
# How to handle duplicates during import
DUPLICATE_STRATEGY = "skip"  # skip, update, or create_new

# Similarity threshold for duplicate detection
IMPORT_DUPLICATE_THRESHOLD = 0.90  # Higher than normal duplicates
```

---

## Performance

### Import Speed
- **Small import** (1-100 bookmarks): 1-2 minutes
- **Medium import** (100-1000 bookmarks): 5-15 minutes
- **Large import** (1000-10000 bookmarks): 30-90 minutes

Factors affecting speed:
- Content fetching time
- AI processing (summaries, tags)
- Duplicate checking
- Server load

### Export Speed
- **JSON export:** Instant (in-memory generation)
- **HTML export:** Instant
- **CSV export:** Instant
- Maximum file size: ~100MB for 10,000 bookmarks

---

## Error Handling

### Common Import Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid file format" | Unsupported file type | Check format and source |
| "File too large" | >50MB | Split file or compress |
| "URL not accessible" | Dead link or paywall | URL skipped, logged as failed |
| "Parsing failed" | Corrupt file | Try re-exporting from source |
| "Duplicate bookmark" | Already exists | Check duplicate strategy setting |

### Failed Bookmark Retry

Users can retry failed bookmarks:
```javascript
POST /api/import-jobs/{job_id}/retry
{
  "failed_urls": ["https://example.com/1", "https://example.com/2"]
}
```

---

## Frontend Implementation

### Import Page (`/imports`)

**Components:**
1. **FileUploader** - Drag-and-drop or file picker
2. **SourceSelector** - Select import source (Pocket, Raindrop, etc.)
3. **FormatSelector** - Select file format (HTML, JSON, CSV)
4. **ImportProgress** - Real-time progress bar and stats
5. **ImportHistory** - List of past imports with status

**State Management:**
```javascript
const [file, setFile] = useState(null)
const [source, setSource] = useState('pocket')
const [format, setFormat] = useState('html')
const [importing, setImporting] = useState(false)
const [jobId, setJobId] = useState(null)
const [progress, setProgress] = useState(null)
```

**Progress Polling:**
```javascript
useEffect(() => {
  if (!jobId) return

  const interval = setInterval(async () => {
    const status = await fetch(`/api/import-jobs/${jobId}`)
    setProgress(status)

    if (status.status === 'completed' || status.status === 'failed') {
      clearInterval(interval)
    }
  }, 2000)  // Poll every 2 seconds

  return () => clearInterval(interval)
}, [jobId])
```

---

## Best Practices

### For Users

**Before Import:**
1. Export from source service in recommended format
2. Check file size (max 50MB)
3. Review bookmarks for quality (optional)
4. Backup existing Arivu bookmarks

**During Import:**
1. Don't close browser tab
2. Monitor progress for errors
3. Note failed bookmarks for manual add

**After Import:**
1. Review imported bookmarks
2. Check for duplicates
3. Clean up tags if needed
4. Retry failed bookmarks

### For Developers

**Import Processing:**
1. Always validate file format first
2. Process in batches (100 at a time)
3. Use background tasks (don't block)
4. Log all failures with details
5. Provide clear error messages

**Export Generation:**
1. Stream large exports (don't load all in memory)
2. Apply user filters correctly
3. Sanitize data for security
4. Use standard formats for compatibility

---

## Security Considerations

### Import Security
- File type validation (check MIME type and content)
- Size limits enforced (prevent DoS)
- Content sanitization (prevent XSS)
- Rate limiting (max 5 imports per hour)

### Export Security
- User authentication required
- Only user's own bookmarks exported
- Sensitive data excluded (user_id, internal IDs)
- No server-side storage of exports

---

## Limitations

Current limitations:
- Max 50MB file size
- Max 10,000 bookmarks per import
- English content only for AI processing
- No real-time import (background processing)
- No incremental/sync imports

Not currently implemented:
- Automatic periodic sync imports
- Multi-language import-specific processing
- Streaming imports above the configured file limit
- Custom field mapping
- Scheduled exports

---

## Troubleshooting

### Import stuck at 0%
- Check browser console for errors
- Verify backend is running
- Check import job status via API
- Contact support if persistent

### Many failed bookmarks
- Common causes: dead links, paywalls, rate limits
- Review failed items list
- Manually add important ones
- Consider content quality

### Export download fails
- Check bookmark count (very large exports may timeout)
- Try different format (JSON is most efficient)
- Apply filters to reduce export size
- Contact support for assistance

---

## Technical Implementation

### Libraries Used
- **Parsing:** `beautifulsoup4` (HTML), `pandas` (CSV)
- **File Handling:** `python-multipart` (uploads)
- **Background Jobs:** `BackgroundTasks` (FastAPI)
- **Validation:** `pydantic` (schema validation)

### Database Schema

**Import Jobs Collection:**
```json
{
  "id": "import_job_123",
  "user_id": "user_id",
  "source": "pocket",
  "format": "html",
  "status": "processing",
  "total_bookmarks": 150,
  "imported_count": 87,
  "failed_count": 2,
  "duplicate_count": 5,
  "failed_items": [
    {"url": "...", "reason": "...", "timestamp": "..."}
  ],
  "created_at": "2026-01-12T10:00:00Z",
  "started_at": "2026-01-12T10:00:01Z",
  "completed_at": null,
  "settings": {
    "duplicate_strategy": "skip",
    "process_ai": true
  }
}
```

---

## Example Workflows

### Pocket Migration
```bash
1. Go to https://getpocket.com/export
2. Click "Export HTML"
3. Download pocket_export.html
4. In Arivu: /imports → Select "Pocket" → Upload file
5. Wait for import to complete (~5 min for 500 bookmarks)
6. Review imported bookmarks
```

### Browser Bookmark Import
```bash
1. Chrome: Menu → Bookmarks → Bookmark Manager → Export
2. Save bookmarks.html
3. In Arivu: /imports → Select "Chrome" → Upload file
4. Wait for processing
5. All bookmarks now in Arivu with AI summaries
```

### Backup Workflow
```bash
1. Monthly: Export all bookmarks as JSON
2. Save to local backup folder
3. Optional: Export as HTML for browser import backup
4. Test restore occasionally to verify integrity
```

---

## Related Features

- **[Duplicates Detection](duplicates-detection.md)** - Used during import to prevent duplicates
- **[Content Intelligence](content-intelligence.md)** - Evaluates imported bookmarks
- **Dashboard** - Displays import history and stats

---

## References

- **API Docs:** [documentation/api/README.md](../api/README.md#importexport-endpoints)
- **Pocket Export:** https://getpocket.com/export
- **Raindrop Export:** https://app.raindrop.io/settings/backups

---

**Last Updated:** May 10, 2026
**Status:** Implemented for Pocket/Raindrop import, import job tracking, export, and backup
