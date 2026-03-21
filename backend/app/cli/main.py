"""Main Typer application for the Arivu CLI."""

from __future__ import annotations

import json
import webbrowser
from pathlib import Path

import typer

from app.cli.client import ArivuAPIClient, CLIClientError, resolve_collection_id
from app.cli.config import ConfigStore
from app.cli.formatters import (
    console,
    print_bookmark,
    print_collections,
    print_graph_overview,
    print_profiles,
    print_resurfacing,
    print_search_results,
    print_status,
    print_user,
)
from app.cli.local import DockerOrchestrator, LocalEnvironmentError, discover_repo_root, validate_root_env

app = typer.Typer(help="Arivu command line interface")
profile_app = typer.Typer(help="Manage CLI profiles")
auth_app = typer.Typer(help="Authenticate CLI profiles")
collections_app = typer.Typer(help="Manage collections")
resurface_app = typer.Typer(help="Resurfacing commands")
graph_app = typer.Typer(help="Knowledge graph commands")
local_app = typer.Typer(help="Manage a local Arivu stack")

app.add_typer(profile_app, name="profile")
app.add_typer(auth_app, name="auth")
app.add_typer(collections_app, name="collections")
app.add_typer(resurface_app, name="resurface")
app.add_typer(graph_app, name="graph")
app.add_typer(local_app, name="local")


def get_store() -> ConfigStore:
    return ConfigStore()


def get_client(profile_name: str | None = None) -> tuple[ConfigStore, ArivuAPIClient]:
    store = get_store()
    _, profile = store.get_profile(profile_name)
    return store, ArivuAPIClient(store, profile)


def exit_with_error(message: str) -> None:
    console.print(f"[red]{message}[/red]")
    raise typer.Exit(code=1)


@profile_app.command("add")
def profile_add(
    name: str,
    url: str = typer.Option(..., "--url", help="Base URL for the Arivu API or app"),
) -> None:
    """Add or update a profile."""
    try:
        profile = get_store().upsert_profile(name, url)
    except ValueError as err:
        exit_with_error(str(err))
    print_status("Profile Saved", f"{profile.name}\n{profile.base_url}")


@profile_app.command("use")
def profile_use(name: str) -> None:
    """Set the active profile."""
    try:
        profile = get_store().set_active_profile(name)
    except ValueError as err:
        exit_with_error(str(err))
    print_status("Active Profile", f"{profile.name}\n{profile.base_url}")


@profile_app.command("list")
def profile_list() -> None:
    """List configured profiles."""
    config, profiles = get_store().list_profiles()
    print_profiles(profiles, config.active_profile)


@profile_app.command("remove")
def profile_remove(name: str) -> None:
    """Remove a saved profile."""
    try:
        get_store().remove_profile(name)
    except ValueError as err:
        exit_with_error(str(err))
    print_status("Profile Removed", name)


@auth_app.command("login")
def auth_login(
    profile: str = typer.Option(..., "--profile", help="Profile name"),
    url: str | None = typer.Option(None, "--url", help="Create the profile if it does not exist"),
) -> None:
    """Authenticate a CLI profile."""
    store = get_store()
    try:
        store.get_profile(profile)
    except ValueError:
        if not url:
            exit_with_error(f"Profile '{profile}' not found. Create it first or pass --url.")
        store.upsert_profile(profile, url)

    _, client = get_client(profile)
    email = typer.prompt("Email")
    password = typer.prompt("Password", hide_input=True)
    try:
        payload = client.login(email, password)
    except CLIClientError as err:
        exit_with_error(str(err))
    print_user(payload["user"], profile)


@auth_app.command("logout")
def auth_logout(profile: str | None = typer.Option(None, "--profile", help="Profile name")) -> None:
    """Remove stored auth tokens from a profile."""
    store = get_store()
    try:
        _, profile_record = store.get_profile(profile)
        store.clear_auth(profile_record.name)
    except ValueError as err:
        exit_with_error(str(err))
    print_status("Logged Out", profile_record.name)


@auth_app.command("whoami")
def auth_whoami(profile: str | None = typer.Option(None, "--profile", help="Profile name")) -> None:
    """Show the authenticated user."""
    try:
        _, client = get_client(profile)
        user = client.whoami()
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))
    print_user(user, client.profile.name)


@app.command("save")
def save_bookmark(
    url: str,
    collection: str | None = typer.Option(None, "--collection", help="Collection name or ID"),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Save a bookmark URL."""
    try:
        _, client = get_client(profile)
        collection_id = resolve_collection_id(client, collection)
        result = client.save_bookmark(url, collection_id=collection_id)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))
    bookmark = result["bookmark"]
    print_status("Bookmark Saved", f"{bookmark.get('id')}\n{bookmark.get('title')}\nAI status: pending")


@app.command("search")
def search(
    query: str,
    limit: int = typer.Option(10, "--limit", min=1, max=100),
    semantic: bool = typer.Option(True, "--semantic/--no-semantic"),
    keyword: bool = typer.Option(True, "--keyword/--no-keyword"),
    as_json: bool = typer.Option(False, "--json", help="Print raw JSON"),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Search bookmarks."""
    try:
        _, client = get_client(profile)
        payload = client.search(query, limit=limit, use_semantic=semantic, use_keyword=keyword)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))

    if as_json:
        console.print_json(json.dumps(payload))
        return

    print_search_results(payload.get("results", []), query)


