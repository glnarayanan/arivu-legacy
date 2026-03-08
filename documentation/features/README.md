# Arivu Features Documentation

**Last Updated:** February 19, 2026

This folder documents shipped behavior and active feature integrations.

## Current Feature Set

### Core Product
- Bookmark capture with background AI processing
- AI summaries (one-line, bullets, long-form)
- Smart highlights and suggested tags
- Hybrid search and filtering
- Read-state tracking and reading time

### Advanced Capabilities
- [Knowledge Graph](knowledge-graph.md)
- [Intelligent Resurfacing](resurfacing-engine.md)
- [Analytics](analytics.md)
- [Content Intelligence](content-intelligence.md)
- [Duplicates Detection](duplicates-detection.md)
- [Import and Export](import-export.md)
- [Collections](collections.md)
- [X Bookmarks Integration](x-api-bookmarks.md)

## Integration Notes

### X Integration (API-based)

The active X integration path is server-side OAuth + API sync, exposed under `/api/auth/x/*`.
Extension-side DOM scraping is not part of the active architecture.

See:
- `documentation/features/x-api-bookmarks.md`
- `documentation/api/README.md`

## Product Status Snapshot

### Shipped
- Single-user bookmark knowledge system with AI enrichment
- Cookie-based authentication
- Browser extension quick-save flow
- Import/export workflows

### Planned / Roadmap
- Real-time collaboration
- Mobile-native clients
- Public developer API ecosystem
- Expanded enterprise controls

## Related Docs

- API reference: `documentation/api/README.md`
- Deployment and self-hosting: `documentation/deployment/DEPLOYMENT.md`
- Design system: `documentation/design/DESIGN_SYSTEM.md`
- Architecture history: `documentation/archive/CLAUDE-verbose.md`
