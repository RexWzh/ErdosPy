# erdospy

`erdospy` is a Python package and CLI for exploring Paul Erdős problems from a bundled SQLite snapshot.

Current Phase 1 scope:

- standard `src` layout package
- reusable SQLite query layer
- `typer + rich` CLI for core read workflows
- pure CLI workspace flow for local build, incremental update, daily progress, and per-problem history

## Install

```bash
pip install -e .
```

## Quick Start

This is the shortest real workflow today.

### 1. Create a writable local workspace database

```bash
erdospy build
```

By default this creates:

```bash
./.erdospy/erdos_problems.db
./.erdospy/history.jsonl
./.erdospy/snapshot.json
```

### 2. Query the local workspace snapshot

```bash
erdospy stats --db ./.erdospy/erdos_problems.db
erdospy get 42 --db ./.erdospy/erdos_problems.db --comments
erdospy search "Sidon set" --db ./.erdospy/erdos_problems.db --limit 5
erdospy list --db ./.erdospy/erdos_problems.db --status open --tag primes --limit 10
```

### 3. Run an incremental refresh

In the current dev workflow, `erdospy update` reuses the upstream `erdos-navigator` scraper checkout.
If `reference/erdos-navigator/` or `core/erdos-navigator/` exists in this workspace, the CLI finds it automatically.

```bash
erdospy update --db ./.erdospy/erdos_problems.db --quick
erdospy update --db ./.erdospy/erdos_problems.db --pull
erdospy update --db ./.erdospy/erdos_problems.db --comments-only
```

If auto-detection fails, pass the path explicitly:

```bash
erdospy update --db ./.erdospy/erdos_problems.db --navigator-root ../reference/erdos-navigator --quick
```

### 4. Check daily progress and specific records

```bash
erdospy daily --db ./.erdospy/erdos_problems.db
erdospy daily --db ./.erdospy/erdos_problems.db --date 2026-04-07
erdospy record 42 --db ./.erdospy/erdos_problems.db
```

### End-to-end CLI flow

```bash
# install once
pip install -e .

# create a writable local DB
erdospy build

# inspect local state
erdospy stats --db ./.erdospy/erdos_problems.db
erdospy get 42 --db ./.erdospy/erdos_problems.db --comments

# run a daily quick refresh
erdospy update --db ./.erdospy/erdos_problems.db --quick

# inspect what changed today
erdospy daily --db ./.erdospy/erdos_problems.db

# drill into one problem's local history
erdospy record 42 --db ./.erdospy/erdos_problems.db
```

## Command Reference

```bash
erdospy stats
erdospy get 42
erdospy get 42 --json
erdospy get 42 --comments
erdospy search "Sidon set"
erdospy list --status open --tag primes --has-prize
erdospy build
erdospy update --quick
erdospy daily
erdospy record 42
```
