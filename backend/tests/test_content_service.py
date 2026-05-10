"""
Tests for webpage content fetching security behavior.
"""

import pytest
from app.services.content_service import fetch_webpage_content


class RedirectResponse:
    is_redirect = True
    headers = {"location": "http://127.0.0.1/admin"}

    def close(self):
        pass


class RecordingSession:
    trust_env = False

    def __init__(self):
        self.requested_urls = []

    def get(self, url, **kwargs):
        self.requested_urls.append(url)
        return RedirectResponse()


@pytest.mark.anyio
async def test_fetch_webpage_content_blocks_unsafe_redirect_before_following(monkeypatch):
    """Redirect targets are validated before any follow-up network request."""
    session = RecordingSession()

    monkeypatch.setattr("app.services.content_service.requests.Session", lambda: session)
    monkeypatch.setattr(
        "app.services.content_service.is_safe_url",
        lambda url, resolve_host=False: (not url.startswith("http://127.0.0.1"), "blocked loopback"),
    )

    with pytest.raises(ValueError, match="Unsafe URL"):
        await fetch_webpage_content("https://example.com/article", raise_on_error=True)

    assert session.requested_urls == ["https://example.com/article"]
