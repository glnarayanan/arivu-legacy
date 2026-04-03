"""HTTP client for the Arivu CLI."""

from __future__ import annotations

import ipaddress
import re
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

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
            raise CLIClientError(f"Request timeout: {e}")
        except httpx.ConnectError as e:
            raise CLIClientError(f"Connection failed: {e}")
        except httpx.RequestError as e:
            raise CLIClientError(f"Network error: {e}")

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
            except Exception:
                pass
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
        headers = {"Content-Type": "application/octet-stream", "X-Import-Source": source}

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

    def _is_safe_preview_url(self, url: str) -> tuple[bool, str]:
        """Check if URL is safe to fetch (not localhost/private IP).

        Security: Resolves DNS and checks ALL resolved IPs for private/loopback.
        Rejects URLs with embedded credentials.
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False, "Only http/https URLs are supported"

            hostname = parsed.hostname
            if not hostname:
                return False, "Invalid URL: no hostname"

            # Security: Reject URLs with embedded credentials
            if parsed.username or parsed.password:
                return False, "URLs with embedded credentials are not supported"

            # Check for localhost names
            if hostname in ("localhost", "127.0.0.1", "::1"):
                return False, "Cannot preview localhost URLs"

            # Security: Check for private IPs by resolving DNS - check ALL addresses
            try:
                # Get all resolved addresses
                addr_info = socket.getaddrinfo(hostname, None)
                if not addr_info:
                    return False, f"Cannot resolve hostname: {hostname}"

                # Check EVERY resolved IP address
                for addr in addr_info:
                    ip_str = addr[4][0]
                    try:
                        ip = ipaddress.ip_address(ip_str)
                        if (
                            ip.is_private
                            or ip.is_loopback
                            or ip.is_reserved
                            or ip.is_link_local
                            or ip.is_multicast
                            or ip.is_unspecified
                        ):
                            return False, "Cannot preview private/reserved network URLs"
                    except ValueError:
                        continue  # Skip invalid IPs

            except socket.gaierror:
                return False, f"Cannot resolve hostname: {hostname}"

            return True, ""
        except Exception as e:
            return False, f"URL validation error: {e}"

    def _is_response_url_safe(self, url: str) -> tuple[bool, str]:
        """Re-validate URL after redirects."""
        return self._is_safe_preview_url(url)

    def _extract_preview_metadata(self, html: str, url: str) -> dict:
        """Extract title and description from HTML."""
        # Extract title
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else None

        # Extract meta description
        desc_match = (
            re.search(
                r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
                html,
                re.IGNORECASE,
            )
            or re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
                html,
                re.IGNORECASE,
            )
            or re.search(
                r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
                html,
                re.IGNORECASE,
            )
        )
        description = desc_match.group(1).strip() if desc_match else None

        # Extract og:title if available
        og_title_match = re.search(
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if og_title_match:
            title = og_title_match.group(1).strip()

        parsed = urlparse(url)
        domain = parsed.netloc or "unknown"

        return {
            "url": url,
            "title": title or "Untitled",
            "description": description or "",
            "domain": domain,
        }

    def preview_url(self, url: str) -> dict:
        """Fetch basic metadata from URL for preview.

        Security: Manually follows redirects with validation at each hop.
        Prevents SSRF via redirect chains.
        """
        # Security: Validate initial URL
        is_safe, error = self._is_safe_preview_url(url)
        if not is_safe:
            raise CLIClientError(error)

        try:
            # Security: Disable automatic redirects, manually validate each hop
            with httpx.Client(timeout=10.0, follow_redirects=False, trust_env=False) as client:
                current_url = url
                max_redirects = 5

                for _ in range(max_redirects):
                    # Security: Validate URL before each request
                    is_safe, error = self._is_safe_preview_url(current_url)
                    if not is_safe:
                        raise CLIClientError(f"Redirect blocked: {error}")

                    response = client.get(
                        current_url,
                        headers={"User-Agent": "Mozilla/5.0 (compatible; ArivuCLI/1.0)"},
                    )

                    # Check if it's a redirect
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("Location")
                        if not location:
                            raise CLIClientError("Redirect missing Location header")

                        # Resolve relative URLs
                        current_url = str(response.url.join(location))
                        continue  # Loop to validate and follow the redirect

                    # Not a redirect, process the response
                    response.raise_for_status()
                    html = response.text[:50000]  # Limit size
                    return self._extract_preview_metadata(html, current_url)

                # Exceeded max redirects
                raise CLIClientError(f"Too many redirects (max: {max_redirects})")

        except httpx.TimeoutException:
            raise CLIClientError("Timeout fetching URL (10s limit)")
        except httpx.HTTPStatusError as e:
            raise CLIClientError(f"HTTP error {e.response.status_code} fetching URL")
        except Exception as e:
            if isinstance(e, CLIClientError):
                raise
            raise CLIClientError(f"Failed to fetch URL: {e}")

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
