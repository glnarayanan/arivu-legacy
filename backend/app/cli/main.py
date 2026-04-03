"""Main Typer application for the Arivu CLI."""

from __future__ import annotations

import json
import os
import shlex
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import List

import typer

from app.cli.client import ArivuAPIClient, CLIClientError, resolve_collection_id
from app.cli.config import ConfigStore
from app.cli.formatters import (
    console,
    print_bookmark,
    print_bookmarks_list,
    print_bulk_save_summary,
    print_collections,
    print_graph_overview,
    print_profiles,
    print_resurfacing,
    print_search_results,
    print_stats_summary,
    print_status,
    print_url_preview,
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
import_app = typer.Typer(help="Import bookmarks from external sources")

app.add_typer(profile_app, name="profile")
app.add_typer(auth_app, name="auth")
app.add_typer(collections_app, name="collections")
app.add_typer(resurface_app, name="resurface")
app.add_typer(graph_app, name="graph")
app.add_typer(local_app, name="local")
app.add_typer(import_app, name="import")


def get_store() -> ConfigStore:
    return ConfigStore()


def get_client(profile_name: str | None = None) -> tuple[ConfigStore, ArivuAPIClient]:
    store = get_store()
    effective_profile = profile_name or os.environ.get("ARIVU_PROFILE")
    _, profile = store.get_profile(effective_profile)
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
    urls: List[str],
    collection: str | None = typer.Option(None, "--collection", help="Collection name or ID"),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Save one or more bookmark URLs."""
    if not urls:
        exit_with_error("At least one URL is required")

    try:
        _, client = get_client(profile)
        collection_id = resolve_collection_id(client, collection)

        if len(urls) == 1:
            # Single URL - use simple output
            result = client.save_bookmark(urls[0], collection_id=collection_id)
            bookmark = result["bookmark"]
            print_status("Bookmark Saved", f"{bookmark.get('id')}\n{bookmark.get('title')}\nAI status: pending")
        else:
            # Multiple URLs - show progress and summary
            results = client.save_bookmarks(urls, collection_id=collection_id)
            print_bulk_save_summary(results["saved"], results["failed"])

    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))


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


@app.command("list")
def list_bookmarks(
    limit: int = typer.Option(20, "--limit", min=1, max=1000),
    unread: bool = typer.Option(False, "--unread", help="Show only unread bookmarks"),
    collection: str | None = typer.Option(None, "--collection", help="Filter by collection name or ID"),
    since: str | None = typer.Option(None, "--since", help="Show bookmarks created on or after date (YYYY-MM-DD)"),
    tag: str | None = typer.Option(None, "--tag", help="Filter by tag"),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """List bookmarks with optional filters."""
    try:
        _, client = get_client(profile)
        collection_id = resolve_collection_id(client, collection)
        read_status = "unread" if unread else None

        fetch_limit = limit if since is None else 1000
        bookmarks = client.list_bookmarks(
            limit=fetch_limit,
            tag=tag,
            collection_id=collection_id,
            read_status=read_status,
        )

        if since is not None:
            try:
                since_date = datetime.strptime(since, "%Y-%m-%d").date()
                since_iso = since_date.isoformat()
                bookmarks = [b for b in bookmarks if b.get("created_at", "") >= since_iso]
                bookmarks = bookmarks[:limit]
            except ValueError:
                exit_with_error(f"Invalid date format: {since}. Use YYYY-MM-DD.")

    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))

    print_bookmarks_list(bookmarks)


@app.command("delete")
def delete_bookmark(
    bookmark_id: str,
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt"),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Delete a bookmark by ID."""
    try:
        _, client = get_client(profile)

        if not force:
            bookmark = client.get_bookmark(bookmark_id)
            title = bookmark.get("title") or "Untitled"
            confirm = typer.confirm(f"Delete bookmark '{title}' ({bookmark_id})?")
            if not confirm:
                console.print("Cancelled")
                raise typer.Exit(code=0)

        client.delete_bookmark(bookmark_id)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))

    print_status("Bookmark Deleted", bookmark_id)


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


@import_app.command("pocket")
def import_pocket(
    file_path: Path = typer.Argument(..., help="Path to Pocket export HTML file", exists=True, readable=True),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Import bookmarks from a Pocket HTML export file."""
    try:
        _, client = get_client(profile)
        result = client.import_bookmarks(file_path, source="pocket")
        print_status("Import Complete", f"Imported {result.get('imported', 0)} bookmarks from Pocket")
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))


@import_app.command("raindrop")
def import_raindrop(
    file_path: Path = typer.Argument(..., help="Path to Raindrop.io export JSON file", exists=True, readable=True),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Import bookmarks from a Raindrop.io JSON export file."""
    try:
        _, client = get_client(profile)
        result = client.import_bookmarks(file_path, source="raindrop")
        print_status("Import Complete", f"Imported {result.get('imported', 0)} bookmarks from Raindrop.io")
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))


@app.command("stats")
def stats(
    weekly: bool = typer.Option(False, "--weekly", help="Show statistics for the last 7 days"),
    monthly: bool = typer.Option(False, "--monthly", help="Show statistics for the last 30 days"),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Show reading statistics and analytics."""
    if weekly and monthly:
        exit_with_error("Cannot use both --weekly and --monthly flags")

    days = 7 if weekly else 30 if monthly else 30
    label = "Last 7 days" if weekly else "Last 30 days" if monthly else "Last 30 days"

    try:
        _, client = get_client(profile)
        payload = client.get_analytics_summary(days=days)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))

    print_stats_summary(payload, label=label)


@app.command("preview")
def preview(
    url: str,
    collection: str | None = typer.Option(None, "--collection", help="Collection name or ID to save to"),
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Preview a URL before saving."""
    try:
        _, client = get_client(profile)
        preview_data = client.preview_url(url)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))

    print_url_preview(preview_data)

    # Ask if user wants to save
    from rich.prompt import Confirm

    if Confirm.ask("Save this bookmark?"):
        try:
            collection_id = resolve_collection_id(client, collection)
            result = client.save_bookmark(url, collection_id=collection_id)
            bookmark = result["bookmark"]
            print_status("Bookmark Saved", f"{bookmark.get('id')}\n{bookmark.get('title')}")
        except (ValueError, CLIClientError) as err:
            exit_with_error(str(err))
    else:
        console.print("[dim]Cancelled.[/dim]")


