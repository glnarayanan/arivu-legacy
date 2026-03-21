"""HTTP client for the Arivu CLI."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.cli.config import ConfigStore, ProfileRecord


class CLIClientError(RuntimeError):
    """Raised for user-facing CLI client failures."""


class ArivuAPIClient:
    """Wrapper around the Arivu HTTP API with token refresh support."""

    def __init__(self, store: ConfigStore, profile: ProfileRecord):
        self.store = store
        self.profile = profile

    def _access_token_expired(self) -> bool:
        if not self.profile.access_token_expires_at:
            return True
        expires_at = datetime.fromisoformat(self.profile.access_token_expires_at)
        return expires_at <= datetime.now(timezone.utc) + timedelta(seconds=30)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.profile.access_token:
            headers["Authorization"] = f"Bearer {self.profile.access_token}"
        return headers

    def _url(self, path: str) -> str:
        return f"{self.profile.base_url}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | list | None = None,
        params: dict | None = None,
        require_auth: bool = True,
        retry_on_401: bool = True,
    ) -> httpx.Response:
        if require_auth and not self.profile.is_authenticated:
            raise CLIClientError(f"Profile '{self.profile.name}' is not authenticated")

        if require_auth and self._access_token_expired():
            self.refresh_tokens()

        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method,
                self._url(path),
                headers=self._headers(),
                json=json_body,
                params=params,
            )

        if response.status_code == 401 and require_auth and retry_on_401:
            self.refresh_tokens()
            return self._request(
                method,
                path,
                json_body=json_body,
                params=params,
                require_auth=require_auth,
                retry_on_401=False,
            )

        if response.is_error:
            detail = None
            try:
                payload = response.json()
                detail = payload.get("detail") or payload.get("message")
            except Exception:
                detail = response.text
            raise CLIClientError(detail or f"Request failed with status {response.status_code}")

        return response

    def login(self, email: str, password: str) -> dict:
        response = self._request(
            "POST",
            "/auth/cli/login",
            json_body={"email": email, "password": password},
            require_auth=False,
        )
        payload = response.json()
        self.profile = self.store.update_auth(self.profile.name, payload)
        return payload

    def refresh_tokens(self) -> dict:
        if not self.profile.refresh_token:
            raise CLIClientError(f"Profile '{self.profile.name}' has no refresh token")
        response = self._request(
            "POST",
            "/auth/cli/refresh",
            json_body={"refresh_token": self.profile.refresh_token},
            require_auth=False,
            retry_on_401=False,
        )
        payload = response.json()
        self.profile = self.store.update_auth(self.profile.name, payload)
        return payload

    def whoami(self) -> dict:
        response = self._request("GET", "/auth/me")
        return response.json()

    def get_bookmark(self, bookmark_id: str) -> dict:
        response = self._request("GET", f"/bookmarks/{bookmark_id}")
        return response.json()

    def save_bookmark(self, url: str, collection_id: str | None = None) -> dict:
        payload = {"url": url, "collection_id": collection_id}
        response = self._request("POST", "/bookmarks", json_body=payload)
        return response.json()

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        use_semantic: bool = True,
        use_keyword: bool = True,
    ) -> dict:
        response = self._request(
            "GET",
            "/search",
            params={
                "query": query,
                "limit": limit,
                "use_semantic": str(use_semantic).lower(),
                "use_keyword": str(use_keyword).lower(),
            },
        )
        return response.json()

    def list_collections(self) -> list[dict]:
        response = self._request("GET", "/collections")
        return response.json()

    def create_collection(self, name: str) -> dict:
        response = self._request("POST", "/collections", json_body={"name": name})
        return response.json()

    def add_to_collection(self, collection_id: str, bookmark_id: str) -> dict:
        response = self._request(
            "POST",
            f"/collections/{collection_id}/add",
            json_body={"bookmark_id": bookmark_id},
        )
        return response.json()

    def list_resurfacing(self, limit: int = 5) -> dict:
        response = self._request("GET", "/resurfacing", params={"limit": limit})
        return response.json()

    def snooze_resurfacing(self, bookmark_id: str, days: int = 7) -> dict:
        response = self._request("POST", f"/resurfacing/{bookmark_id}/snooze", json_body={"days": days})
        return response.json()

    def archive_resurfacing(self, bookmark_id: str) -> dict:
        response = self._request("POST", f"/resurfacing/{bookmark_id}/archive")
        return response.json()

    def graph_search(self, query: str, limit: int = 10) -> dict:
        response = self._request("GET", "/knowledge-graph/search", params={"query": query, "limit": limit})
        return response.json()

    def graph_overview(self, limit: int = 50) -> dict:
        response = self._request("GET", "/knowledge-graph/explore", params={"limit": limit})
        return response.json()


def resolve_collection_id(client: ArivuAPIClient, collection_name_or_id: str | None) -> str | None:
    """Resolve a collection by ID or exact name."""
    if not collection_name_or_id:
        return None

    collections = client.list_collections()
    for collection in collections:
        if collection.get("id") == collection_name_or_id:
            return collection["id"]

    matches = [collection for collection in collections if collection.get("name") == collection_name_or_id]
    if len(matches) == 1:
        return matches[0]["id"]
    if len(matches) > 1:
        raise CLIClientError(f"Multiple collections named '{collection_name_or_id}' found; use the collection ID")

    raise CLIClientError(f"Collection '{collection_name_or_id}' not found")
