"""Shared CLI helpers for erdospy."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

DBOption = Annotated[
    Optional[Path],
    typer.Option("--db", help="Use a specific SQLite database file."),
]


def get_console():
    from rich.console import Console

    return Console()


def get_table(*args, **kwargs):
    from rich.table import Table

    return Table(*args, **kwargs)


def get_panel(*args, **kwargs):
    from rich.panel import Panel

    return Panel(*args, **kwargs)


def get_text(*args, **kwargs):
    from rich.text import Text

    return Text(*args, **kwargs)


def status_style(status: str) -> str:
    if status in {"solved", "proved"}:
        return "green"
    if status in {"disproved", "falsifiable"}:
        return "red"
    if status == "open":
        return "yellow"
    return "cyan"


def statement_preview(text: str, limit: int = 100) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[: limit - 3]}..."
