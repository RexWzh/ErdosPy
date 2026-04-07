"""Query-oriented erdospy CLI commands."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from .common import (
    DBOption,
    get_console,
    get_panel,
    get_table,
    get_text,
    statement_preview,
    status_style,
)

query_app = typer.Typer(help="Query problems and local database state.")


def _render_problem_detail(problem) -> None:
    console = get_console()
    from rich.panel import Panel
    from rich.table import Table

    meta = Table.grid(padding=(0, 2))
    meta.add_column(style="bold cyan", justify="right")
    meta.add_column()
    meta.add_row(
        "Status",
        f"[{status_style(problem.status)}]{problem.status}[/{status_style(problem.status)}]",
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


def _render_problem_table(problems: list, title: str) -> None:
    console = get_console()
    table = get_table(title=title)
    text = get_text
    table.add_column("#", style="bold")
    table.add_column("Status")
    table.add_column("Prize")
    table.add_column("Tags")
    table.add_column("Comments", justify="right")
    table.add_column("Statement")

    for problem in problems:
        table.add_row(
            problem.number,
            text(problem.status, style=status_style(problem.status)),
            problem.prize,
            ", ".join(problem.tags[:3]) if problem.tags else "-",
            str(problem.comments_count),
            statement_preview(problem.statement),
        )

    console.print(table)


@query_app.command()
def stats(db_path: DBOption = None) -> None:
    """Show dataset statistics."""

    from erdospy.db import ErdosDB

    console = get_console()
    with ErdosDB(db_path) as db:
        data = db.get_statistics()
        summary = get_table(title="erdospy Stats")
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

        status_table = get_table(title="Status Breakdown")
        status_table.add_column("Status", style="bold")
        status_table.add_column("Count", justify="right")
        for status_name, count in sorted(
            data["by_status"].items(), key=lambda item: (-item[1], item[0])
        ):
            status_table.add_row(
                get_text(status_name, style=status_style(status_name)), str(count)
            )
        console.print(status_table)

        tag_table = get_table(title="Top Tags")
        tag_table.add_column("Tag", style="bold")
        tag_table.add_column("Count", justify="right")
        for tag, count in db.get_all_tags()[:15]:
            tag_table.add_row(tag, str(count))
        console.print(tag_table)


@query_app.command()
def get(
    number: str,
    db_path: DBOption = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output raw JSON")] = False,
    comments: Annotated[
        bool, typer.Option("--comments", help="Include comments in output")
    ] = False,
) -> None:
    """Show a single problem."""

    from erdospy.db import ErdosDB

    console = get_console()
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
            comment_table = get_table(title=f"Comments for #{problem.number}")
            comment_table.add_column("Author", style="bold")
            comment_table.add_column("Date")
            comment_table.add_column("Likes", justify="right")
            comment_table.add_column("Content")
            for comment in db.get_comments(number):
                comment_table.add_row(
                    comment.author or comment.author_username,
                    comment.date,
                    str(comment.likes),
                    statement_preview(comment.content, limit=120),
                )
            console.print(comment_table)


@query_app.command()
def search(
    query: str,
    db_path: DBOption = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=200)] = 20,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
) -> None:
    """Full-text search across problem statements."""

    from erdospy.db import ErdosDB

    console = get_console()
    with ErdosDB(db_path) as db:
        problems = db.full_text_search(query, limit=limit, offset=offset)
        if not problems:
            console.print(f"[yellow]No matches for {query!r}.[/yellow]")
            return
        _render_problem_table(problems, f"Search Results for {query!r}")


@query_app.command(name="list")
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

    from erdospy.db import ErdosDB

    console = get_console()
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
