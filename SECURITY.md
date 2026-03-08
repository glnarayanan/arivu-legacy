# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Arivu, please report it responsibly.

**Email:** security@arivu.app

**Do NOT** open a public GitHub issue for security vulnerabilities.

## What to Include

- Description of the vulnerability
- Steps to reproduce
- Affected components (backend, frontend, extension, deployment)
- Potential impact

## Response Timeline

- **Acknowledgment:** Within 48 hours
- **Initial assessment:** Within 1 week
- **Fix timeline:** Depends on severity; critical issues are prioritized

## Scope

The following components are in scope:

- Backend API (`backend/server.py`)
- Frontend application (`frontend/`)
- Browser extension (`extension/`)
- Deployment configurations (`docker-compose*.yml`, nginx configs)
- Authentication and authorization flows

## Out of Scope

- Third-party services (MongoDB Atlas, Gemini API, X API)
- Issues in dependencies (report upstream; let us know if it affects Arivu)

## Disclosure

We will coordinate disclosure with the reporter. We aim to release fixes before public disclosure.
