"""Forum extraction and inspection commands."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from .common import DBOption, get_console, get_panel, get_table

forum_app = typer.Typer(help="Extract and inspect full forum data.")


@forum_app.command("sync")
def forum_sync(
    db_path: DBOption = None,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            min=1,
            help="Only fetch the first N indexed threads for a partial full sync.",
        ),
    ] = None,
    show_top: Annotated[
        int,
        typer.Option("--show-top", min=0, max=20, help="Show top threads after sync."),
    ] = 10,
) -> None:
    """Run a full forum extraction and store all thread/post data locally."""

    from erdospy.scraper.incremental import IncrementalUpdater
    from erdospy.workflow import initialize_workspace, resolve_db_path

    console = get_console()
    resolved = resolve_db_path(db_path)
    if not resolved.exists():
        initialize_workspace(resolved)

    with IncrementalUpdater(resolved) as updater:
        result = updater.full_sync_limited(limit=limit)

    summary = get_table(title="Forum Full Sync")
    summary.add_column("Metric", style="bold cyan")
    summary.add_column("Value", justify="right")
    summary.add_row("Workspace DB", str(resolved))
    summary.add_row("Detected at", result.detected_at)
    summary.add_row("Threads indexed", str(result.forum_threads_seen))
    summary.add_row("Thread pages fetched", str(result.thread_details_fetched))
    summary.add_row("Posts captured", str(result.forum_posts_fetched))
    summary.add_row("Mode", "full" if limit is None else f"partial ({limit})")
    console.print(summary)

    if show_top > 0:
        from erdospy.db import ErdosDB

        with ErdosDB(resolved) as db:
            stats = db.get_forum_statistics()
        top = get_table(title="Top Problem Threads")
        top.add_column("Problem", style="bold")
        top.add_column("Comments", justify="right")
        top.add_column("Title")
        for item in stats["top_problem_threads"][:show_top]:
            top.add_row(
                item["problem_number"] or "-",
                str(item["comment_count"]),
                item["title"] or "-",
            )
        console.print(top)


@forum_app.command("stats")
def forum_stats(
    db_path: DBOption = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="Output stats as JSON.")
    ] = False,
) -> None:
    """Show stored forum extraction statistics."""

    from erdospy.db import ErdosDB

    with ErdosDB(db_path) as db:
        stats = db.get_forum_statistics()

    if as_json:
        typer.echo(json.dumps(stats, ensure_ascii=False, indent=2))
        return

    console = get_console()
    summary = get_table(title="Forum Statistics")
    summary.add_column("Metric", style="bold cyan")
    summary.add_column("Value", justify="right")
    summary.add_row("Problem threads", str(stats["problem_threads"]))
    summary.add_row("Stored thread details", str(stats["thread_details"]))
    summary.add_row("Stored posts", str(stats["forum_posts"]))
    summary.add_row("Distinct post authors", str(stats["distinct_post_authors"]))
    console.print(summary)

    top = get_table(title="Top Problem Threads")
    top.add_column("Problem", style="bold")
    top.add_column("Comments", justify="right")
    top.add_column("Title")
    for item in stats["top_problem_threads"]:
        top.add_row(
            item["problem_number"] or "-",
            str(item["comment_count"]),
            item["title"] or "-",
        )
    console.print(top)


@forum_app.command("thread")
def forum_thread(
    thread_key: str,
    db_path: DBOption = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="Output full stored thread data as JSON.")
    ] = False,
    show_posts: Annotated[
        int,
        typer.Option(
            "--show-posts",
            min=0,
            max=50,
            help="Number of posts to render in the terminal.",
        ),
    ] = 10,
) -> None:
    """Show a stored full thread, including posts and problem metadata."""

    from erdospy.db import ErdosDB

    with ErdosDB(db_path) as db:
        detail = db.get_forum_thread_detail(thread_key)

    if not detail:
        raise typer.BadParameter(f"No stored forum thread found for {thread_key!r}.")

    if as_json:
        typer.echo(json.dumps(detail, ensure_ascii=False, indent=2))
        return

    console = get_console()
    console.print(
        get_panel(
            detail["statement"] or "No statement stored.",
            title=detail["title"] or thread_key,
            border_style="blue",
        )
    )

    meta = get_table(title="Thread Metadata")
    meta.add_column("Field", style="bold cyan")
    meta.add_column("Value")
    meta.add_row("Thread key", detail["thread_key"])
    meta.add_row("Category", detail["category"])
    meta.add_row("Problem", detail["problem_number"] or "-")
    meta.add_row("Status", detail["status_text"] or "-")
    meta.add_row("Comments", str(detail["comment_count"]))
    meta.add_row("Tags", ", ".join(detail["tags"]) if detail["tags"] else "-")
    meta.add_row("URL", detail["thread_url"] or "-")
    console.print(meta)

    posts = detail["posts"][:show_posts]
    post_table = get_table(title=f"Posts ({len(posts)} shown)")
    post_table.add_column("Post")
    post_table.add_column("Author")
    post_table.add_column("When")
    post_table.add_column("Content")
    for post in posts:
        preview = " ".join(post["content_markdown"].split())
        if len(preview) > 120:
            preview = preview[:117] + "..."
        post_table.add_row(
            f"#{post['post_id']} d={post['depth']}",
            post["author_name"] or post["author_username"] or "-",
            post["created_at"] or "-",
            preview or "-",
        )
    console.print(post_table)
