"""Serve a simple local erdospy dashboard."""

from __future__ import annotations

import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Annotated

import typer

from .common import DBOption, get_console

serve_app = typer.Typer(help="Serve a simple local dashboard for erdospy.")


@serve_app.command("dashboard")
def serve_dashboard(
    db_path: DBOption = None,
    host: Annotated[str, typer.Option("--host", help="Host to bind.")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", min=1, max=65535)] = 8000,
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Directory used to stage the served dashboard."),
    ] = Path(".erdospy/site"),
) -> None:
    """Generate and serve a static dashboard with core stats and latest changes."""

    from erdospy.dashboard import write_dashboard_html

    console = get_console()
    output_dir = output_dir.expanduser().resolve()
    target = write_dashboard_html(output_dir / "index.html", db_path=db_path)

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(output_dir))
    server = ThreadingHTTPServer((host, port), handler)
    console.print(f"[green]Serving dashboard:[/green] http://{host}:{port}")
    console.print(f"[cyan]Source:[/cyan] {target}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped dashboard server.[/yellow]")
    finally:
        server.server_close()
