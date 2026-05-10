"""Tests for the Arivu CLI package."""

from pathlib import Path

import pytest
from app.cli.client import resolve_collection_id
from app.cli.config import ConfigStore, normalize_api_url
from app.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


class FakeClient:
    def __init__(self):
        self.profile = type("Profile", (), {"name": "test"})()
        self.saved_urls: list[str] = []
        self.deleted_ids: list[str] = []
        self.list_kwargs: dict = {}
        self.import_calls: list[dict] = []
        self.preview_calls: list[str] = []

    def search(self, query, limit=10, use_semantic=True, use_keyword=True):
        return {
            "results": [
                {
                    "id": "bm-1",
                    "title": "Example Result",
                    "domain": "example.com",
                    "relevance_score": 0.9,
                }
            ]
        }

    def get_bookmark(self, bookmark_id):
        return {
            "id": bookmark_id,
            "title": "Example Bookmark",
            "url": "https://example.com/article",
            "domain": "example.com",
            "ai_summary": {"one_sentence": "Summary"},
        }

    def save_bookmark(self, url, collection_id=None):
        self.saved_urls.append(url)
        return {"bookmark": {"id": "bm-1", "title": "Saved Bookmark", "url": url}}

    def list_collections(self):
        return [
            {"id": "col-1", "name": "Inbox", "bookmark_ids": []},
            {"id": "col-2", "name": "Research", "bookmark_ids": ["bm-1"]},
        ]

    def list_bookmarks(self, *, limit=20, tag=None, collection_id=None, read_status=None):
        self.list_kwargs = {
            "limit": limit,
            "tag": tag,
            "collection_id": collection_id,
            "read_status": read_status,
        }
        bookmarks = [
            {
                "id": "bm-1",
                "title": "First Bookmark",
                "domain": "example.com",
                "read": True,
                "created_at": "2026-03-01T10:00:00",
            },
            {
                "id": "bm-2",
                "title": "Second Bookmark",
                "domain": "test.com",
                "read": False,
                "created_at": "2026-03-15T12:00:00",
            },
        ]
        if read_status == "unread":
            bookmarks = [b for b in bookmarks if not b["read"]]
        return bookmarks[:limit]

    def delete_bookmark(self, bookmark_id):
        self.deleted_ids.append(bookmark_id)
        return {"message": "Bookmark deleted", "id": bookmark_id}

    def save_bookmarks(self, urls, collection_id=None):
        saved = []
        failed = []
        for url in urls:
            try:
                result = self.save_bookmark(url, collection_id)
                saved.append(result.get("bookmark", {"url": url}))
            except Exception as e:
                failed.append({"url": url, "error": str(e)})
        return {"saved": saved, "failed": failed}

    def import_bookmarks(self, file_path, *, source):
        self.import_calls.append({"file_path": file_path, "source": source})
        return {"imported": 5, "source": source}

    def get_analytics_summary(self, *, days=30):
        return {
            "stats": {
                "total_bookmarks": 100,
                "read_bookmarks": 75,
                "unread_bookmarks": 25,
                "completion_rate": 75.0,
                "total_reading_time_minutes": 360,
            },
            "topics": [
                {"name": "Python", "count": 20},
                {"name": "AI", "count": 15},
            ],
        }

    def preview_url(self, url):
        self.preview_calls.append(url)
        return {
            "url": url,
            "title": "Preview Title",
            "domain": "example.com",
            "description": "A preview description",
        }


def test_normalize_api_url_adds_api_path():
    assert normalize_api_url("http://localhost") == "http://localhost/api"
    assert normalize_api_url("https://example.com/api") == "https://example.com/api"


def test_config_store_round_trip(tmp_path):
    store = ConfigStore(config_dir=tmp_path)
    store.upsert_profile("local", "http://localhost", is_local_profile=True)
    store.set_active_profile("local")

    config, profiles = store.list_profiles()
    assert config.active_profile == "local"
    assert profiles[0].base_url == "http://localhost/api"
    assert profiles[0].is_local_profile is True


def test_resolve_collection_id_by_name():
    assert resolve_collection_id(FakeClient(), "Inbox") == "col-1"
    assert resolve_collection_id(FakeClient(), "col-2") == "col-2"


def test_search_command_renders_results(monkeypatch):
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, FakeClient()))

    result = runner.invoke(app, ["search", "example query"])

    assert result.exit_code == 0
    assert "Example Result" in result.stdout
    assert "bm-1" in result.stdout


