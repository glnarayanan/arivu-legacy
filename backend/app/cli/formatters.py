"""Rich output helpers for CLI commands."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def print_profiles(profiles: list, active_profile: str | None) -> None:
    table = Table(title="Arivu Profiles")
    table.add_column("Name", style="bold")
    table.add_column("Base URL")
    table.add_column("Auth")
    table.add_column("Active")

    for profile in profiles:
        table.add_row(
            profile.name,
            profile.base_url,
            "yes" if profile.is_authenticated else "no",
            "yes" if profile.name == active_profile else "",
        )

    console.print(table)


def print_user(user: dict, profile_name: str) -> None:
    console.print(
        Panel.fit(
            f"[bold]{user.get('name') or user.get('email', 'Unknown')}[/bold]\n"
            f"{user.get('email', 'Unknown email')}\n"
            f"profile: {profile_name}",
            title="Authenticated User",
        )
    )


def print_search_results(results: list[dict], query: str) -> None:
    table = Table(title=f"Search Results for '{query}'")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Domain")
    table.add_column("Score")

    for result in results:
        score = result.get("relevance_score") or result.get("similarity_score") or ""
        table.add_row(
            result.get("id", ""),
            result.get("title") or "Untitled",
            result.get("domain") or "",
            str(score),
        )

    console.print(table)


def print_bookmark(bookmark: dict) -> None:
    title = bookmark.get("title") or "Untitled"
    body = [
        f"[bold]{title}[/bold]",
        bookmark.get("url") or "",
        f"domain: {bookmark.get('domain') or 'unknown'}",
    ]

    ai_summary = bookmark.get("ai_summary") or {}
    if ai_summary.get("one_sentence"):
        body.append("")
        body.append(ai_summary["one_sentence"])

    highlights = ai_summary.get("highlights") or []
    if highlights:
        body.append("")
        body.append("Highlights:")
        body.extend(f"- {item}" for item in highlights[:3])

    console.print(Panel("\n".join(body), title=f"Bookmark {bookmark.get('id', '')}"))


def print_collections(collections: list[dict]) -> None:
    table = Table(title="Collections")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Bookmarks")

    for collection in collections:
        table.add_row(
            collection.get("id", ""),
            collection.get("name", ""),
            str(len(collection.get("bookmark_ids", []))),
        )

    console.print(table)


def print_resurfacing(suggestions: list[dict]) -> None:
    table = Table(title="Resurfacing Suggestions")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Reason")
    table.add_column("Score")

    for item in suggestions:
        table.add_row(
            item.get("id", ""),
            item.get("title") or "Untitled",
            item.get("resurfacing_reason") or "",
            str(item.get("resurfacing_score", "")),
        )

    console.print(table)


def print_graph_overview(payload: dict) -> None:
    top_concepts = payload.get("concepts", [])[:10]
    top_entities = payload.get("entities", [])[:10]
    console.print(
        Panel.fit(
            "\n".join(
                [
                    f"bookmarks: {payload.get('total_bookmarks', 0)}",
                    f"concepts: {payload.get('total_concepts', 0)}",
                    f"entities: {payload.get('total_entities', 0)}",
                    "",
                    f"top concepts: {', '.join(top_concepts) if top_concepts else 'none'}",
                    f"top entities: {', '.join(top_entities) if top_entities else 'none'}",
                ]
            ),
            title="Knowledge Graph Overview",
        )
    )


def print_status(title: str, body: str) -> None:
    console.print(Panel.fit(body, title=title))

