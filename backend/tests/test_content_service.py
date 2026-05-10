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


@pytest.mark.anyio
async def test_fetch_webpage_content_blocks_unsafe_redirect_before_following(monkeypatch):
    """Redirect targets are validated before any follow-up network request."""
    requested_urls = []

    def open_response(url, headers):
        requested_urls.append(url)
        return RedirectResponse()

    monkeypatch.setattr("app.services.content_service._open_validated_response", open_response)
    monkeypatch.setattr(
        "app.services.content_service.is_safe_url",
        lambda url, resolve_host=False: (not url.startswith("http://127.0.0.1"), "blocked loopback"),
    )

    with pytest.raises(ValueError, match="Unsafe URL"):
        await fetch_webpage_content("https://example.com/article", raise_on_error=True)

    assert requested_urls == ["https://example.com/article"]
