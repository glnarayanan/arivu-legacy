import os
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def server_module():
    backend_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_root))

    os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
    os.environ.setdefault("SECRET_KEY", "x" * 32)

    if "html2text" not in sys.modules:

        class _HTML2TextStub:  # minimal stub for import-time usage
            def __init__(self):
                pass

        sys.modules["html2text"] = types.SimpleNamespace(HTML2Text=_HTML2TextStub)

    if "google.generativeai" not in sys.modules:
        genai_stub = types.SimpleNamespace(
            configure=lambda *args, **kwargs: None,
            GenerativeModel=lambda *args, **kwargs: None,
        )
        sys.modules["google"] = types.SimpleNamespace(generativeai=genai_stub)
        sys.modules["google.generativeai"] = genai_stub

    if "resend" not in sys.modules:
        sys.modules["resend"] = types.SimpleNamespace(api_key=None)

    import server

    return server


def test_normalize_url_for_dedup_strips_tracking(server_module):
    normalize = server_module.normalize_url_for_dedup
    url = "https://Example.com/path/?utm_source=twitter&utm_medium=social&id=1#section"
    assert normalize(url) == "https://example.com/path?id=1"


def test_normalize_url_for_dedup_trailing_slash(server_module):
    normalize = server_module.normalize_url_for_dedup
    url = "https://example.com/path/"
    assert normalize(url) == "https://example.com/path"


def test_build_x_oauth_url_encodes_params(server_module):
    build_url = server_module.build_x_oauth_url
    url = build_url(
        client_id="client123",
        redirect_uri="https://arivu.app/settings?section=connections",
        state="state456",
        code_challenge="challenge789",
        scopes="bookmark.read tweet.read",
    )

    assert url.startswith("https://twitter.com/i/oauth2/authorize?")
    assert "redirect_uri=https%3A%2F%2Farivu.app%2Fsettings%3Fsection%3Dconnections" in url
    assert "scope=bookmark.read%20tweet.read" in url
    assert "state=state456" in url
    assert "code_challenge=challenge789" in url


def test_map_x_sync_error_status(server_module):
    mapper = server_module.map_x_sync_error_status
    assert mapper(401) == "auth_expired"
    assert mapper(429) == "rate_limited"
    assert mapper(502) == "error"