def test_show_command_renders_bookmark(monkeypatch):
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, FakeClient()))

    result = runner.invoke(app, ["show", "bm-1"])

    assert result.exit_code == 0
    assert "Example Bookmark" in result.stdout
    assert "Summary" in result.stdout


def test_list_command_renders_bookmarks(monkeypatch):
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, FakeClient()))

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "First Bookmark" in result.stdout
    assert "Second Bookmark" in result.stdout
    assert "bm-1" in result.stdout
    assert "bm-2" in result.stdout


def test_list_command_with_unread_filter(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["list", "--unread"])

    assert result.exit_code == 0
    assert client.list_kwargs.get("read_status") == "unread"


def test_list_command_with_limit(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["list", "--limit", "5"])

    assert result.exit_code == 0
    assert client.list_kwargs.get("limit") == 5


def test_delete_command_confirms_and_deletes(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["delete", "bm-1"], input="y\n")

    assert result.exit_code == 0
    assert "bm-1" in client.deleted_ids


def test_delete_command_with_force_skips_confirm(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["delete", "bm-1", "--force"])

    assert result.exit_code == 0
    assert "bm-1" in client.deleted_ids


def test_save_command_accepts_single_url(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["save", "https://example.com"])

    assert result.exit_code == 0
    assert client.saved_urls == ["https://example.com"]


def test_save_command_accepts_multiple_urls(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["save", "https://example.com", "https://test.com"])

    assert result.exit_code == 0
    assert len(client.saved_urls) == 2


def test_import_pocket_command_posts_file(monkeypatch, tmp_path):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    # Create a dummy file
    test_file = tmp_path / "pocket.html"
    test_file.write_text("<html></html>")

    result = runner.invoke(app, ["import", "pocket", str(test_file)])

    assert result.exit_code == 0
    assert len(client.import_calls) == 1
    assert client.import_calls[0]["source"] == "pocket"


def test_import_raindrop_command_posts_file(monkeypatch, tmp_path):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    # Create a dummy file
    test_file = tmp_path / "raindrop.json"
    test_file.write_text('{"bookmarks": []}')

    result = runner.invoke(app, ["import", "raindrop", str(test_file)])

    assert result.exit_code == 0
    assert len(client.import_calls) == 1
    assert client.import_calls[0]["source"] == "raindrop"


def test_stats_command_renders_summary(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["stats"])

    assert result.exit_code == 0
    assert "100" in result.stdout  # total bookmarks


def test_stats_command_weekly_flag(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["stats", "--weekly"])

    assert result.exit_code == 0


def test_stats_command_rejects_conflicting_flags(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["stats", "--weekly", "--monthly"])

    assert result.exit_code != 0


def test_preview_command_renders_metadata(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["preview", "https://example.com"], input="n\n")

    assert result.exit_code == 0
    assert client.preview_calls == ["https://example.com"]


def test_preview_command_saves_when_confirmed(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["preview", "https://example.com"], input="y\n")

    assert result.exit_code == 0
    assert client.saved_urls == ["https://example.com"]


def test_preview_command_skips_save_when_declined(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["preview", "https://example.com"], input="n\n")

    assert result.exit_code == 0
    assert "https://example.com" not in client.saved_urls


def test_interactive_mode_exits_on_quit(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["interactive"], input="quit\n")

    assert result.exit_code == 0
    assert "Goodbye" in result.stdout or "Interactive" in result.stdout


