# Security Notes

## 2026-06-13: Dependency and Lint Fixes

- `pip-audit` findings were addressed in `backend/requirements.txt` by upgrading `aiohttp` to `3.14.0` (`CVE-2026-34993`, `CVE-2026-47265`), `PyJWT` to `2.13.0` (`PYSEC-2026-175` through `PYSEC-2026-179`), and `starlette` to `1.0.1` (`CVE-2026-48710`, `PYSEC-2026-161`).
- `yarn audit --level high` findings were addressed in `frontend/package.json` by pinning `esbuild` to `^0.28.1` via Yarn resolutions (`GHSA-gv7w-rqvm-qjhr`, `GHSA-g7r4-m6w7-qqqr`).
- Backend Black formatting was restored in `backend/app/services/ai_service.py`.

## 2026-05-10: GitHub Security Fixes

- Dependabot alert 68 (`CVE-2026-42561`, `GHSA-pp6c-gr5w-3c5g`) was addressed by upgrading `python-multipart` from `0.0.26` to `0.0.27` in `backend/requirements.txt`.
- CodeQL alert 15 (`py/full-ssrf`) was addressed in `backend/app/services/content_service.py` by keeping explicit fetch-time URL validation immediately before each request and before following redirects. Validation uses `is_safe_url(..., resolve_host=True)` to block unsupported schemes, embedded credentials, local hostnames, and private/reserved DNS resolutions.
- CodeQL alerts 12-14 were test-only findings in `backend/tests/test_cli.py`; the tests now use exact list equality assertions instead of substring-style membership checks.

Re-run the GitHub CodeQL and Dependabot checks after merging so GitHub can mark the alerts fixed on the default branch.
