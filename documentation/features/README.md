# Arivu Features Documentation

**Last Updated:** January 12, 2026

This folder contains detailed documentation for all Arivu features, with a focus on the advanced features implemented from the 2026 roadmap.

---

## Feature Status

### ✅ Core Features (Production)
- [Bookmarking & AI Summaries](#bookmarking--ai-summaries) - Instant save with background AI processing
- [Smart Highlights](#smart-highlights) - AI-extracted key quotes
- [Auto-Tagging](#auto-tagging) - Intelligent tag suggestions
- [Search & Filters](#search--filters) - Powerful search capabilities
- [Reading List](#reading-list) - Track read/unread status

### ✅ Advanced Features (2026 Roadmap - Implemented)
1. **[Knowledge Graph](knowledge-graph.md)** - Semantic AI-powered entity and relationship mapping (Roadmap Item 1)
2. **[Intelligent Resurfacing](resurfacing-engine.md)** - Spaced repetition engine (Roadmap Item 2)
3. **[Learning Analytics](analytics.md)** - Reading stats and insights (Roadmap Item 12)
4. **[Content Intelligence](content-intelligence.md)** - Quality scoring and evaluation (Roadmap Item 11)
5. **[Duplicates Management](duplicates-detection.md)** - Smart duplicate detection and merging
6. **[Import/Export](import-export.md)** - Seamless data migration
7. **[Collections](collections.md)** - Organize bookmarks into collections

### 🚧 In Progress
- Real-time collaboration (Roadmap Item 3)
- Mobile native apps (Roadmap Item 5)
- Developer API ecosystem (Roadmap Item 8)

### 📋 Planned (2026 Roadmap)
- Performance infrastructure overhaul (Roadmap Item 4)
- Advanced AI research assistant (Roadmap Item 6)
- Enterprise platform features (Roadmap Item 7)
- Comprehensive testing & CI/CD (Roadmap Item 9)
- Global expansion & localization (Roadmap Item 10)
- Social knowledge sharing (Roadmap Item 13)

---

## Quick Feature Overview

### Bookmarking & AI Summaries
Save any web page instantly with one click. AI automatically generates:
- One-sentence summary
- Bullet-point summary
- Long-form summary
- Auto-detected tags

**Access:** Dashboard, Browser extension
**API:** `POST /api/bookmarks`

---

### Smart Highlights
AI extracts the most important quotes and highlights from your saved content.

**Access:** Bookmark detail page
**API:** Included in bookmark response

---

### Auto-Tagging
Intelligent tag suggestions based on content analysis. Tags are automatically assigned but can be customized.

**Access:** Dashboard, Bookmark detail
**API:** Included in bookmark response

---

### Search & Filters
Powerful search across titles, content, summaries, and tags. Filter by:
- Tags
- Read status
- Date ranges
- Content type

**Access:** Dashboard
**API:** `GET /api/bookmarks?search=query&tag=tag`

---

### Reading List
Track which bookmarks you've read with automatic reading time estimation.

**Access:** Dashboard
**API:** `PATCH /api/bookmarks/{id}/read-status`

---

## Advanced Feature Details

For detailed documentation on advanced features, see individual feature pages:

- **[Knowledge Graph](knowledge-graph.md)** - Visualize connections between your bookmarks
- **[Intelligent Resurfacing](resurfacing-engine.md)** - Rediscover content at optimal times
- **[Learning Analytics](analytics.md)** - Reading stats, topic analysis, and AI insights
- **[Content Intelligence](content-intelligence.md)** - Quality scoring and content evaluation
- **[Duplicates Detection](duplicates-detection.md)** - Smart duplicate detection and merging
- **[Import/Export](import-export.md)** - Seamless migration from Pocket, Raindrop.io, browsers
- **[Collections](collections.md)** - Organize bookmarks into custom groups

---

## Feature Comparison

| Feature | Free | Pro (Planned) | Enterprise (Planned) |
|---------|------|---------------|---------------------|
| Bookmarks | Unlimited | Unlimited | Unlimited |
| AI Summaries | ✅ | ✅ | ✅ |
| Knowledge Graph | ✅ | ✅ | ✅ |
| Resurfacing | ✅ | ✅ | ✅ |
| Analytics | Basic | Advanced | Custom |
| Import/Export | ✅ | ✅ | ✅ |
| Collections | Unlimited | Unlimited | Unlimited |
| API Access | Limited | Full | Full + Webhooks |
| Team Collaboration | ❌ | Limited | Unlimited |
| SSO/SAML | ❌ | ❌ | ✅ |

---

## Feature Requests

To request new features:
1. Check the [2026 Roadmap](../roadmap/2026-roadmap/README.md)
2. Open a GitHub issue with label `feature-request`
3. Describe your use case and expected behavior

---

## Developer Resources

- **API Documentation:** [/documentation/api/](../api/README.md)
- **Architecture:** [/documentation/archive/CLAUDE-verbose.md](../archive/CLAUDE-verbose.md)
- **Design System:** [/documentation/design/BRUTALIST_DESIGN_SYSTEM.md](../design/BRUTALIST_DESIGN_SYSTEM.md)

---

**Last Updated:** January 12, 2026
