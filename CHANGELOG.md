# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Open-source release infrastructure (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY)
- Self-hosted Docker Compose configuration (`docker-compose.yml`) with frontend, backend, MongoDB, and Redis
- Administrative API key management UI and backend
- Toggleable user registration via `SIGNUPS_ENABLED` environment variable
- OSS export tooling and GitHub Actions sync workflow
- CI/CD pipelines for automated testing and linting
- Frontend test infrastructure with Vitest and Testing Library
- ESLint flat config for frontend code quality
- Ruff and Black configuration for backend Python linting
- Pre-commit hooks for secrets detection and code formatting
- Dependabot configuration for automated dependency updates
- Architecture documentation (`documentation/architecture.md`)
- Troubleshooting guide (`documentation/troubleshooting.md`)
- CLI commands for local stack orchestration, Pocket/Raindrop import, URL preview, graph search, and analytics summaries
- Security notes for the latest GitHub security remediation pass

### Changed
- Pinned `pytest-asyncio` to `<1.0` to avoid breaking changes
- Restored server-side X OAuth/API integration (removed DOM scraping)
- Refactored runtime configuration to dedicated resolver
- Moved project reference docs into `documentation/` and refreshed stale deployment, API, and environment references
- Updated deployment documentation to match the current frontend nginx entry point and `/api` proxy
- Replaced dated roadmap language with current-state documentation and explicit "not currently implemented" sections
- Rewrote the collections feature guide to match the current backend model and endpoints

### Removed
- Extension-side DOM scraping for X integration
- Redundant documentation files (DOCUMENTATION_AUDIT.md, DOCUMENTATION_REVIEW.md)
- Stale deployment references from active project docs
- Stale Create React App template comments from the Vite frontend HTML template

## [1.0.0] - 2026-03-08

### Added
- AI-powered bookmarking with automatic summarization, tagging, and categorization
- Knowledge Graph visualization of bookmark relationships
- Analytics dashboard with reading insights
- Resurfacing engine for bookmark rediscovery (Memory Jogger)
- Collections and tag-based organization
- Full-text search with AI-enhanced results
- Import/Export support (HTML bookmarks, JSON backup)
- Duplicate detection and merge tools
- Chrome/Firefox browser extension (Manifest V3)
- X (Twitter) bookmark sync via OAuth API
- Cookie-based JWT authentication with token refresh
- Rate limiting and account lockout protection
- Email-based password reset
