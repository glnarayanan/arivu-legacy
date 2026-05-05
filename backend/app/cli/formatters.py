"""Rich output helpers for CLI commands."""

from __future__ import annotations

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def _format_created_date(value: str | None) -> str:
    """Format ISO date string to readable format."""
    if not value:
        return "unknown"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return value[:10] if value else "unknown"


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


def print_bookmarks_list(bookmarks: list[dict]) -> None:
    """Print table of bookmarks with ID, Title, Domain, Read status, Date."""
    table = Table(title="Bookmarks")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold", max_width=50)
    table.add_column("Domain", max_width=25)
    table.add_column("Read", justify="center", width=6)
    table.add_column("Date", width=12)

    for bookmark in bookmarks:
        is_read = bookmark.get("read", False) or bookmark.get("is_read", False)
        read_status = "✓" if is_read else "○"
        created_at = _format_created_date(bookmark.get("created_at"))

        table.add_row(
            bookmark.get("id", ""),
            bookmark.get("title") or "Untitled",
            bookmark.get("domain") or "",
            read_status,
            created_at,
        )

    console.print(table)


def print_bulk_save_summary(saved: list[dict], failed: list[dict]) -> None:
    """Print summary of bulk save operation."""
    if failed:
        console.print(
            Panel(
                f"[bold green]Saved: {len(saved)}[/bold green]\n"
                f"[bold red]Failed: {len(failed)}[/bold red]\n\n"
                + "\n".join(f"[red]✗ {f['url']}: {f['error']}[/red]" for f in failed[:5]),
                title="Bulk Save Summary",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold green]Successfully saved {len(saved)} bookmarks[/bold green]",
                title="Bulk Save Summary",
            )
        )

    # List saved bookmarks
    if saved:
        console.print("")
        table = Table(title="Saved Bookmarks")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("URL", max_width=50)

        for bookmark in saved:
            table.add_row(
                bookmark.get("id", ""),
                bookmark.get("title") or "Untitled",
                bookmark.get("url", "")[:50],
            )

        console.print(table)


def print_stats_summary(payload: dict, *, label: str = "Statistics") -> None:
    """Print analytics stats with reading metrics."""
    stats = payload.get("stats", {})
    topics = payload.get("topics", [])

    body_lines = [
        f"Total Bookmarks: {stats.get('total_bookmarks', 0)}",
        f"Read: {stats.get('read_bookmarks', 0)}",
        f"Unread: {stats.get('unread_bookmarks', 0)}",
    ]

    completion_rate = stats.get("completion_rate")
    if completion_rate is not None:
        body_lines.append(f"Completion Rate: {completion_rate:.1f}%")

    reading_time = stats.get("total_reading_time_minutes")
    if reading_time:
        hours = reading_time // 60
        mins = reading_time % 60
        body_lines.append(f"Total Reading Time: {hours}h {mins}m")

    if topics:
        body_lines.append("")
        body_lines.append("Top Topics:")
        for topic in topics[:5]:
            name = topic.get("name", "Unknown")
            count = topic.get("count", 0)
            body_lines.append(f"  • {name}: {count}")

    console.print(Panel.fit("\n".join(body_lines), title=label))


def print_url_preview(preview: dict) -> None:
    """Print URL preview metadata."""
    title = preview.get("title") or "Untitled"
    domain = preview.get("domain") or "unknown"
    description = preview.get("description") or ""

    body = [
        f"[bold]{title}[/bold]",
        f"[dim]{domain}[/dim]",
    ]

    if description:
        body.append("")
        body.append(description[:200])

    console.print(Panel("\n".join(body), title=f"Preview {preview.get('url', '')[:60]}"))


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
