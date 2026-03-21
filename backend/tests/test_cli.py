"""Tests for the Arivu CLI package."""

from pathlib import Path

from typer.testing import CliRunner

from app.cli.client import resolve_collection_id
from app.cli.config import ConfigStore, normalize_api_url
from app.cli.main import app

runner = CliRunner()


class FakeClient:
    def __init__(self):
        self.profile = type("Profile", (), {"name": "test"})()

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
        return {"bookmark": {"id": "bm-1", "title": "Saved Bookmark"}}

    def list_collections(self):
        return [
            {"id": "col-1", "name": "Inbox", "bookmark_ids": []},
            {"id": "col-2", "name": "Research", "bookmark_ids": ["bm-1"]},
        ]


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

