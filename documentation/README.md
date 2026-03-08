# Arivu Documentation

This folder is the canonical project documentation for contributors, operators, and AI assistants.

## Folder Structure

### `api/`
API reference for application endpoints.
- `README.md`: endpoint catalog, auth model, request and response examples

### `features/`
Implementation and behavior docs for product features.
- Includes Knowledge Graph, Resurfacing, Analytics, Collections, Import/Export, Duplicates, and X integration

### `deployment/`
Infrastructure and operations documentation.
- `DEPLOYMENT.md`: local and production deployment
- `ENVIRONMENT_VARIABLES.md`: environment variable reference
- `RESTORATION.md`: backup and restore procedures

### `development/`
Engineering-focused implementation and security docs.
- `SECURITY_IMPROVEMENTS.md`

### `design/`
UI and design system guidance.
- `DESIGN_SYSTEM.md`

### `roadmap/`
Planning documents and roadmap items.

### `archive/`
Historical and verbose documents retained for reference.

## Quick Reference

| Need | Document |
|------|----------|
| API endpoints | `documentation/api/README.md` |
| Feature behavior | `documentation/features/README.md` |
| Self-hosting and deployment | `documentation/deployment/DEPLOYMENT.md` |
| Environment configuration | `documentation/deployment/ENVIRONMENT_VARIABLES.md` |
| Backup and restoration | `documentation/deployment/RESTORATION.md` |
| Security patterns | `documentation/development/SECURITY_IMPROVEMENTS.md` |
| Design rules | `documentation/design/DESIGN_SYSTEM.md` |
| Deep architecture history | `documentation/archive/CLAUDE-verbose.md` |

## Public Documentation Site

The marketing site now includes a public docs section for self-hosting users:
- `marketing/content/documentation/`

Use this for user-facing guides, and keep implementation/developer detail in this `documentation/` directory.

## Documentation Maintenance Rules

1. Update docs in the same PR/commit as behavior changes.
2. Remove stale docs when a feature path is replaced.
3. Prefer concrete examples and exact file paths.
4. Keep root clean; add new docs under `documentation/` unless they are marketing-site content.

## AI Assistant Context

1. Start with `/Users/tbl-gln/TBL/arivu-app/CLAUDE.md`.
2. Load only relevant docs; avoid loading the full tree.
3. Verify docs against code before trusting feature claims.
4. Update docs after every task completion.

**Last Updated:** February 19, 2026
