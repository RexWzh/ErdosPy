"""Workspace-oriented erdospy CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from .common import DBOption, get_console, get_table
from erdospy.workflow import update_workspace as workflow_update_workspace

workspace_app = typer.Typer(
    help="Manage the local erdospy workspace and update history."
)
update_workspace = workflow_update_workspace


@workspace_app.command()
def build(
    db_path: DBOption = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite the target DB if it exists.")
    ] = False,
) -> None:
    """Create a writable local workspace database from the bundled snapshot."""

    from erdospy.workflow import initialize_workspace

    console = get_console()
    resolved = initialize_workspace(db_path, force=force)
    console.print(f"[green]Initialized workspace database:[/green] {resolved}")
    console.print(f"[cyan]History file:[/cyan] {resolved.parent / 'history.jsonl'}")


@workspace_app.command()
def update(
    db_path: DBOption = None,
    navigator_root: Annotated[
        Optional[Path],
        typer.Option(
            "--navigator-root", help="Reserved path for source repo compatibility."
        ),
    ] = None,
    pull: Annotated[
        bool,
        typer.Option("--pull", help="Reserved flag for future source synchronization."),
    ] = False,
    quick: Annotated[
        bool, typer.Option("--quick", help="Reserved flag for future update modes.")
    ] = False,
    comments_only: Annotated[
        bool,
        typer.Option(
            "--comments-only", help="Reserved flag for future comment-only sync."
        ),
    ] = False,
    show_changes: Annotated[
        bool,
        typer.Option(
            "--show-changes/--no-show-changes",
            help="Render detected changes after the update.",
        ),
    ] = True,
) -> None:
    """Run an incremental update against a writable workspace database."""

    console = get_console()
    result = update_workspace(
        db_path,
        navigator_root=navigator_root,
        pull=pull,
        quick=quick,
        comments_only=comments_only,
    )

    summary = get_table(title="Update Summary")
    summary.add_column("Metric", style="bold cyan")
    summary.add_column("Value", justify="right")
    summary.add_row("Workspace DB", str(result.db_path))
    summary.add_row("Recorded at", result.run.recorded_at)
    summary.add_row("Total changes", str(result.run.total_changes))
    summary.add_row("Status changes", str(result.run.status_changes))
    summary.add_row("Comment deltas", str(result.run.comment_changes))
    console.print(summary)

    if show_changes and result.changes:
        table = get_table(title="Detected Changes")
        table.add_column("Problem", style="bold")
        table.add_column("Type")
        table.add_column("Description")
        for change in result.changes[:20]:
            table.add_row(change.problem_number, change.change_type, change.description)
        console.print(table)
    elif show_changes:
        console.print("[yellow]No changes detected in this update run.[/yellow]")


@workspace_app.command()
def daily(
    db_path: DBOption = None,
    date: Annotated[
        Optional[str],
        typer.Option(
            "--date", help="Show progress for a specific UTC date, e.g. 2026-04-07."
        ),
    ] = None,
) -> None:
    """Show the recorded daily progress from prior build/update runs."""

    from erdospy.workflow import daily_history, format_daily_heading

    console = get_console()
    entries = daily_history(db_path, date=date)
    if not entries:
        console.print(
            "[yellow]No daily history recorded yet. Run `erdospy build` or `erdospy update` first.[/yellow]"
        )
        return

    effective_date = date or entries[0]["recorded_at"][:10]
    changes = [entry for entry in entries if entry.get("kind") == "change"]
    runs = [entry for entry in entries if entry.get("kind") == "run"]
    typer.echo(format_daily_heading(effective_date))

    summary = get_table(title="Daily Progress Summary")
    summary.add_column("Metric", style="bold cyan")
    summary.add_column("Value", justify="right")
    summary.add_row("Runs", str(len(runs)))
    summary.add_row("Tracked changes", str(len(changes)))
    summary.add_row(
        "Changed problems", str(len({entry["problem_number"] for entry in changes}))
    )
    console.print(summary)

    if changes:
        typer.echo("Daily change summary:")
        for entry in changes[:20]:
            typer.echo(
                f"- {entry['recorded_at']} | #{entry['problem_number']} | {entry['change_type']} | {entry['description']}"
            )

        table = get_table(title="Daily Change Log")
        table.add_column("When")
        table.add_column("Problem", style="bold")
        table.add_column("Type")
        table.add_column("Description")
        for entry in changes[:20]:
            table.add_row(
                entry["recorded_at"],
                entry["problem_number"],
                entry["change_type"],
                entry["description"],
            )
        console.print(table)


@workspace_app.command()
def record(
    problem_number: str,
    db_path: DBOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 10,
) -> None:
    """Show the recorded local change history for a specific problem."""

    from erdospy.workflow import format_record_heading, problem_record

    console = get_console()
    entries = problem_record(problem_number, db_path, limit=limit)
    if not entries:
        console.print(
            f"[yellow]No recorded history for problem #{problem_number} yet.[/yellow]"
        )
        return

    typer.echo(format_record_heading(problem_number))
    typer.echo("Recorded change summary:")
    for entry in entries:
        typer.echo(
            f"- {entry['recorded_at']} | {entry['change_type']} | {entry['description']}"
        )

    table = get_table(title="Problem Record")
    table.add_column("When")
    table.add_column("Type")
    table.add_column("Description")
    for entry in entries:
        table.add_row(entry["recorded_at"], entry["change_type"], entry["description"])
    console.print(table)
