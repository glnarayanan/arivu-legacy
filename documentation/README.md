# Arivu Documentation

This folder is the canonical project documentation for contributors, operators, and AI assistants.

## Folder Structure

### `api/`
API reference for application endpoints.
- `README.md`: endpoint catalog, auth model, request and response examples

### `features/`
Implementation and behavior docs for product features.
- Includes Knowledge Graph, CLI, Resurfacing, Analytics, Collections, Import/Export, Duplicates, and X integration

### `deployment/`
Infrastructure and operations documentation.
- `DEPLOYMENT.md`: local and production deployment
- `ENVIRONMENT_VARIABLES.md`: environment variable reference

## Quick Reference

| Need | Document |
|------|----------|
| API endpoints | `documentation/api/README.md` |
| Feature behavior | `documentation/features/README.md` |
| CLI usage | `documentation/features/cli.md` |
| Self-hosting and deployment | `documentation/deployment/DEPLOYMENT.md` |
| Environment configuration | `documentation/deployment/ENVIRONMENT_VARIABLES.md` |

## Documentation Maintenance Rules

1. Update docs in the same PR/commit as behavior changes.
2. Remove stale docs when a feature path is replaced.
3. Prefer concrete examples and exact file paths.
4. Keep root clean; add new docs under `documentation/` unless they are marketing-site content.
