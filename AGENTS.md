# Agent Notes

Keep this file lean. Load the focused docs under `documentation/` when needed.

## Canonical Docs

- Project overview: `README.md`
- Documentation index: `documentation/README.md`
- Architecture: `documentation/architecture.md`
- API reference: `documentation/api/README.md`
- Deployment: `documentation/deployment/DEPLOYMENT.md`
- Environment variables: `documentation/deployment/ENVIRONMENT_VARIABLES.md`
- Troubleshooting: `documentation/troubleshooting.md`
- Security notes: `documentation/security.md`
- Changelog: `CHANGELOG.md`

## Working Rules

- Keep long-form project docs in `documentation/`.
- Update relevant documentation and `CHANGELOG.md` when behavior, setup, or operational guidance changes.
- Keep deployment docs aligned with the checked-in Docker Compose stack.
- Frontend API calls currently use relative `/api`; Docker nginx proxies requests to the backend.
- Run relevant checks before handing off: backend `pytest tests/ -m "not integration"`, frontend `yarn lint`, and frontend `yarn test --run` when dependencies are available.
