"""HTTP client for the Arivu CLI."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

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
        return expires_at <= datetime.now(UTC) + timedelta(seconds=30)

    def _headers(self, extra: dict | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if extra:
            headers.update(extra)
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
        content_body: bytes | str | None = None,
        params: dict | None = None,
        extra_headers: dict | None = None,
        require_auth: bool = True,
        retry_on_401: bool = True,
    ) -> httpx.Response:
        if require_auth and not self.profile.is_authenticated:
            raise CLIClientError(f"Profile '{self.profile.name}' is not authenticated")

        if require_auth and self._access_token_expired():
            self.refresh_tokens()

        headers = self._headers(extra_headers)

        try:
            with httpx.Client(timeout=30.0) as client:
                if content_body is not None:
                    response = client.request(
                        method,
                        self._url(path),
                        headers=headers,
                        content=content_body,
                        params=params,
                    )
                else:
                    response = client.request(
                        method,
                        self._url(path),
                        headers=headers,
                        json=json_body,
                        params=params,
                    )
        except httpx.TimeoutException as e:
            raise CLIClientError(f"Request timeout: {e}") from e
        except httpx.ConnectError as e:
            raise CLIClientError(f"Connection failed: {e}") from e
        except httpx.RequestError as e:
            raise CLIClientError(f"Network error: {e}") from e

        if response.status_code == 401 and require_auth and retry_on_401:
            self.refresh_tokens()
            return self._request(
                method,
                path,
                json_body=json_body,
                content_body=content_body,
                params=params,
                extra_headers=extra_headers,
                require_auth=require_auth,
                retry_on_401=False,
            )

        if response.is_error:
            detail = None
            try:
                payload = response.json()
                detail = payload.get("detail") or payload.get("message")
            except ValueError:
                detail = None
            if not detail:
                detail = f"Request failed with status {response.status_code}"
            raise CLIClientError(detail)

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

    def list_bookmarks(
        self,
        *,
        limit: int = 20,
        tag: str | None = None,
        collection_id: str | None = None,
        read_status: str | None = None,
    ) -> list[dict]:
        """Fetch bookmarks with optional filters."""
        params: dict = {"limit": limit}
        if tag:
            params["tag"] = tag
        if collection_id:
            params["collection_id"] = collection_id
        if read_status:
            params["read_status"] = read_status
        response = self._request("GET", "/bookmarks", params=params)
        return response.json()

    def delete_bookmark(self, bookmark_id: str) -> dict:
        """Delete a bookmark by ID."""
        response = self._request("DELETE", f"/bookmarks/{bookmark_id}")
        return response.json()

    def save_bookmarks(
        self,
        urls: list[str],
        collection_id: str | None = None,
    ) -> dict:
        """Save multiple URLs sequentially. Returns {saved: [], failed: []}."""
        saved: list[dict] = []
        failed: list[dict] = []

        for url in urls:
            try:
                result = self.save_bookmark(url, collection_id=collection_id)
                saved.append(result.get("bookmark", {"url": url, "id": result.get("id")}))
            except CLIClientError as e:
                failed.append({"url": url, "error": str(e)})

        return {"saved": saved, "failed": failed}

    def import_bookmarks(self, file_path: Path, *, source: str) -> dict:
        """Import bookmarks from file."""
        if not file_path.exists():
            raise CLIClientError(f"File not found: {file_path}")

        # Security: Enforce file size limit (50MB to match backend)
        max_size = 50 * 1024 * 1024  # 50MB
        file_size = file_path.stat().st_size
        if file_size > max_size:
            raise CLIClientError(f"File too large: {file_size / (1024 * 1024):.1f}MB. Maximum allowed: 50MB")

        content = file_path.read_bytes()
        headers = {
            "Content-Type": "application/octet-stream",
            "X-Import-Source": source,
        }

        response = self._request(
            "POST",
            "/bookmarks/import",
            content_body=content,
            extra_headers=headers,
        )
        return response.json()

    def get_analytics_summary(self, *, days: int = 30) -> dict:
        """Get analytics summary for time window."""
        response = self._request("GET", "/analytics/summary", params={"days": days})
        return response.json()

    def preview_url(self, url: str) -> dict:
        """Fetch URL preview metadata through the authenticated API."""
        response = self._request("POST", "/bookmarks/preview", json_body={"url": url})
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