def test_interactive_mode_shows_help(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.cli.main.get_client", lambda profile_name=None: (None, client))

    result = runner.invoke(app, ["interactive"], input="help\nquit\n")

    assert result.exit_code == 0
    assert "save" in result.stdout or "Available commands" in result.stdout


def test_normalize_api_url_enforces_https_for_remote():
    """Remote URLs must use HTTPS."""
    # Should raise for non-local HTTP
    with pytest.raises(ValueError, match="HTTPS"):
        normalize_api_url("http://example.com")

    with pytest.raises(ValueError, match="HTTPS"):
        normalize_api_url("http://api.example.com/api")

    # Should work for HTTPS
    assert normalize_api_url("https://example.com") == "https://example.com/api"
    assert normalize_api_url("https://api.example.com/api") == "https://api.example.com/api"

    # Should work for localhost HTTP
    assert normalize_api_url("http://localhost") == "http://localhost/api"
    assert normalize_api_url("http://127.0.0.1") == "http://127.0.0.1/api"


def test_import_bookmarks_enforces_file_size_limit(monkeypatch, tmp_path):
    """Import should reject files over 50MB."""
    from app.cli.client import ArivuAPIClient, CLIClientError

    # Create a fake profile and store
    store = ConfigStore(config_dir=tmp_path)
    profile = store.upsert_profile("test", "http://localhost/api", is_local_profile=True)
    client = ArivuAPIClient(store, profile)

    # Create a file (we mock the size check to avoid creating a 51MB file)
    large_file = tmp_path / "large_export.html"
    large_file.write_text("<html></html>")

    # Mock Path.stat() to return a large size
    def mock_stat(self):
        class MockStat:
            st_size = 51 * 1024 * 1024  # 51MB

        return MockStat()

    monkeypatch.setattr(Path, "stat", mock_stat)

    with pytest.raises(CLIClientError, match="50MB"):
        client.import_bookmarks(large_file, source="pocket")


def test_preview_url_uses_api_endpoint(tmp_path, monkeypatch):
    """Preview should call the authenticated API instead of fetching arbitrary URLs locally."""
    from app.cli.client import ArivuAPIClient

    store = ConfigStore(config_dir=tmp_path)
    profile = store.upsert_profile("test", "http://localhost/api", is_local_profile=True)
    client = ArivuAPIClient(store, profile)

    calls = []

    class MockResponse:
        def json(self):
            return {
                "url": "https://example.com",
                "title": "Example",
                "domain": "example.com",
            }

    def mock_request(method, path, *, json_body=None, **kwargs):
        calls.append({"method": method, "path": path, "json_body": json_body})
        return MockResponse()

    monkeypatch.setattr(client, "_request", mock_request)

    result = client.preview_url("https://example.com")

    assert result["title"] == "Example"
    assert calls == [
        {
            "method": "POST",
            "path": "/bookmarks/preview",
            "json_body": {"url": "https://example.com"},
        }
    ]


def test_config_store_uses_env_var(tmp_path, monkeypatch):
    """ARIVU_CONFIG_DIR environment variable should be respected."""
    env_dir = tmp_path / "env_config"
    monkeypatch.setenv("ARIVU_CONFIG_DIR", str(env_dir))

    store = ConfigStore()
    assert store.config_dir == env_dir


def test_normalize_api_url_blocks_private_ips():
    """Private IP addresses should be rejected for remote profiles."""
    # These should fail for HTTP
    with pytest.raises(ValueError):
        normalize_api_url("http://192.168.1.1")

    with pytest.raises(ValueError):
        normalize_api_url("http://10.0.0.1")

    # But localhost profile URLs are allowed for local development
    assert normalize_api_url("http://127.0.0.1") == "http://127.0.0.1/api"


def test_config_store_repairs_active_profile(tmp_path, monkeypatch):
    """ConfigStore should repair active_profile when invalid profiles are filtered."""
    import json
    import warnings

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    # Create config with one valid HTTPS profile and one invalid HTTP profile
    config_data = {
        "active_profile": "invalid_http",  # Points to HTTP remote that will be filtered
        "profiles": {
            "valid_https": {
                "base_url": "https://example.com/api",
                "access_token": "token1",
                "refresh_token": "refresh1",
            },
            "invalid_http": {
                "base_url": "http://example.com/api",  # Will be filtered out
                "access_token": "token2",
                "refresh_token": "refresh2",
            },
        },
    }
    config_file.write_text(json.dumps(config_data))

    # Monkeypatch platformdirs to use our temp directory
    monkeypatch.setenv("ARIVU_CONFIG_DIR", str(config_dir))

    with warnings.catch_warnings(record=True):
        store = ConfigStore()
        config = store.load()

    # The invalid profile should be filtered out
    assert "invalid_http" not in config.profiles
    assert "valid_https" in config.profiles

    # Active profile should be repaired to point to valid profile
    assert config.active_profile == "valid_https"


def test_config_store_handles_all_invalid_profiles(tmp_path, monkeypatch):
    """ConfigStore should set active_profile to None when all profiles are invalid."""
    import json
    import warnings

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    # Create config with only invalid profiles
    config_data = {
        "active_profile": "invalid_http",
        "profiles": {
            "invalid_http": {
                "base_url": "http://example.com/api",  # Will be filtered
                "access_token": "token",
                "refresh_token": "refresh",
            }
        },
    }
    config_file.write_text(json.dumps(config_data))

    monkeypatch.setenv("ARIVU_CONFIG_DIR", str(config_dir))

    with warnings.catch_warnings(record=True):
        store = ConfigStore()
        config = store.load()

    # No profiles should remain
    assert len(config.profiles) == 0
    # Active profile should be None
    assert config.active_profile is None
