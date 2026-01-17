# Technical Guides

This folder contains layman-friendly explanations of Arivu's unique features and AI-powered capabilities. These guides are designed for:

- **Marketing content creation** — explain features to potential users
- **Training materials** — onboard new team members
- **Sales enablement** — communicate value propositions clearly

## Feature Guides

| Guide | Feature | Key Benefit |
|-------|---------|-------------|
| [Knowledge Graph](./knowledge-graph.md) | Semantic connections between bookmarks | See how your saved content is interconnected |
| [Hybrid Search](./hybrid-search.md) | Smart search combining keywords & meaning | Find bookmarks by what they're about, not just exact words |
| [Duplicate Detection](./duplicate-detection.md) | Find and merge similar bookmarks | Keep your library clean and organized |
| [Intelligent Resurfacing](./intelligent-resurfacing.md) | Proactive bookmark reminders | Rediscover forgotten but valuable content |
| [AI Summarization](./ai-summarization.md) | Automatic content understanding | Get instant summaries without reading everything |
| [Entity Extraction](./entity-extraction.md) | Identify people, companies, technologies | Build a knowledge base of topics you follow |
| [Content Intelligence](./content-intelligence.md) | Quality and credibility scoring | Know which sources to trust |

## How These Features Work Together

```
┌─────────────────────────────────────────────────────────────────────┐
│                     When You Save a Bookmark                        │
├─────────────────────────────────────────────────────────────────────┤
│  1. Content fetched from URL                                        │
│  2. AI reads and understands the content                            │
│  3. Summary generated (one-sentence, key points, tags)              │
│  4. Entities extracted (people, companies, technologies)            │
│  5. Embedding created (mathematical meaning representation)         │
│  6. Connected to similar bookmarks in your Knowledge Graph          │
│  7. Ready for instant semantic search                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Glossary

| Term | Plain English |
|------|---------------|
| **Embedding** | A number that represents what a piece of content "means" |
| **Semantic** | Related to meaning, not just exact word matches |
| **Cosine Similarity** | A way to measure how similar two pieces of content are |
| **Entity** | A specific thing like a person, company, or technology |
| **TF-IDF** | A technique to find the most important words in text |