@app.command("show")
def show(
    bookmark_id: str,
    as_json: bool = typer.Option(False, "--json", help="Print raw JSON"),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Show bookmark details."""
    try:
        _, client = get_client(profile)
        payload = client.get_bookmark(bookmark_id)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))

    if as_json:
        console.print_json(json.dumps(payload))
        return

    print_bookmark(payload)


@app.command("open")
def open_bookmark(
    bookmark_id: str,
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Open a bookmark in the system browser."""
    try:
        _, client = get_client(profile)
        bookmark = client.get_bookmark(bookmark_id)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))
    webbrowser.open(bookmark["url"])
    print_status("Opened Bookmark", bookmark["url"])


@collections_app.command("list")
def collections_list(profile: str | None = typer.Option(None, "--profile", help="Profile name")) -> None:
    """List collections."""
    try:
        _, client = get_client(profile)
        collections = client.list_collections()
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))
    print_collections(collections)


@collections_app.command("create")
def collections_create(
    name: str,
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Create a collection."""
    try:
        _, client = get_client(profile)
        collection = client.create_collection(name)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))
    print_status("Collection Created", f"{collection['name']}\n{collection['id']}")


@collections_app.command("add")
def collections_add(
    collection: str,
    bookmark_id: str,
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Add a bookmark to a collection."""
    try:
        _, client = get_client(profile)
        collection_id = resolve_collection_id(client, collection)
        client.add_to_collection(collection_id, bookmark_id)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))
    print_status("Collection Updated", f"{bookmark_id} -> {collection}")


@resurface_app.command("list")
def resurface_list(
    limit: int = typer.Option(5, "--limit", min=1, max=50),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """List resurfacing suggestions."""
    try:
        _, client = get_client(profile)
        payload = client.list_resurfacing(limit=limit)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))
    print_resurfacing(payload.get("suggestions", []))


@resurface_app.command("snooze")
def resurface_snooze(
    bookmark_id: str,
    days: int = typer.Option(7, "--days", min=1, max=90),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Snooze a resurfacing suggestion."""
    try:
        _, client = get_client(profile)
        payload = client.snooze_resurfacing(bookmark_id, days=days)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))
    print_status("Bookmark Snoozed", payload["message"])


@resurface_app.command("archive")
def resurface_archive(
    bookmark_id: str,
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Archive a resurfacing suggestion."""
    try:
        _, client = get_client(profile)
        payload = client.archive_resurfacing(bookmark_id)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))
    print_status("Bookmark Archived", payload["message"])


@graph_app.command("search")
def graph_search(
    query: str,
    limit: int = typer.Option(10, "--limit", min=1, max=50),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Run semantic graph search."""
    try:
        _, client = get_client(profile)
        payload = client.graph_search(query, limit=limit)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))
    print_search_results(payload.get("results", []), query)


@graph_app.command("overview")
def graph_overview(
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Show a high-level knowledge graph summary."""
    try:
        _, client = get_client(profile)
        payload = client.graph_overview(limit=limit)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))
    print_graph_overview(payload)


@local_app.command("up")
def local_up() -> None:
    """Start the full local Arivu stack with Docker Compose."""
    try:
        repo_root = discover_repo_root(Path.cwd())
        warnings = validate_root_env(repo_root)
        orchestrator = DockerOrchestrator(repo_root)
        orchestrator.ensure_available()
        message = orchestrator.up()
        store = get_store()
        store.upsert_profile("local", "http://localhost/api", is_local_profile=True)
        store.set_active_profile("local")
    except (LocalEnvironmentError, ValueError) as err:
        exit_with_error(str(err))

    if warnings:
        for warning in warnings:
            console.print(f"[yellow]{warning}[/yellow]")
    print_status("Local Stack", message)


@local_app.command("down")
def local_down() -> None:
    """Stop the local Arivu stack."""
    try:
        repo_root = discover_repo_root(Path.cwd())
        orchestrator = DockerOrchestrator(repo_root)
        orchestrator.ensure_available()
        message = orchestrator.down()
    except LocalEnvironmentError as err:
        exit_with_error(str(err))
    print_status("Local Stack", message)


@local_app.command("status")
def local_status() -> None:
    """Show Docker Compose and application health status."""
    try:
        repo_root = discover_repo_root(Path.cwd())
        orchestrator = DockerOrchestrator(repo_root)
        orchestrator.ensure_available()
        payload = orchestrator.status()
    except LocalEnvironmentError as err:
        exit_with_error(str(err))
    print_status(
        "Local Stack Status",
        "\n\n".join(
            [
                payload["compose_status"],
                f"frontend: {payload['frontend_health']}",
                f"backend: {payload['backend_health']}",
            ]
        ),
    )


@local_app.command("logs")
def local_logs(service: str | None = typer.Argument(None, help="Optional service name")) -> None:
    """Show recent logs from the local Arivu stack."""
    try:
        repo_root = discover_repo_root(Path.cwd())
        orchestrator = DockerOrchestrator(repo_root)
        orchestrator.ensure_available()
        output = orchestrator.logs(service)
    except LocalEnvironmentError as err:
        exit_with_error(str(err))
    console.print(output or "No logs available.")

