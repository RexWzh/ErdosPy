"""Task-oriented skills commands for erdospy."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from .common import DBOption, get_console

skills_app = typer.Typer(help="Run higher-level Erdős workflow skills.")


@skills_app.command("refresh")
def skills_refresh(
    db_path: DBOption = None,
    full_forum: Annotated[
        bool,
        typer.Option(
            "--full-forum",
            help="Run a full forum sync after the incremental workspace update.",
        ),
    ] = False,
    forum_limit: Annotated[
        int | None,
        typer.Option("--forum-limit", min=1, help="Limit forum sync to first N threads."),
    ] = None,
) -> None:
    """Refresh the local workspace for a typical daily Erdős workflow."""

    from erdospy.cli.workspace import update_workspace
    from erdospy.db import ErdosDB
    from erdospy.scraper.incremental import IncrementalUpdater
    from erdospy.workflow import initialize_workspace, resolve_db_path

    console = get_console()
    resolved = resolve_db_path(db_path)
    if not resolved.exists():
        initialize_workspace(resolved)

    result = update_workspace(resolved)
    console.print(
        f"[green]Workspace refreshed:[/green] {resolved} ({result.run.total_changes} changes)"
    )

    if full_forum:
        with IncrementalUpdater(resolved) as updater:
            sync_result = updater.full_sync_limited(limit=forum_limit)
        console.print(
            "[cyan]Forum sync completed:[/cyan] "
            f"{sync_result.thread_details_fetched} thread pages, {sync_result.forum_posts_fetched} posts"
        )

    with ErdosDB(resolved) as db:
        digest = db.get_forum_digest(limit=5)
    if digest["recent_changes"]:
        console.print("[bold]Latest signals:[/bold]")
        for entry in digest["recent_changes"][:5]:
            console.print(
                f"- #{entry['problem_number']} [{entry['change_type']}] {entry['description']}"
            )


@skills_app.command("investigate")
def skills_investigate(
    number: str,
    db_path: DBOption = None,
    show_posts: Annotated[
        int,
        typer.Option("--show-posts", min=0, max=10, help="Posts to show from related thread."),
    ] = 3,
) -> None:
    """Inspect one problem together with its recent progress signals."""

    from erdospy.cli.forum import forum_thread
    from erdospy.cli.query import progress
    from erdospy.db import ErdosDB

    progress(number, db_path=db_path, as_json=False)

    with ErdosDB(db_path) as db:
        rows = db.get_related_problem_threads(number, limit=1)
    if rows:
        typer.echo()
        forum_thread(rows[0]["thread_key"], db_path=db_path, as_json=False, show_posts=show_posts)


@skills_app.command("publish-dashboard")
def skills_publish_dashboard(
    db_path: DBOption = None,
    output: Annotated[
        Path, typer.Option("--output", help="Dashboard HTML output path.")
    ] = Path("site/dashboard/index.html"),
) -> None:
    """Generate the static dashboard page used by local serve and GitHub Pages."""

    from erdospy.dashboard import write_dashboard_html

    console = get_console()
    target = write_dashboard_html(output, db_path=db_path)
    console.print(f"[green]Dashboard written:[/green] {target}")
