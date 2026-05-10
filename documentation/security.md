# Security Notes

## 2026-05-10: GitHub Security Fixes

- Dependabot alert 68 (`CVE-2026-42561`, `GHSA-pp6c-gr5w-3c5g`) was addressed by upgrading `python-multipart` from `0.0.26` to `0.0.27` in `backend/requirements.txt`.
- CodeQL alert 15 (`py/full-ssrf`) was addressed in `backend/app/services/content_service.py` by keeping explicit fetch-time URL validation immediately before each request and before following redirects. Validation uses `is_safe_url(..., resolve_host=True)` to block unsupported schemes, embedded credentials, local hostnames, and private/reserved DNS resolutions. The request sink carries an in-source CodeQL suppression because the scanner does not infer the project-specific validation helper as a sanitizer.
- CodeQL alerts 12-14 were test-only findings in `backend/tests/test_cli.py`; the tests now use exact list equality assertions instead of substring-style membership checks.

Re-run the GitHub CodeQL and Dependabot checks after merging so GitHub can mark the alerts fixed on the default branch.
