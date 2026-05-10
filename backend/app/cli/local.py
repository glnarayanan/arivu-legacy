"""Docker Compose orchestration for local CLI usage."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import httpx
from dotenv import dotenv_values


class LocalEnvironmentError(RuntimeError):
    """Raised when local orchestration cannot proceed."""


def discover_repo_root(start: Path | None = None) -> Path:
    """Find the repo root containing docker-compose.yml."""
    candidates = []
    if start is not None:
        candidates.extend([start, *start.parents])

    module_root = Path(__file__).resolve()
    candidates.extend(module_root.parents)

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        compose_file = candidate / "docker-compose.yml"
        if compose_file.exists() and (candidate / "frontend").exists() and (candidate / "backend").exists():
            return candidate

    raise LocalEnvironmentError("Could not find the Arivu repo root with docker-compose.yml")


def validate_root_env(repo_root: Path) -> list[str]:
    """Validate the root .env file before running docker compose."""
    env_file = repo_root / ".env"
    example_file = repo_root / ".env.example"
    if not env_file.exists():
        raise LocalEnvironmentError(f"Missing {env_file}. Copy {example_file.name} first.")

    values = dotenv_values(env_file)
    warnings = []
    secret_key = values.get("SECRET_KEY", "")
    gemini_api_key = values.get("GEMINI_API_KEY", "")

    if not secret_key or "change-in-production" in secret_key or len(secret_key) < 32:
        raise LocalEnvironmentError("Root .env has an invalid SECRET_KEY. Generate a real 32+ char secret first.")

    if not gemini_api_key or "your_gemini_api_key_here" in gemini_api_key:
        warnings.append("GEMINI_API_KEY is not configured; AI summaries and semantic features will be limited.")

    return warnings


class DockerOrchestrator:
    """Wrapper around docker compose for the local Arivu stack."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def _run(self, args: list[str], *, capture_output: bool = True) -> subprocess.CompletedProcess:
        command = ["docker", "compose", *args]
        try:
            # Args are selected by CLI commands; service names are passed as a single argv element.
            return subprocess.run(  # noqa: S603
                command,
                cwd=self.repo_root,
                check=True,
                text=True,
                capture_output=capture_output,
            )
        except FileNotFoundError as err:
            raise LocalEnvironmentError("Docker Compose is not available on PATH") from err
        except subprocess.CalledProcessError as err:
            stderr = err.stderr.strip() if err.stderr else str(err)
            raise LocalEnvironmentError(stderr) from err

    def ensure_available(self) -> None:
        self._run(["version"])

    def up(self) -> str:
        self._run(["up", "-d", "--build"])
        return "Local Arivu stack is starting."

    def down(self) -> str:
        self._run(["down"])
        return "Local Arivu stack has been stopped."

    def logs(self, service: str | None = None) -> str:
        args = ["logs", "--tail", "200"]
        if service:
            args.append(service)
        result = self._run(args)
        return result.stdout.strip()

    def status(self) -> dict:
        compose_status = self._run(["ps"], capture_output=True).stdout.strip()
        frontend_health = None
        backend_health = None

        try:
            frontend_health = httpx.get("http://localhost/health", timeout=5.0).text.strip()
        except Exception:
            frontend_health = "unreachable"

        try:
            backend_response = httpx.get("http://localhost/api/health", timeout=5.0)
            backend_health = json.dumps(backend_response.json())
        except Exception:
            backend_health = "unreachable"

        return {
            "compose_status": compose_status,
            "frontend_health": frontend_health,
            "backend_health": backend_health,
        }
