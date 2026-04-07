"""Typer CLI for erdospy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from erdospy.db import ErdosDB
from erdospy.models import Problem
from erdospy.workflow import (
    daily_history,
    format_daily_heading,
    format_record_heading,
    initialize_workspace,
    problem_record,
    update_workspace,
)

app = typer.Typer(
    help="Explore Erdős problems from the terminal.", no_args_is_help=True
)
console = Console()
DBOption = Annotated[
    Path | None,
    typer.Option("--db", help="Use a specific SQLite database file."),
]


def _status_style(status: str) -> str:
    if status in {"solved", "proved"}:
        return "green"
    if status in {"disproved", "falsifiable"}:
        return "red"
    if status == "open":
        return "yellow"
    return "cyan"


def _statement_preview(text: str, limit: int = 100) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[: limit - 3]}..."


def _render_problem_detail(problem: Problem) -> None:
    meta = Table.grid(padding=(0, 2))
    meta.add_column(style="bold cyan", justify="right")
    meta.add_column()
    meta.add_row(
        "Status",
        f"[{_status_style(problem.status)}]{problem.status}[/{_status_style(problem.status)}]",
    )
    meta.add_row("Prize", problem.prize)
    meta.add_row("Formalized", "yes" if problem.formalized else "no")
    meta.add_row("Comments", str(problem.comments_count))
    meta.add_row("Tags", ", ".join(problem.tags) if problem.tags else "-")
    meta.add_row("OEIS", ", ".join(problem.oeis) if problem.oeis else "-")
    if problem.lean_url:
        meta.add_row("Lean", problem.lean_url)

    body = problem.statement.strip() or "No statement stored."
    if problem.additional_text:
        body = f"{body}\n\n[bold]Additional context[/bold]\n{problem.additional_text.strip()}"

    console.print(
        Panel.fit(meta, title=f"Problem #{problem.number}", border_style="blue")
    )
    console.print(Panel(body, title="Statement", border_style="white"))

    if problem.references:
        console.print(
            Panel(
                "\n".join(problem.references[:10]),
                title="References",
                border_style="magenta",
            )
        )
    if problem.related_problems:
        console.print(
            Panel(
                ", ".join(problem.related_problems[:20]),
                title="Related Problems",
                border_style="cyan",
            )
        )


def _render_problem_table(problems: list[Problem], title: str) -> None:
    table = Table(title=title)
    table.add_column("#", style="bold")
    table.add_column("Status")
    table.add_column("Prize")
    table.add_column("Tags")
    table.add_column("Comments", justify="right")
    table.add_column("Statement")

    for problem in problems:
        status_text = Text(problem.status, style=_status_style(problem.status))
        table.add_row(
            problem.number,
            status_text,
            problem.prize,
            ", ".join(problem.tags[:3]) if problem.tags else "-",
            str(problem.comments_count),
            _statement_preview(problem.statement),
        )

    console.print(table)


@app.command()
def stats(db_path: DBOption = None) -> None:
    """Show dataset statistics."""

    with ErdosDB(db_path) as db:
        data = db.get_statistics()
        summary = Table(title="erdospy Stats")
        summary.add_column("Metric", style="bold cyan")
        summary.add_column("Value", justify="right")
        summary.add_row("Total problems", str(data["total"]))
        summary.add_row("With statements", str(data["with_statements"]))
        summary.add_row("Formalized", str(data["formalized"]))
        summary.add_row("With Lean links", str(data["with_lean"]))
        summary.add_row("With prizes", str(data["with_prizes"]))
        summary.add_row("Total reactions", str(data["total_reactions"]))
        summary.add_row("Unique users", str(data["unique_users"]))
        summary.add_row("Total contributors", str(data["total_contributors"]))
        summary.add_row("Total comments", str(data["total_comments"]))
        console.print(summary)

        status_table = Table(title="Status Breakdown")
        status_table.add_column("Status", style="bold")
        status_table.add_column("Count", justify="right")
        for status_name, count in sorted(
            data["by_status"].items(), key=lambda item: (-item[1], item[0])
        ):
            status_table.add_row(
                Text(status_name, style=_status_style(status_name)), str(count)
            )
        console.print(status_table)

        tag_table = Table(title="Top Tags")
        tag_table.add_column("Tag", style="bold")
        tag_table.add_column("Count", justify="right")
        for tag, count in db.get_all_tags()[:15]:
            tag_table.add_row(tag, str(count))
        console.print(tag_table)


@app.command()
def get(
    number: str,
    db_path: DBOption = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output raw JSON")] = False,
    comments: Annotated[
        bool, typer.Option("--comments", help="Include comments in output")
    ] = False,
) -> None:
    """Show a single problem."""

    with ErdosDB(db_path) as db:
        problem = db.get_problem(number)
        if not problem:
            console.print(f"[red]Problem #{number} not found.[/red]")
            raise typer.Exit(code=1)

        if as_json:
            payload = problem.model_dump()
            if comments:
                payload["comments"] = [
                    comment.model_dump() for comment in db.get_comments(number)
                ]
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        _render_problem_detail(problem)

        if comments:
            comment_table = Table(title=f"Comments for #{problem.number}")
            comment_table.add_column("Author", style="bold")
            comment_table.add_column("Date")
            comment_table.add_column("Likes", justify="right")
            comment_table.add_column("Content")
            for comment in db.get_comments(number):
                comment_table.add_row(
                    comment.author or comment.author_username,
                    comment.date,
                    str(comment.likes),
                    _statement_preview(comment.content, limit=120),
                )
            console.print(comment_table)


@app.command()
def search(
    query: str,
    db_path: DBOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=200)] = 20,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
) -> None:
    """Full-text search across problem statements."""

    with ErdosDB(db_path) as db:
        problems = db.full_text_search(query, limit=limit, offset=offset)
        if not problems:
            console.print(f"[yellow]No matches for {query!r}.[/yellow]")
            return
        _render_problem_table(problems, f"Search Results for {query!r}")


@app.command(name="list")
def list_problems(
    db_path: DBOption = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
    tag: Annotated[str | None, typer.Option("--tag")] = None,
    has_prize: Annotated[
        bool | None, typer.Option("--has-prize/--no-has-prize")
    ] = None,
    formalized: Annotated[
        bool | None, typer.Option("--formalized/--no-formalized")
    ] = None,
    has_lean: Annotated[bool | None, typer.Option("--has-lean/--no-has-lean")] = None,
    has_reactions: Annotated[
        bool | None, typer.Option("--has-reactions/--no-has-reactions")
    ] = None,
    reaction_type: Annotated[str | None, typer.Option("--reaction-type")] = None,
    text_query: Annotated[str | None, typer.Option("--query")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=500)] = 30,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
) -> None:
    """List problems using structured filters."""

    with ErdosDB(db_path) as db:
        problems = db.search(
            status=status,
            tag=tag,
            has_prize=has_prize,
            formalized=formalized,
            has_lean=has_lean,
            has_reactions=has_reactions,
            reaction_type=reaction_type,
            text_query=text_query,
            limit=limit,
            offset=offset,
        )
        if not problems:
            console.print("[yellow]No problems matched the requested filters.[/yellow]")
            return

        filters = {
            "status": status,
            "tag": tag,
            "has_prize": has_prize,
            "formalized": formalized,
            "has_lean": has_lean,
            "has_reactions": has_reactions,
            "reaction_type": reaction_type,
            "query": text_query,
            "limit": limit,
            "offset": offset,
        }
        active = ", ".join(
            f"{key}={value}"
            for key, value in filters.items()
            if value not in {None, False, 0, ""}
        )
        title = "Problem List" if not active else f"Problem List ({active})"
        _render_problem_table(problems, title)


@app.command()
def build(
    db_path: DBOption = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite the target DB if it exists.")
    ] = False,
) -> None:
    """Create a writable local workspace database from the bundled snapshot."""

    resolved = initialize_workspace(db_path, force=force)
    console.print(f"[green]Initialized workspace database:[/green] {resolved}")
    console.print(f"[cyan]History file:[/cyan] {resolved.parent / 'history.jsonl'}")


@app.command()
def update(
    db_path: DBOption = None,
    navigator_root: Annotated[
        Path | None,
        typer.Option(
            "--navigator-root", help="Path to the upstream erdos-navigator checkout."
        ),
    ] = None,
    pull: Annotated[
        bool, typer.Option("--pull", help="Pull the latest YAML repo before updating.")
    ] = False,
    quick: Annotated[
        bool, typer.Option("--quick", help="Skip comment scraping.")
    ] = False,
    comments_only: Annotated[
        bool, typer.Option("--comments-only", help="Refresh comments only.")
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

    result = update_workspace(
        db_path,
        navigator_root=navigator_root,
        pull=pull,
        quick=quick,
        comments_only=comments_only,
    )

    summary = Table(title="Update Summary")
    summary.add_column("Metric", style="bold cyan")
    summary.add_column("Value", justify="right")
    summary.add_row("Workspace DB", str(result.db_path))
    summary.add_row("Recorded at", result.run.recorded_at)
    summary.add_row("Total changes", str(result.run.total_changes))
    summary.add_row("Status changes", str(result.run.status_changes))
    summary.add_row("Comment deltas", str(result.run.comment_changes))
    console.print(summary)

    if show_changes and result.changes:
        table = Table(title="Detected Changes")
        table.add_column("Problem", style="bold")
        table.add_column("Type")
        table.add_column("Description")
        for change in result.changes[:20]:
            table.add_row(change.problem_number, change.change_type, change.description)
        console.print(table)
    elif show_changes:
        console.print("[yellow]No changes detected in this update run.[/yellow]")


@app.command()
def daily(
    db_path: DBOption = None,
    date: Annotated[
        str | None,
        typer.Option(
            "--date", help="Show progress for a specific UTC date, e.g. 2026-04-07."
        ),
    ] = None,
) -> None:
    """Show the recorded daily progress from prior build/update runs."""

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

    summary = Table(title="Daily Progress Summary")
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

        table = Table(title="Daily Change Log")
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


@app.command()
def record(
    problem_number: str,
    db_path: DBOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 10,
) -> None:
    """Show the recorded local change history for a specific problem."""

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

    table = Table(title="Problem Record")
    table.add_column("When")
    table.add_column("Type")
    table.add_column("Description")
    for entry in entries:
        table.add_row(entry["recorded_at"], entry["change_type"], entry["description"])
    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
