---
name: erdospy-workflow
description: Use erdospy to build a local workspace under ~/.erdospy, inspect Erdős problem progress, refresh forum-derived changes, and serve a simple dashboard.
version: 0.1.0
---

# erdospy Workflow

## Overview

Use `erdospy` as a local CLI workspace for Erdős problem exploration.

This skill assumes:

- runtime workspace data lives under `~/.erdospy/`
- the main database is `~/.erdospy/erdos_problems.db`
- automation and tests can override paths with `ERDOSPY_HOME` or `ERDOSPY_DB_PATH`

## Core Flow

Initialize a writable local workspace:

```bash
erdospy build
```

Inspect current state:

```bash
erdospy stats --db ~/.erdospy/erdos_problems.db
erdospy progress 12 --db ~/.erdospy/erdos_problems.db
erdospy digest --db ~/.erdospy/erdos_problems.db --limit 10
```

Refresh latest changes:

```bash
erdospy update --db ~/.erdospy/erdos_problems.db
erdospy daily --db ~/.erdospy/erdos_problems.db
erdospy record 12 --db ~/.erdospy/erdos_problems.db
```

Inspect forum activity:

```bash
erdospy forum stats --db ~/.erdospy/erdos_problems.db
erdospy forum latest --db ~/.erdospy/erdos_problems.db --limit 10
erdospy forum thread 12 --db ~/.erdospy/erdos_problems.db --show-posts 5
```

Serve the local dashboard:

```bash
erdospy serve dashboard --db ~/.erdospy/erdos_problems.db --port 8000
```

## Notes

- Keep runtime data out of the source repository.
- Do not add parallel CLI entry points for this workflow unless there is a durable need.
- Prefer updating this `SKILL.md` when the workflow changes, so the reusable process stays documented separately from the CLI surface.
