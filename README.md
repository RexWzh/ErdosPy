# erdospy

`erdospy` is a Python package and CLI for analyzing Erdős problems, tracking latest progress, and surfacing relevant discussions directly from the terminal.

Documentation:

- Chinese quick start: `docs/quick-start.zh.md`
- MkDocs config: `mkdocs.yml`

Current Phase 1 scope:

- standard `src` layout package
- reusable SQLite query layer
- `typer + rich` CLI for core read workflows
- pure CLI workspace flow for local build, incremental update, daily progress, and per-problem history
- full forum extraction via CLI, including thread metadata, problem descriptions, posts, replies, and reaction summaries
- analysis-oriented CLI access to the latest progress and related discussion history
- simple `serve` dashboard for local viewing and GitHub Pages publishing

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
~/.erdospy/erdos_problems.db
~/.erdospy/history.jsonl
~/.erdospy/snapshot.json
```

### 2. Query the local workspace snapshot

```bash
erdospy stats --db ~/.erdospy/erdos_problems.db
erdospy get 42 --db ~/.erdospy/erdos_problems.db --comments
erdospy search "Sidon set" --db ~/.erdospy/erdos_problems.db --limit 5
erdospy list --db ~/.erdospy/erdos_problems.db --status open --tag primes --limit 10
```

### 3. Run an incremental refresh

`erdospy update` updates the local workspace changelog from the tracked forum index.

```bash
erdospy update --db ~/.erdospy/erdos_problems.db --quick
erdospy update --db ~/.erdospy/erdos_problems.db --pull
erdospy update --db ~/.erdospy/erdos_problems.db --comments-only
```

### 4. Run a full forum extraction

To capture full forum structure, including thread pages, posts, replies, and reaction summaries:

```bash
erdospy forum sync --db ~/.erdospy/erdos_problems.db
```

For a partial full sync while iterating on the scraper:

```bash
erdospy forum sync --db ~/.erdospy/erdos_problems.db --limit 20 --show-top 5
```

Stored forum stats can be inspected directly from CLI:

```bash
erdospy forum stats --db ~/.erdospy/erdos_problems.db
erdospy forum thread 12 --db ~/.erdospy/erdos_problems.db --show-posts 3
erdospy forum latest --db ~/.erdospy/erdos_problems.db --limit 10
erdospy forum related 12 --db ~/.erdospy/erdos_problems.db
erdospy forum search "Lean proofs" --db ~/.erdospy/erdos_problems.db
```

### 5. Check daily progress and specific records

```bash
erdospy daily --db ~/.erdospy/erdos_problems.db
erdospy daily --db ~/.erdospy/erdos_problems.db --date 2026-04-07
erdospy record 42 --db ~/.erdospy/erdos_problems.db
```

### End-to-end CLI flow

```bash
# install once
pip install -e .

# create a writable local DB
erdospy build

# inspect local state
erdospy stats --db ~/.erdospy/erdos_problems.db
erdospy get 42 --db ~/.erdospy/erdos_problems.db --comments

# capture forum data once in full
erdospy forum sync --db ~/.erdospy/erdos_problems.db

# then run daily incremental refreshes
erdospy update --db ~/.erdospy/erdos_problems.db

# inspect what changed today
erdospy daily --db ~/.erdospy/erdos_problems.db

# drill into one problem's local history
erdospy record 42 --db ~/.erdospy/erdos_problems.db

# inspect full stored forum data for a thread
erdospy forum thread 12 --db ~/.erdospy/erdos_problems.db --show-posts 3

# inspect latest progress and related discussion
erdospy forum latest --db ~/.erdospy/erdos_problems.db --limit 10
erdospy forum related 12 --db ~/.erdospy/erdos_problems.db
erdospy forum search "formalised" --db ~/.erdospy/erdos_problems.db

# inspect one problem as a whole
erdospy progress 12 --db ~/.erdospy/erdos_problems.db

# get a compact digest of latest movement
erdospy digest --db ~/.erdospy/erdos_problems.db --limit 10

# serve a local dashboard
erdospy serve dashboard --db ~/.erdospy/erdos_problems.db --port 8000
```

## Forum Capture Status

The current CLI supports a full forum extraction pass that stores:

- thread index metadata from `/forum/`
- problem descriptions attached to thread pages
- full thread pages for stored entries
- posts and nested replies
- reaction summaries for posts
- problem-level forum reactions where present

Recent real CLI run against the local workspace database produced:

- indexed problem threads: `735`
- stored thread details: `79`
- stored forum posts: `1745`
- distinct post authors: `85`

Top stored problem threads in the current local snapshot:

- `#1038` with `134` comments
- `#848` with `48` comments
- `#1045` with `47` comments
- `#1041` with `41` comments
- `#423` with `38` comments

## Command Reference

```bash
erdospy stats
erdospy get 42
erdospy get 42 --json
erdospy get 42 --comments
erdospy search "Sidon set"
erdospy list --status open --tag primes --has-prize
erdospy progress 12
erdospy digest
erdospy build
erdospy update --quick
erdospy daily
erdospy record 42
erdospy forum sync
erdospy forum stats
erdospy forum thread 12
erdospy forum latest
erdospy forum related 12
erdospy forum search "formalised"
erdospy serve dashboard
```
