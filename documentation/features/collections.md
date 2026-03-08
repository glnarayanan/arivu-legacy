# Collections

**Status:** ✅ Fully Implemented
**Implemented:** January 2026
**Frontend:** Integrated in Dashboard
**API:** `/api/collections/*`

---

## Overview

Collections allow you to organize bookmarks into custom groups beyond simple tagging. Think of collections as folders, playlists, or projects - they help you group related bookmarks for specific purposes, topics, or workflows.

---

## Key Features

### 1. **Custom Organization**
Create unlimited collections:
- Named collections (e.g., "AI Research", "Design Inspiration", "Read Later")
- Optional descriptions
- Cover images or colors (planned)
- Public or private visibility (planned)

### 2. **Flexible Membership**
Bookmarks can belong to multiple collections:
- One bookmark in many collections
- Easy add/remove interface
- Bulk actions (add multiple bookmarks)
- Drag-and-drop organization (planned)

### 3. **Collection Views**
Browse bookmarks by collection:
- Filter dashboard by collection
- Dedicated collection pages
- Collection-specific stats
- Export collection separately

### 4. **Smart Collections**
Auto-populated based on rules (planned):
- "All unread bookmarks"
- "High quality (score >0.8)"
- "Saved this week"
- "Tagged 'tutorial'"

---

## How It Works

### Backend Structure

Collections are stored as separate documents with relationships to bookmarks:

```python
# Collection document
{
  "id": "collection_123",
  "user_id": "user_id",
  "name": "AI Research",
  "description": "Resources for my AI research project",
  "bookmark_ids": ["bm_1", "bm_2", "bm_3"],
  "bookmark_count": 3,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-12T00:00:00Z"
}
```

**Relationship Model:**
- One-to-many: One collection contains many bookmarks
- Many-to-many: One bookmark can be in many collections
- Lightweight: Only bookmark IDs stored in collection

---

## API Endpoints

### GET /api/collections
List all collections for current user.

**Response:**
```json
[
  {
    "id": "collection_123",
    "name": "AI Research",
    "description": "Resources for my AI research project",
    "bookmark_count": 23,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-12T00:00:00Z",
    "preview_bookmarks": [
      {
        "id": "bookmark_1",
        "title": "ML Guide",
        "url": "https://example.com/ml"
      }
    ]
  },
  {
    "id": "collection_456",
    "name": "Design Inspiration",
    "description": "Beautiful design examples",
    "bookmark_count": 45,
    "created_at": "2026-01-05T00:00:00Z",
    "updated_at": "2026-01-10T00:00:00Z",
    "preview_bookmarks": [ /* ... */ ]
  }
]
```

---

### POST /api/collections
Create a new collection.

**Request:**
```json
{
  "name": "Reading List Q1 2026",
  "description": "Articles to read in Q1",
  "bookmark_ids": ["bookmark_1", "bookmark_2"]  // Optional initial bookmarks
}
```

**Response:**
```json
{
  "id": "collection_789",
  "name": "Reading List Q1 2026",
  "description": "Articles to read in Q1",
  "bookmark_count": 2,
  "created_at": "2026-01-12T10:00:00Z",
  "updated_at": "2026-01-12T10:00:00Z"
}
```

---

### GET /api/collections/{collection_id}
Get details of a specific collection.

