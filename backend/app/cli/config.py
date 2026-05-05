"""Persistent CLI profile storage."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from platformdirs import user_config_dir


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_api_url(raw_url: str) -> str:
    """Normalize user-supplied URLs to an API base URL.

    Security: Only allows HTTP for localhost/loopback addresses.
    Remote profiles must use HTTPS to protect bearer tokens.
    """
    value = raw_url.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Profile URL must be an absolute http(s) URL")

    # Enforce HTTPS for non-local profiles (security fix)
    hostname = parsed.hostname
    is_local = hostname in {"localhost", "127.0.0.1", "::1"}

    if parsed.scheme == "http" and not is_local:
        raise ValueError(
            f"Remote profile URL must use HTTPS for security. HTTP is only allowed for localhost. Got: {raw_url}"
        )

    path = parsed.path.rstrip("/")
    if path in {"", "/"}:
        path = "/api"

    return parsed._replace(path=path, params="", query="", fragment="").geturl()


@dataclass
class ProfileRecord:
    name: str
    base_url: str
    is_local_profile: bool = False
    access_token: str | None = None
    refresh_token: str | None = None
    access_token_expires_at: str | None = None
    refresh_token_expires_at: str | None = None
    user_summary: dict = field(default_factory=dict)
    last_used_at: str | None = None
    auth_mode: str = "cli_token"

    @property
    def is_authenticated(self) -> bool:
        return bool(self.access_token and self.refresh_token)

    def touch(self) -> None:
        self.last_used_at = _now_iso()


@dataclass
class CLIConfig:
    active_profile: str | None = None
    profiles: dict[str, ProfileRecord] = field(default_factory=dict)


class ConfigStore:
    """Store CLI configuration in the user's config directory."""

    def __init__(self, config_dir: Path | None = None):
        # Check ARIVU_CONFIG_DIR environment variable first
        env_config_dir = os.environ.get("ARIVU_CONFIG_DIR")
        if env_config_dir:
            root = Path(env_config_dir)
        elif config_dir:
            root = config_dir
        else:
            root = Path(user_config_dir("arivu", "arivu"))
        self.config_dir = root
        self.config_file = root / "config.json"

    def load(self) -> CLIConfig:
        if not self.config_file.exists():
            return CLIConfig()

        data = json.loads(self.config_file.read_text(encoding="utf-8"))
        profiles: dict[str, ProfileRecord] = {}

        # Security: Revalidate all profile URLs on load to enforce HTTPS policy
        for name, profile_data in data.get("profiles", {}).items():
            try:
                # Revalidate URL to ensure HTTPS enforcement
                url = profile_data.get("base_url", "")
                if url:
                    profile_data["base_url"] = normalize_api_url(url)
                profiles[name] = ProfileRecord(name=name, **profile_data)
            except ValueError as e:
                # Skip invalid profiles (e.g., HTTP remote URLs that are no longer allowed)
                import warnings

                warnings.warn(f"Skipping invalid profile '{name}': {e}", stacklevel=2)
                continue

        # Security: Repair active_profile if it was filtered out
        active_profile = data.get("active_profile")
        if active_profile not in profiles:
            active_profile = next(iter(profiles.keys()), None)  # Reset to first valid or None

        return CLIConfig(
            active_profile=active_profile,
            profiles=profiles,
        )

    def save(self, config: CLIConfig) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "active_profile": config.active_profile,
            "profiles": {
                name: {key: value for key, value in asdict(profile).items() if key != "name"}
                for name, profile in config.profiles.items()
            },
        }
        self.config_file.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self.config_file.chmod(0o600)

    def list_profiles(self) -> tuple[CLIConfig, list[ProfileRecord]]:
        config = self.load()
        return config, sorted(config.profiles.values(), key=lambda profile: profile.name)

    def get_profile(self, name: str | None = None) -> tuple[CLIConfig, ProfileRecord]:
        config = self.load()
        profile_name = name or config.active_profile
        if not profile_name or profile_name not in config.profiles:
            raise ValueError("No active profile configured")
        return config, config.profiles[profile_name]

    def upsert_profile(self, name: str, base_url: str, *, is_local_profile: bool = False) -> ProfileRecord:
        config = self.load()
        existing = config.profiles.get(name)
        profile = existing or ProfileRecord(name=name, base_url=normalize_api_url(base_url))
        profile.base_url = normalize_api_url(base_url)
        profile.is_local_profile = is_local_profile
        profile.touch()
        config.profiles[name] = profile
        if not config.active_profile:
            config.active_profile = name
        self.save(config)
        return profile

    def set_active_profile(self, name: str) -> ProfileRecord:
        config = self.load()
        if name not in config.profiles:
            raise ValueError(f"Profile '{name}' not found")
        config.active_profile = name
        config.profiles[name].touch()
        self.save(config)
        return config.profiles[name]

    def remove_profile(self, name: str) -> None:
        config = self.load()
        if name not in config.profiles:
            raise ValueError(f"Profile '{name}' not found")
        del config.profiles[name]
        if config.active_profile == name:
            config.active_profile = next(iter(config.profiles.keys()), None)
        self.save(config)

    def update_auth(self, profile_name: str, payload: dict) -> ProfileRecord:
        config = self.load()
        if profile_name not in config.profiles:
            raise ValueError(f"Profile '{profile_name}' not found")

        profile = config.profiles[profile_name]
        profile.access_token = payload.get("access_token")
        profile.refresh_token = payload.get("refresh_token")
        profile.access_token_expires_at = payload.get("access_token_expires_at")
        profile.refresh_token_expires_at = payload.get("refresh_token_expires_at")
        profile.user_summary = payload.get("user") or {}
        profile.touch()
        config.active_profile = profile_name
        self.save(config)
        return profile

    def clear_auth(self, profile_name: str) -> ProfileRecord:
        config = self.load()
        if profile_name not in config.profiles:
            raise ValueError(f"Profile '{profile_name}' not found")

        profile = config.profiles[profile_name]
        profile.access_token = None
        profile.refresh_token = None
        profile.access_token_expires_at = None
        profile.refresh_token_expires_at = None
        profile.user_summary = {}
        profile.touch()
        self.save(config)
        return profile
