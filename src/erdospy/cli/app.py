"""Top-level erdospy CLI application."""

from __future__ import annotations

import typer


def build_app() -> typer.Typer:
    app = typer.Typer(
        help="Explore Erdős problems from the terminal.", no_args_is_help=True
    )

    # Import command modules lazily when building the CLI, keeping the entrypoint thin.
    from erdospy.cli.query import query_app
    from erdospy.cli.workspace import workspace_app

    for command in query_app.registered_commands:
        app.registered_commands.append(command)
    for command in workspace_app.registered_commands:
        app.registered_commands.append(command)

    return app


app = build_app()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
