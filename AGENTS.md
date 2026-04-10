# erdospy Development Notes

This repository keeps implementation and runtime workspace data separate.

## Data and Workspace

- Do not commit large runtime database files into the source repository.
- Default runtime workspace data lives under `~/.erdospy/`.
- Default database path: `~/.erdospy/erdos_problems.db`
- Default history path: `~/.erdospy/history.jsonl`
- Default snapshot path: `~/.erdospy/snapshot.json`
- Use environment overrides when automation or tests need isolated paths:
- `ERDOSPY_HOME` overrides the workspace root
- `ERDOSPY_DB_PATH` overrides the exact database file path

## CLI Surface

- Keep the CLI small and task-focused.
- Do not add new top-level command groups unless there is a clear, durable need.
- Prefer improving existing commands over adding parallel entry points.
- `serve dashboard` is acceptable as a lightweight local viewing command.

## Testing

- Tests must not depend on a real user home directory.
- Tests must not depend on a large repository-tracked database snapshot.
- Use temporary sample databases and environment variable injection for isolated test runs.
- Keep generation logic and test data setup decoupled.

## Docs and CI

- Update docs when changing default paths or user-facing workflow.
- Keep README and `docs/quick-start.zh.md` aligned with actual behavior.
- Keep GitHub Actions workflows consistent with the current implementation, especially around dashboard generation and workspace assumptions.

## Change Scope

- Prefer the smallest correct change.
- Avoid mixing unrelated cleanup into feature work.
- Finish implementation, tests, docs, and CI alignment before asking for review.