**Response:**
```json
{
  "id": "collection_123",
  "name": "AI Research",
  "description": "Resources for my AI research project",
  "bookmark_count": 23,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-12T00:00:00Z",
  "bookmarks": [
    {
      "id": "bookmark_1",
      "url": "https://example.com/ml-guide",
      "title": "Complete ML Guide",
      "summary": "Comprehensive guide...",
      "tags": ["ml", "ai"],
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### PUT /api/collections/{collection_id}
Update collection details.

**Request:**
```json
{
  "name": "Updated Collection Name",
  "description": "Updated description"
}
```

**Response:** Updated collection object

---

### DELETE /api/collections/{collection_id}
Delete a collection (bookmarks remain intact).

**Response:**
```json
{
  "message": "Collection deleted successfully",
  "deleted_id": "collection_123"
}
```

---

### POST /api/collections/{collection_id}/add
Add a bookmark to a collection.

**Request:**
```json
{
  "bookmark_id": "bookmark_xyz"
}
```

**Response:**
```json
{
  "message": "Bookmark added to collection",
  "collection_id": "collection_123",
  "bookmark_id": "bookmark_xyz",
  "new_bookmark_count": 24
}
```

---

### POST /api/collections/{collection_id}/remove
Remove a bookmark from a collection.

**Request:**
```json
{
  "bookmark_id": "bookmark_xyz"
}
```

**Response:**
```json
{
  "message": "Bookmark removed from collection",
  "collection_id": "collection_123",
  "bookmark_id": "bookmark_xyz",
  "new_bookmark_count": 22
}
```

---

### POST /api/collections/{collection_id}/bulk-add
Add multiple bookmarks to a collection.

**Request:**
```json
{
  "bookmark_ids": ["bm_1", "bm_2", "bm_3", "bm_4"]
}
```

**Response:**
```json
{
  "message": "4 bookmarks added to collection",
  "added_count": 4,
  "new_bookmark_count": 27
}
```

---

## Use Cases

### 1. **Project Organization**
"I'm working on a research paper about AI ethics. I create a collection to group all related bookmarks in one place."

### 2. **Curated Lists**
"I maintain a 'Best React Tutorials' collection that I share with my team (when sharing is implemented)."

### 3. **Reading Queue**
"I have a 'Read This Week' collection where I add bookmarks I plan to read soon. After reading, I move them to topic-specific collections."

### 4. **Client Work**
"For each client project, I create a collection to organize relevant resources, competitor research, and inspiration."

### 5. **Learning Paths**
"I created a 'Learn Python' collection with bookmarks ordered from beginner to advanced topics."

---

## Collection Strategies

### By Topic
```
Collections:
- Machine Learning
- Web Development
- Design Systems
- Product Management
```

### By Status
```
Collections:
- To Read
- Currently Reading
- Reference Material
- Completed
```

### By Project
```
Collections:
- Project Alpha Resources
- Project Beta Research
- Competitor Analysis
- Design Inspiration
```

### By Time
```
Collections:
- Q1 2026 Reading
- January Discoveries
- Weekend Reads
- Quick References
```

---

## Configuration

### Limits
```python
# Maximum collections per user
MAX_COLLECTIONS = 100

# Maximum bookmarks per collection
MAX_BOOKMARKS_PER_COLLECTION = 5000

# Collection name length
MAX_COLLECTION_NAME_LENGTH = 100
MAX_COLLECTION_DESCRIPTION_LENGTH = 500
```

### Features
```python
# Enable collection sharing (planned)
ENABLE_COLLECTION_SHARING = False

# Enable smart collections (planned)
ENABLE_SMART_COLLECTIONS = False

# Enable collection exports
ENABLE_COLLECTION_EXPORT = True
```

---

## Frontend Implementation

### Dashboard Integration

**Collection Sidebar:**
```javascript
const [collections, setCollections] = useState([])
const [selectedCollection, setSelectedCollection] = useState(null)

useEffect(() => {
  fetch('/api/collections').then(setCollections)
}, [])

// Filter bookmarks by collection
const filteredBookmarks = selectedCollection
  ? bookmarks.filter(b =>
      selectedCollection.bookmark_ids.includes(b.id)
    )
  : bookmarks