@app.command("interactive")
def interactive(
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
) -> None:
    """Start an interactive REPL session."""
    console.print("[bold green]Arivu Interactive Mode[/bold green]")
    console.print("Type 'help' for available commands, 'quit' to exit.\n")

    try:
        store, client = get_client(profile)
    except (ValueError, CLIClientError) as err:
        exit_with_error(str(err))

    from rich.prompt import Prompt

    while True:
        try:
            command_line = Prompt.ask("arivu")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        command_line = command_line.strip()
        if not command_line:
            continue

        if command_line.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if command_line.lower() == "help":
            console.print("""
[bold]Available commands:[/bold]
  save <url> [--collection NAME]     Save a bookmark
  search <query> [--limit N]           Search bookmarks
  list [--unread] [--limit N]          List bookmarks
  show <bookmark-id>                   Show bookmark details
  open <bookmark-id>                   Open bookmark in browser
  delete <bookmark-id> [--force]       Delete a bookmark
  stats [--weekly|--monthly]           Show analytics
  quit                                 Exit interactive mode

[dim]Tip: Use shell completion outside interactive mode for faster typing:[/dim]
[dim]  arivu --install-completion[/dim]
""")
            continue

        # Parse command
        try:
            tokens = shlex.split(command_line)
        except ValueError as e:
            console.print(f"[red]Invalid command: {e}[/red]")
            continue

        if not tokens:
            continue

        cmd = tokens[0].lower()
        args = tokens[1:]

        # Dispatch to appropriate handler
        try:
            if cmd == "save":
                if len(args) < 1:
                    console.print("[red]Usage: save <url>[/red]")
                    continue
                urls = [arg for arg in args if not arg.startswith("--")]
                collection_arg = next((arg for arg in args if arg.startswith("--collection")), None)
                collection = collection_arg.split("=", 1)[1] if collection_arg and "=" in collection_arg else None
                if not collection:
                    # Check if next arg is collection value
                    for i, arg in enumerate(args):
                        if arg == "--collection" and i + 1 < len(args):
                            collection = args[i + 1]
                            break
                result = client.save_bookmarks(
                    urls, collection_id=resolve_collection_id(client, collection) if collection else None
                )
                print_bulk_save_summary(result["saved"], result["failed"])

            elif cmd == "search":
                if len(args) < 1:
                    console.print("[red]Usage: search <query>[/red]")
                    continue
                query = args[0]
                limit = 10
                for i, arg in enumerate(args):
                    if arg == "--limit" and i + 1 < len(args):
                        try:
                            limit = int(args[i + 1])
                        except ValueError:
                            pass
                        break
                payload = client.search(query, limit=limit)
                print_search_results(payload.get("results", []), query)

            elif cmd == "list":
                limit = 20
                unread = False
                collection = None
                i = 0
                while i < len(args):
                    if args[i] == "--limit" and i + 1 < len(args):
                        try:
                            limit = int(args[i + 1])
                        except ValueError:
                            pass
                        i += 2
                    elif args[i] == "--unread":
                        unread = True
                        i += 1
                    elif args[i] == "--collection" and i + 1 < len(args):
                        collection = args[i + 1]
                        i += 2
                    else:
                        i += 1
                collection_id = resolve_collection_id(client, collection) if collection else None
                read_status = "unread" if unread else None
                bookmarks = client.list_bookmarks(limit=limit, collection_id=collection_id, read_status=read_status)
                print_bookmarks_list(bookmarks)

            elif cmd == "show":
                if len(args) < 1:
                    console.print("[red]Usage: show <bookmark-id>[/red]")
                    continue
                bookmark_id = args[0]
                bookmark = client.get_bookmark(bookmark_id)
                print_bookmark(bookmark)

            elif cmd == "open":
                if len(args) < 1:
                    console.print("[red]Usage: open <bookmark-id>[/red]")
                    continue
                bookmark_id = args[0]
                bookmark = client.get_bookmark(bookmark_id)
                url = bookmark.get("url")
                if url:
                    webbrowser.open(url)
                    print_status("Opened", f"{url}")
                else:
                    console.print("[red]No URL found for bookmark[/red]")

            elif cmd == "delete":
                if len(args) < 1:
                    console.print("[red]Usage: delete <bookmark-id> [--force][/red]")
                    continue
                bookmark_id = args[0]
                force = "--force" in args
                if not force:
                    from rich.prompt import Confirm

                    if not Confirm.ask(f"Delete bookmark {bookmark_id}?"):
                        console.print("[dim]Cancelled.[/dim]")
                        continue
                result = client.delete_bookmark(bookmark_id)
                print_status("Deleted", f"Bookmark {result.get('id')} deleted")

            elif cmd == "stats":
                weekly = "--weekly" in args
                monthly = "--monthly" in args
                days = 7 if weekly else 30
                payload = client.get_analytics_summary(days=days)
                label = "Last 7 days" if weekly else "Last 30 days"
                print_stats_summary(payload, label=label)

            else:
                console.print(f"[red]Unknown command: {cmd}. Type 'help' for available commands.[/red]")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
