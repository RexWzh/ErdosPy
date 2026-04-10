"""Top-level erdospy CLI application."""

from __future__ import annotations

import typer


def build_app() -> typer.Typer:
    app = typer.Typer(
        help="Explore Erdős problems from the terminal.", no_args_is_help=True
    )

    # Import command modules lazily when building the CLI, keeping the entrypoint thin.
    from erdospy.cli.forum import forum_app
    from erdospy.cli.query import query_app
    from erdospy.cli.serve import serve_app
    from erdospy.cli.skills import skills_app
    from erdospy.cli.workspace import workspace_app

    for command in query_app.registered_commands:
        app.registered_commands.append(command)
    for command in workspace_app.registered_commands:
        app.registered_commands.append(command)
    app.add_typer(forum_app, name="forum")
    app.add_typer(skills_app, name="skills")
    app.add_typer(serve_app, name="serve")

    return app


app = build_app()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