```

**Add to Collection Dialog:**
```javascript
const AddToCollectionDialog = ({ bookmark }) => {
  const [selectedCollections, setSelectedCollections] = useState([])

  const addToCollections = async () => {
    await Promise.all(
      selectedCollections.map(collectionId =>
        fetch(`/api/collections/${collectionId}/add`, {
          method: 'POST',
          body: JSON.stringify({ bookmark_id: bookmark.id })
        })
      )
    )
  }

  return (
    <Dialog>
      <CheckboxList options={collections} onChange={setSelectedCollections} />
      <Button onClick={addToCollections}>Add to Collections</Button>
    </Dialog>
  )
}
```

---

## Performance

### Optimization
- Collections loaded once on dashboard init
- Bookmark counts cached (updated on add/remove)
- Preview bookmarks limited to 5
- Lazy loading for collection details

### Database Indexes
- `user_id` - Fast user collections lookup
- `user_id` + `name` - Unique collection names per user
- `bookmark_ids` (array) - Fast membership checks

---

## Best Practices

### For Users

**Collection Naming:**
- Use clear, descriptive names
- Avoid ambiguous names like "Stuff" or "Misc"
- Use consistent naming convention
- Add descriptions for context

**Organization:**
- Don't over-organize (avoid too many collections)
- Use tags for broad categories, collections for specific groups
- Review collections periodically
- Archive or delete unused collections

**Workflow:**
- Add bookmarks to collections immediately
- Use collections for active projects
- Use tags for permanent categorization
- Combine tags + collections for powerful organization

### For Developers

**Data Integrity:**
- Validate bookmark ownership before adding to collection
- Clean up orphaned bookmark_ids (deleted bookmarks)
- Check collection limits before adding
- Handle concurrent modifications

**Performance:**
- Don't load all bookmarks for large collections
- Use pagination for collection views
- Cache collection metadata
- Batch bookmark additions

---

## Limitations

Current limitations:
- No collection sharing (single user only)
- No smart/dynamic collections
- No collection hierarchy (nested collections)
- No collection templates
- No collection cover images

**Planned Improvements (Q2 2026):**
- Collection sharing (public links, team sharing)
- Smart collections (auto-populate based on rules)
- Nested collections (sub-collections)
- Collection templates (quick setup)
- Visual customization (colors, icons, covers)
- Collection activity feed
- Collaborative collections (team editing)

---

## Troubleshooting

### Collection not showing
- Refresh page (cache issue)
- Check browser console for errors
- Verify collection belongs to current user

### Cannot add bookmark to collection
- Check bookmark ownership (must be yours)
- Verify collection limit not reached
- Check for duplicate (already in collection)

### Collection count incorrect
- Counts cached for performance
- Refresh or clear cache
- Report if persistent issue

---

## Technical Implementation

### Libraries Used
- **Backend:** `pymongo` (MongoDB collections)
- **Validation:** `pydantic` (schema validation)
- **Frontend:** `react` (UI components)

### Database Schema

**Collections Collection:**
```json
{
  "id": "collection_123",
  "user_id": "user_id",
  "name": "AI Research",
  "description": "Resources for my AI research project",
  "bookmark_ids": ["bm_1", "bm_2", "bm_3"],
  "bookmark_count": 3,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-12T00:00:00Z",
  "settings": {
    "public": false,
    "color": "#3B82F6",
    "icon": "beaker"
  }
}
```

**Bookmark with Collections (embedded):**
```json
{
  "id": "bookmark_xyz",
  "url": "https://example.com/article",
  "title": "Article Title",
  "collection_ids": ["collection_123", "collection_456"],
  "collection_count": 2
}
```

---

## Collection vs. Tags

| Feature | Collections | Tags |
|---------|-------------|------|
| **Purpose** | Group related bookmarks for projects/topics | Categorize bookmarks broadly |
| **Relationship** | Explicit membership | Flexible labeling |
| **Hierarchy** | Planned (nested) | Flat (no hierarchy) |
| **Visibility** | Per-collection settings | All tags public to user |
| **Management** | Dedicated UI | Inline editing |
| **Use Case** | Active projects, reading lists | Permanent categorization |
| **Count** | Limited (~100) | Unlimited |

**Best Practice:** Use both!
- **Tags** for broad categories: "ai", "design", "tutorial"
- **Collections** for specific groups: "Q1 Reading List", "Client Project A"

---

## Export Collections

Export a specific collection separately:

```bash
GET /api/bookmarks/export?format=json&collection_id=collection_123
```

Response includes only bookmarks from that collection.

---

## Bulk Operations

### Add All Bookmarks with Tag
```javascript
// Add all "tutorial" tagged bookmarks to "Learning" collection
const tutorialBookmarks = bookmarks.filter(b => b.tags.includes('tutorial'))
await fetch(`/api/collections/${learningCollectionId}/bulk-add`, {
  method: 'POST',
  body: JSON.stringify({
    bookmark_ids: tutorialBookmarks.map(b => b.id)
  })
})
```

### Move Between Collections
```javascript
// Move bookmark from Collection A to Collection B
await fetch(`/api/collections/${collectionA}/remove`, {
  method: 'POST',
  body: JSON.stringify({ bookmark_id: bookmarkId })
})

await fetch(`/api/collections/${collectionB}/add`, {
  method: 'POST',
  body: JSON.stringify({ bookmark_id: bookmarkId })
})
```

---

## Future Features

### Smart Collections (Planned Q2 2026)
```javascript
// Example smart collection rules
{
  "name": "High Quality Unread",
  "smart": true,
  "rules": {
    "quality_score": {"$gte": 0.8},
    "read_status": false
  },
  "auto_update": true
}
```

### Collection Sharing (Planned Q3 2026)
```javascript
// Share collection publicly
{
  "collection_id": "collection_123",
  "sharing": {
    "public": true,
    "public_url": "https://your-domain.com/shared/abc123",
    "allow_cloning": true
  }
}
```

---

## Related Features

- **[Import/Export](import-export.md)** - Import preserves collection structure from Raindrop.io
- **Dashboard** - Collection filtering and sidebar
- **Tags** - Complementary organization system

---

## References

- **API Docs:** [documentation/api/README.md](../api/README.md#collections-endpoints)

---

**Last Updated:** January 12, 2026
**Status:** Fully Implemented (Basic Features)
**Next Enhancements:** Q2 2026 (Smart collections, Sharing, Nesting)
